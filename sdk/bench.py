"""bench.py — banc d'essai local d'un agent, sans plateforme ni Docker : `python3 bench.py <dossier de l'agent> [--live]`.

Rejoue chaque fixtures/*.json en appelant run(ctx, params) dans ce processus avec un broker de poche : la mémoire et les
données viennent de la fixture, les modèles répondent par un texte factice (ou pour de vrai avec --live et la variable
INFOMANIAK_AI_TOKEN). Vérifie `expect` : report_contains, max_maic (estimation), max_seconds. Ce n'est PAS le bac à sable
(étape 2 du pipeline, jouée par la plateforme) : c'est l'outil du développeur pour itérer vite.
"""
import glob, json, os, sys, time, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import maic_sdk
TIER_MODEL = {"tool": "mistralai/Ministral-3-14B-Instruct-2512", "code": "Qwen/Qwen3.5-122B-A10B-FP8", "deal": "moonshotai/Kimi-K2.6", "pitch": "moonshotai/Kimi-K2.6", "ops": "moonshotai/Kimi-K2.6", "frontier": "moonshotai/Kimi-K2.6"}
RATES = {"tool": 0.05, "code": 0.2, "deal": 0.4, "pitch": 0.4, "ops": 0.4, "frontier": 0.8}   # maic pour 1000 tokens (même table que la plateforme)


def live_llm(tier, messages, max_tokens, temperature, want_json):
    import urllib.request
    base = os.environ.get("MAIC_LLM_BASE", "https://api.infomaniak.com/2/ai/110008/openai/v1"); key = os.environ["INFOMANIAK_AI_TOKEN"]
    model = TIER_MODEL.get(tier, TIER_MODEL["tool"]); body = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    if "Kimi" in model: body["chat_template_kwargs"] = {"thinking": False}
    if want_json: body["response_format"] = {"type": "json_object"}
    req = urllib.request.Request(base + "/chat/completions", data=json.dumps(body).encode(), method="POST", headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "User-Agent": "maic-bench/0.1"})
    with urllib.request.urlopen(req, timeout=120) as r: d = json.loads(r.read().decode())
    u = d.get("usage") or {}
    return (d["choices"][0]["message"].get("content") or ""), int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0)


def run_fixture(agent_dir, fx, live):
    company = fx.get("company") or {"name": "Compagnie test", "slug": "test", "lang": "fr"}; lang = company.get("lang", "fr")
    prompts = {os.path.basename(p)[:-4]: open(p, encoding="utf-8").read() for p in glob.glob(os.path.join(agent_dir, "prompt", "*.txt"))}
    cap = int((fx.get("expect") or {}).get("max_maic") or 100); state = {"maic": 0, "calls": 0, "log": []}; facts_written = []

    def broker(op, **kw):
        if op == "memory.search":
            return [{"name": f"note-{i}", "description": m[:80], "excerpt": m} for i, m in enumerate(fx.get("memory") or [])][:int(kw.get("k") or 5)]
        if op == "memory.note": return {"path": kw.get("path"), "text": "\n".join(fx.get("memory") or [])}
        if op == "data": return (fx.get("data") or {}).get(kw.get("scope"), [])
        if op == "write": facts_written.extend(kw.get("facts") or []); return {"ok": True}
        if op == "progress": state["log"].append(f"progress {kw.get('pct')}%"); return None
        if op == "spent": return {"maic": state["maic"], "cap": cap}
        if op == "llm":
            state["calls"] += 1
            if state["calls"] > 40: raise maic_sdk.AgentError("budget: 40 appels par run")
            msgs = kw["messages"]; tin = sum(len(str(m.get("content", ""))) for m in msgs) // 4
            if live and os.environ.get("INFOMANIAK_AI_TOKEN"):
                text, tin, tout = live_llm(kw["tier"], msgs, kw.get("max_tokens", 800), kw.get("temperature", 0.2), kw.get("json"))
            else:
                last = next((str(m.get("content", "")) for m in reversed(msgs) if m.get("role") == "user"), "")
                text = (fx.get("llm") or {}).get("reply") or ('{"note": "réponse factice"}' if kw.get("json") else f"[réponse factice · {kw['tier']}] {last[:300]}"); tout = len(text) // 4
            cost = max(1, int(round((tin + tout) / 1000 * RATES.get(kw["tier"], 0.05)))); state["maic"] += cost
            if state["maic"] > cap: raise maic_sdk.BudgetExceeded(f"budget: {state['maic']} > {cap} maic")
            return text
        raise maic_sdk.AgentError(f"op inconnue {op}")

    old = maic_sdk._call; maic_sdk._call = lambda op, **kw: broker(op, **kw)
    ctx = maic_sdk.Context({"company": company, "lang": lang, "params": fx.get("params") or {}, "prompts": prompts, "manifest": {}})
    t0 = time.time(); err = None; rep = None
    try:
        spec = importlib.util.spec_from_file_location("agent_run_" + str(abs(hash(agent_dir))), os.path.join(agent_dir, "run.py")); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        res = mod.run(ctx, dict(ctx.params)); rep = ctx._report or (res if isinstance(res, dict) else {"html": str(res)})
    except maic_sdk.BudgetExceeded as e:
        rep = ctx._report or {}; err = f"budget ({e})"
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    finally:
        maic_sdk._call = old
    secs = round(time.time() - t0, 2); exp = fx.get("expect") or {}; problems = []
    text = json.dumps(rep or {}, ensure_ascii=False)
    if err: problems.append(err)
    if live:   # hors ligne les modèles répondent un texte factice : `report_contains` n'a de sens qu'avec de vraies réponses
        for s_ in exp.get("report_contains") or []:
            if str(s_).lower() not in text.lower(): problems.append(f"rapport sans « {s_} »")
    if exp.get("max_maic") is not None and state["maic"] > int(exp["max_maic"]): problems.append(f"{state['maic']} maic > {exp['max_maic']}")
    if exp.get("max_seconds") is not None and secs > float(exp["max_seconds"]): problems.append(f"{secs} s > {exp['max_seconds']}")
    return {"ok": not problems, "problems": problems, "maic": state["maic"], "seconds": secs, "report": rep, "facts": facts_written}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]; live = "--live" in sys.argv
    if not args: print(__doc__); sys.exit(2)
    agent_dir = os.path.abspath(args[0]); fxs = sorted(glob.glob(os.path.join(agent_dir, "fixtures", "*.json")))
    if not fxs: print("aucune fixture dans", agent_dir); sys.exit(1)
    bad = 0; costs = []
    for f in fxs:
        r = run_fixture(agent_dir, json.load(open(f, encoding="utf-8")), live); costs.append(r["maic"]); bad += 0 if r["ok"] else 1
        print(("✓" if r["ok"] else "✗"), os.path.basename(f), f"{r['maic']} maic, {r['seconds']} s" + ("" if r["ok"] else " · " + "; ".join(r["problems"])))
        if "--show" in sys.argv: print("   ", json.dumps(r["report"], ensure_ascii=False)[:600])
    print(f"{len(fxs) - bad}/{len(fxs)} fixtures OK · coût médian {sorted(costs)[len(costs) // 2]} maic" + ("" if live else " · hors ligne : run() exécuté avec des modèles factices, `report_contains` vérifié seulement avec --live")); sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
