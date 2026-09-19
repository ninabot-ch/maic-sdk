"""maic_sdk — ce que `run(ctx, params)` reçoit dans le bac à sable (docs/agents.md §3).

Le bac à sable n'a ni réseau, ni variables d'environnement, ni fichier hors /work. Tout ce qui touche la
compagnie ou les modèles passe par `ctx`, qui parle au runner par des lignes JSON (stdout → requête,
stdin → réponse). Le runner relaie à maic-api, qui applique les scopes du manifeste et le budget en maic.
Les `print()` de l'agent partent sur stderr et finissent dans le journal du run.
"""
import html, json, os, sys

_OUT = sys.stdout            # canal protocole (réservé) ; les prints de l'agent sont redirigés vers stderr par le boot
_IN = sys.stdin


class AgentError(Exception):
    """Refus du serveur (scope non déclaré, budget épuisé, appel inconnu)."""


class BudgetExceeded(AgentError):
    """Le plafond `cost.cap_maic` du manifeste est atteint : l'agent doit conclure avec ce qu'il a."""


def _call(op, **kw):
    kw["op"] = op
    _OUT.write(json.dumps(kw, ensure_ascii=False) + "\n"); _OUT.flush()
    line = _IN.readline()
    if not line:
        raise AgentError("runner closed")
    r = json.loads(line)
    if not r.get("ok"):
        err = str(r.get("error") or "error")
        raise BudgetExceeded(err) if err.startswith("budget") else AgentError(err)
    return r.get("result")


class _Memory:
    def search(self, q, k=5):
        """Notes de la Bibliothèque (CortHeXis) les plus proches du sujet : liste de {name, description, excerpt}."""
        return _call("memory.search", q=str(q)[:500], k=int(k))

    def note(self, path):
        return _call("memory.note", path=str(path))


class _Data:
    """Lecture des scopes déclarés dans `reads` : ctx.data.contacts(), .products(), .orders(), .invoices(), .leads(), .files()."""
    def __getattr__(self, scope):
        if scope.startswith("_"):
            raise AttributeError(scope)
        return lambda limit=200: _call("data", scope=scope, limit=int(limit))


class _Write:
    """Écritures déclarées dans `writes` (P1 : memory seulement ; products/contacts arrivent avec la prévisualisation)."""
    def memory(self, title, facts, description=""):
        return _call("write", scope="memory", title=str(title)[:120], facts=[str(f)[:300] for f in facts][:30], description=str(description)[:300])


class Context:
    def __init__(self, env):
        self.company = env.get("company") or {}
        self.lang = env.get("lang") or "fr"
        self.params = env.get("params") or {}
        self.manifest = env.get("manifest") or {}
        self.memory = _Memory(); self.data = _Data(); self.write = _Write()
        self._prompts = env.get("prompts") or {}
        self._report = None

    # --- prompts : prompt/<lang>.<name>.txt, variables {{param}}
    def prompt(self, name="main", **vars_):
        key = f"{self.lang}.{name}"
        txt = self._prompts.get(key) or self._prompts.get(f"fr.{name}") or self._prompts.get(f"en.{name}") or ""
        merged = dict(self.params); merged.update(vars_)
        for k, v in merged.items():
            txt = txt.replace("{{" + str(k) + "}}", str(v))
        return txt

    # --- modèles : par palier, compté en maic par le serveur, coupé au plafond
    def llm(self, tier, messages, max_tokens=800, temperature=0.2):
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        return _call("llm", tier=str(tier), messages=messages, max_tokens=int(max_tokens), temperature=float(temperature))

    def llm_json(self, tier, messages, max_tokens=800):
        """Comme llm() mais attend un objet JSON (le serveur force le mode JSON quand le modèle le permet)."""
        txt = _call("llm", tier=str(tier), messages=messages if not isinstance(messages, str) else [{"role": "user", "content": messages}], max_tokens=int(max_tokens), temperature=0.1, json=True)
        s = txt.strip()
        if s.startswith("```"):
            s = s.strip("`"); s = s[s.find("{"):]
        return json.loads(s[s.find("{"):s.rfind("}") + 1])

    def progress(self, pct):
        _call("progress", pct=max(0, min(100, int(pct))))

    def spent(self):
        """Maic déjà consommés par ce run et plafond."""
        return _call("spent")

    @staticmethod
    def esc(x):
        return html.escape(str(x if x is not None else ""))

    def report(self, title=None, html="", facts=None, text=None):
        """Le résultat du run. `title` None = titre du manifeste ; `facts` = phrases courtes gardées en mémoire."""
        self._report = {"title": title, "html": str(html)[:60000], "facts": [str(f)[:300] for f in (facts or [])][:20], "text": text}
        return self._report

    def log(self, *a):
        print(*a, file=sys.stderr, flush=True)
