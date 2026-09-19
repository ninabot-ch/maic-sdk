#!/usr/bin/env python3
"""Étape 1 du pipeline (lint) — docs/agents.md §7. Zéro dépendance : YAML plat lu à la main, suffisant pour le manifeste."""
import json, os, re, sys
ROOT = os.path.dirname(os.path.abspath(__file__)); errs = []
CAMPUS = {"studio", "marche", "scene", "mairie", "biblio", "centrale"}; TIERS = {"tool", "code", "deal", "pitch", "ops", "frontier"}
SCOPES_R = {"contacts", "products", "orders", "invoices", "leads", "files", "memory"}; SCOPES_W = {"report", "products", "contacts", "files", "memory"}
try:
    y = open(os.path.join(ROOT, "agent.yaml"), encoding="utf-8").read()
except FileNotFoundError:
    print("agent.yaml manquant"); sys.exit(1)
def field(k):
    m = re.search(rf"^{k}:\s*(.+?)\s*(#.*)?$", y, re.M); return m.group(1).strip() if m else None
def lst(k):
    v = field(k) or ""; m = re.match(r"^\[(.*)\]$", v); return [x.strip() for x in m.group(1).split(",") if x.strip()] if m else None
id_ = field("id") or ""
if not re.match(r"^[a-z0-9]([a-z0-9-]{1,38}[a-z0-9])$", id_) or "<" in id_: errs.append("id : kebab-case, 3–40 caractères, pas de < >")
if not re.match(r"^\d+\.\d+\.\d+$", field("version") or ""): errs.append("version : semver x.y.z")
if field("campus") not in CAMPUS: errs.append(f"campus : un de {sorted(CAMPUS)}")
for k in ("title", "summary"):
    v = field(k) or ""
    if not (re.search(r"fr:\s*\"[^\"<>]{3,}\"", v) and re.search(r"en:\s*\"[^\"<>]{3,}\"", v)): errs.append(f"{k} : fr ET en, sans < >")
r, w = lst("reads"), lst("writes")
if r is None or not set(r) <= SCOPES_R: errs.append(f"reads : sous-ensemble de {sorted(SCOPES_R)}")
if w is None or not set(w) <= SCOPES_W or "report" not in w: errs.append(f"writes : sous-ensemble de {sorted(SCOPES_W)}, report obligatoire")
n = lst("network")
if n is None: errs.append("network : liste (vide par défaut)")
elif n and not os.path.exists(os.path.join(ROOT, "NETWORK.md")): errs.append("network non vide : justifier dans NETWORK.md (revue humaine)")
t = lst("models")
if not t or not set(t) <= TIERS: errs.append(f"models : paliers parmi {sorted(TIERS)}, jamais un nom de modèle")
c = field("cost") or ""
m = {k: int(v) for k, v in re.findall(r"(estimate_maic|cap_maic|rate_maic_h):\s*(\d+)", c)}
if not {"estimate_maic", "cap_maic", "rate_maic_h"} <= set(m): errs.append("cost : estimate_maic, cap_maic, rate_maic_h")
elif not (0 < m["estimate_maic"] <= m["cap_maic"] <= 5000): errs.append("cost : 0 < estimate ≤ cap ≤ 5000")
if "<" in (field("author") or ""): errs.append("author : renseigner sokkan_dev et name")
if not re.search(r"per_run_maic:\s*\d+|per_month_maic:\s*\d+", field("price") or ""): errs.append("price : per_run_maic ou per_month_maic")
if (field("license") or "") != "maic-marketplace-1.0": errs.append("license : maic-marketplace-1.0")
# bâtiment (docs/buildings.md) — un agent = un bâtiment
B_ENUM = {"footprint": {"1x1", "2x1", "2x2"}, "shape": {"slab", "ring", "dome", "hall", "terraces", "tower-low", "pavilion"},
          "glass": {"campus", "blue", "teal", "slate", "warm", "plum", "olive"}, "roof": {"flat", "green", "solar", "curved", "dome"},
          "signature": {"awning", "ring", "dome", "chimney", "terrace", "dish", "canopy", "atrium", "none"}}
bm = re.search(r"^building:[ \t]*(?:#.*)?$((?:\n[ \t]+.*)+)", y, re.M); bblock = bm.group(1) if bm else ""
if not bblock: errs.append("building : bloc obligatoire (docs/buildings.md)")
else:
    def bf(k):
        m = re.search(rf"^\s+{k}:\s*(.+?)\s*(#.*)?$", bblock, re.M); return m.group(1).strip().strip('"') if m else None
    for k, allowed in B_ENUM.items():
        if bf(k) not in allowed: errs.append(f"building.{k} : un de {sorted(allowed)}")
    lv = bf("levels")
    if not (lv and lv.isdigit() and 1 <= int(lv) <= 4): errs.append("building.levels : 1..4")
    lb = bf("label") or ""
    fr_, en_ = re.search(r"fr:\s*\"([^\"]*)\"", lb), re.search(r"en:\s*\"([^\"]*)\"", lb)
    if not (fr_ and en_) or "<" in lb or len(fr_.group(1)) > 16 or len(en_.group(1)) > 16 or len(fr_.group(1)) < 2: errs.append("building.label : fr ET en, 2–16 caractères, sans < >")
    g = bf("glyph")
    if g and len(g) > 2: errs.append("building.glyph : ≤ 2 caractères")
for f in ("run.py", "README.md", "prompt/fr.main.txt", "prompt/en.main.txt"):
    if not os.path.exists(os.path.join(ROOT, f)): errs.append(f"{f} manquant")
fx = sorted(f for f in os.listdir(os.path.join(ROOT, "fixtures")) if f.endswith(".json")) if os.path.isdir(os.path.join(ROOT, "fixtures")) else []
if len(fx) < 3: errs.append("fixtures : 3 jeux minimum")
for f in fx:
    try:
        d = json.load(open(os.path.join(ROOT, "fixtures", f), encoding="utf-8"))
        if not {"params", "expect"} <= set(d): errs.append(f"fixtures/{f} : clés params et expect")
    except Exception as e: errs.append(f"fixtures/{f} : JSON invalide ({type(e).__name__})")
src = open(os.path.join(ROOT, "run.py"), encoding="utf-8").read() if os.path.exists(os.path.join(ROOT, "run.py")) else ""
if "def run(ctx, params)" not in src: errs.append("run.py : def run(ctx, params)")
for bad in ("import requests", "import urllib", "import socket", "import subprocess", "os.environ", "open("):
    if bad in src: errs.append(f"run.py : interdit ({bad}) — passer par ctx")
if "<" in open(os.path.join(ROOT, "README.md"), encoding="utf-8").read() if os.path.exists(os.path.join(ROOT, "README.md")) else False: errs.append("README.md : remplacer les < placeholders >")
for e in errs: print("✗", e)
print("✓ manifeste et structure valides" if not errs else f"{len(errs)} problème(s)"); sys.exit(1 if errs else 0)
