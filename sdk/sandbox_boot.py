# Amorce exécutée DANS le bac à sable (python:3.12-slim, --network none, /work en tmpfs, utilisateur nobody).
# Lit sur stdin une ligne JSON {"bundle": <tar.gz base64>, "env": {...}}, déballe /work/agent, importe run.py,
# construit le Context et appelle run(ctx, params). Protocole ensuite : stdout = requêtes, stdin = réponses.
import base64, io, json, os, sys, tarfile, traceback
_proto_out = sys.stdout
sys.stdout = sys.stderr                                   # les print() de l'agent ne polluent pas le protocole
first = sys.stdin.readline()
msg = json.loads(first)
os.makedirs("/work/agent", exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(base64.b64decode(msg["bundle"])), mode="r:gz") as t:
    for m in t.getmembers():                              # pas de chemins sortants, pas de liens
        if m.name.startswith("/") or ".." in m.name or m.issym() or m.islnk():
            raise SystemExit("bundle: chemin refusé " + m.name)
    t.extractall("/work/agent", filter="data")
sys.path.insert(0, "/work/agent/sdk"); sys.path.insert(0, "/work/agent")
os.chdir("/work/agent")
import maic_sdk
maic_sdk._OUT = _proto_out
env = msg.get("env") or {}
prompts = {}
pdir = "/work/agent/prompt"
if os.path.isdir(pdir):
    for fn in os.listdir(pdir):
        if fn.endswith(".txt"):
            prompts[fn[:-4]] = open(os.path.join(pdir, fn), encoding="utf-8").read()
env["prompts"] = prompts
ctx = maic_sdk.Context(env)
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("agent_run", "/work/agent/run.py"); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    result = mod.run(ctx, dict(ctx.params))
    rep = ctx._report or (result if isinstance(result, dict) else None) or {"title": None, "html": "<p>" + maic_sdk.Context.esc(result) + "</p>", "facts": []}
    _proto_out.write(json.dumps({"op": "done", "report": rep}, ensure_ascii=False) + "\n"); _proto_out.flush()
except maic_sdk.BudgetExceeded as e:
    rep = ctx._report
    _proto_out.write(json.dumps({"op": "done", "report": rep, "budget": True, "message": str(e)}, ensure_ascii=False) + "\n"); _proto_out.flush()
except BaseException as e:
    _proto_out.write(json.dumps({"op": "error", "message": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-3000:]}, ensure_ascii=False) + "\n"); _proto_out.flush()
