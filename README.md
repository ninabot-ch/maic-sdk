# maic-sdk — build agents for MyAiCompany companies

An agent is a small Python program that runs in a sandbox on the MyAiCompany platform and works for one company:
it reads what the company allows (its memory, contacts, products, orders, files), calls language models through
tiers, and returns a report the founder reads in thirty seconds. Every agent is also a building in the company's city.

- `sdk/maic_sdk.py` — the `ctx` your `run(ctx, params)` receives (memory, data, llm, prompt, progress, report).
- `sdk/bench.py` — local test bench: `python3 sdk/bench.py template/` (add `--live` with `INFOMANIAK_AI_TOKEN` to call real models).
- `template/` — copy it, fill `agent.yaml` (params, scopes, cost, price, building), write `run.py`, prompts FR + EN, 3 fixtures.
- `examples/resume-semaine/` — a real published agent (weekly summary of a company).
- `docs/agents.md` — manifest, guidelines, marketplace rules, validation pipeline; `docs/buildings.md` — one agent = one building.

Publishing goes through the platform (lint → sandbox fixtures → security scan → jury → beta → published); developers are
registered on SOKKAN Missions and are paid on every sale. MIT licence for this SDK; agents keep their author's licence.

## FR
Un agent est un petit programme Python qui tourne dans un bac à sable de la plateforme MyAiCompany et travaille pour une
compagnie : il lit ce qu'elle autorise, appelle les modèles par paliers, et rend un rapport lisible en trente secondes.
Chaque agent est aussi un bâtiment de la ville. Copie `template/`, remplis `agent.yaml`, écris `run.py`, teste avec
`python3 sdk/bench.py`, puis publie via la plateforme (voir `docs/agents.md`).
