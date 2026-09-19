# Agents MyAiCompany — mécanique, guidelines, marché, pipeline de validation (v0.1, 19.09.2026)

> Réponse aux questions de Nick du 19.09 : comment on crée un agent, quelles règles, comment le marché s'ouvre aux
> développeurs SOKKAN Missions qui publient spontanément, comment ils sont payés, et comment on valide. Nick a validé
> l'ensemble le 19.09 (« ok pour tout ») : commission 30 %, pipeline en six étapes, marché ouvert aux devs SOKKAN Missions.

## 1. Ce qu'est un agent ici
Un agent est **une capacité empaquetée** qu'une compagnie lance depuis son deck, avec des paramètres, un devis en
maics et un rapport à la fin. Rien d'autre : pas de chat libre, pas d'agent qui « vit » en permanence (les
tâches récurrentes sont des agents lancés par un planning). Les six actions d'aujourd'hui (clients, site, pitch,
facture, domaine, agent) sont des agents maison écrits selon ce même modèle.

Un agent = un dossier versionné dans un dépôt Forgejo (`maic-agents/<nom>`) :

```
agent.yaml        manifeste (voir §2)
prompt/           gabarits de prompts FR + EN (fichiers texte, variables {{param}})
run.py            point d'entrée : run(ctx, params) -> Report ; stdlib + SDK maic uniquement
fixtures/         3 jeux d'entrée/sortie attendus minimum (tests de validation)
README.md         ce qu'il fait, pour qui, exemples, limites, coût observé
```
Le manifeste porte aussi le **bâtiment** de l'agent (bloc `building:`, §5bis et `docs/buildings.md`).

## 2. Le manifeste `agent.yaml`
```yaml
id: prix-photo                # unique, kebab-case
version: 1.2.0                # semver ; le marché garde toutes les versions publiées
campus: marche                # studio | marche | scene | mairie | biblio | centrale
title: {fr: "Prix depuis une photo", en: "Price from a photo"}
summary: {fr: "…", en: "…"}   # une phrase, celle du menu
params:                       # affichés tels quels dans le formulaire de l'action (mêmes types que le deck)
  - {k: photo, type: file, accept: image/*, required: true, l: {fr: "Photo", en: "Photo"}}
  - {k: marge, type: select, o: [{v: "30", fr: "30 %", en: "30 %"}, …], d: "30"}
reads: [products, orders, memory]      # ce que l'agent lit dans la compagnie (scopes, principe du minimum)
writes: [report]                       # report | products | contacts | files | memory (jamais ledger, jamais mail direct)
network: []                            # hôtes externes autorisés (vide par défaut) ; les modèles passent par le SDK
models: [tool, code]                   # paliers de modèles (§4), pas de nom de modèle en dur
cost:
  estimate_maic: 40                    # devis affiché ; la validation vérifie ± 20 % sur les fixtures
  cap_maic: 80                         # plafond dur : au-delà, arrêt et rendu du reste
  rate_maic_h: 60                      # pour l'animation du campus
report: {title: {fr: "…", en: "…"}}    # gabarit du rapport, corps produit par run()
author: {sokkan_dev: "dev-1234", name: "…"}
price:                                 # ce que paie une compagnie qui n'a pas financé l'agent
  per_run_maic: 40                     # ou
  per_month_maic: 300
license: maic-marketplace-1.0
```

## 3. Ce que le SDK donne à `run(ctx, params)` — CODÉ le 18.09.2026 (`agents/sdk/maic_sdk.py`)
Le SDK est un fichier Python sans dépendance, glissé dans le bac à sable avec l'agent. Il ne fait AUCUN travail
lui-même : chaque appel est une ligne JSON sur stdout, la réponse arrive sur stdin (protocole runner ↔ bac à sable,
§9). C'est maic-api qui exécute l'appel, applique les scopes déclarés dans le manifeste et compte les maic.
- `ctx.company` (`name`, `slug`, `lang`, `tagline`), `ctx.lang`, `ctx.params`, `ctx.manifest` ;
- `ctx.prompt(name="main", **vars)` : `prompt/<lang>.<name>.txt` avec les `{{param}}` remplacés ;
- `ctx.llm(tier, messages, max_tokens=800, temperature=.2)` et `ctx.llm_json(...)` : le seul chemin vers les
  modèles (palier → modèle Infomaniak, table `TIERS` d'agents.py), **compté en maic** par le serveur
  (`(tokens entrée + sortie) / 1000 × tarif du palier`, table `RATES`, ⚠️ à recaler sur les tarifs relevés),
  refusé au-delà de `cost.cap_maic` (`BudgetExceeded`) et de 40 appels par run ;
- `ctx.data.contacts() / products() / orders() / invoices() / leads() / files()` selon `reads` ;
  `ctx.memory.search(q, k)` (score par mots sur les notes CortHeXis de la compagnie) et `ctx.memory.note(path)` ;
- `ctx.write.memory(title, facts)` selon `writes` (products/contacts : P2, prévisualisation obligatoire) ;
- `ctx.progress(pct)` (barre du chantier), `ctx.spent()`, `ctx.esc(x)`, `ctx.log(...)` (→ journal du run) ;
- `ctx.report(title=None, html=..., facts=[...])` : le résultat ; `facts` = 1 à 3 phrases gardées dans la
  Bibliothèque (`/data/memory/<slug>/agents/<agent>-<run>.md`) si `writes` contient `memory`.
Tout le reste est interdit par le bac à sable : pas de réseau (`--network none`), pas de fichier hors `/work`
(tmpfs 64 Mo, rootfs en lecture seule), pas de variable d'environnement, utilisateur `nobody`, `cap-drop ALL`,
1 CPU, 512 Mo, 64 processus, 10 minutes (le runner tue le conteneur).

## 4. Paliers de modèles (Infomaniak, hébergés en Suisse) — décision Nick 18.09
| Palier | Usage | Modèle par défaut |
|---|---|---|
| `tool` | classer, extraire, reformuler, courts | Qwen 2.5 / Mistral Nemo (le moins cher) |
| `code` | générer ou modifier du code de site | Qwen Coder / DeepSeek Coder |
| `deal` / `pitch` | prospection, pitch, ton et persuasion | Kimi K2.6 |
| `ops` | opérer et maintenir (logs, diagnostic) | Kimi K2.6 |
| `frontier` | architecture produit, décisions | meilleur modèle Infomaniak du moment |
L'agent nomme le palier, jamais le modèle : on change de modèle sans toucher aux agents. Le tarif par palier est
public dans la doc du marché.

## 5. Guidelines de création (ce qui est vérifié à la validation)
1. **Un agent = un travail** nommable en une phrase, avec un rapport lisible par un non-technicien.
2. **Paramètres explicites** : tout ce qui change le résultat est un champ ; pas de « demande-moi si besoin ».
3. **Devis honnête** : `estimate_maic` dans ± 20 % du coût mesuré sur les fixtures ; le plafond est respecté.
4. **Minimum de droits** : `reads`/`writes` justifiés dans le README ; `writes` sur `products`/`contacts` exige
   une prévisualisation dans le rapport et une validation du client avant application (le SDK l'impose).
5. **Aucune fuite** : pas de données de la compagnie hors du SDK ; `network` vide sauf besoin documenté (une API
   publique, allowlist par hôte, revue humaine).
6. **FR + EN** : prompts, libellés, rapport.
7. **Reproductible** : 3 fixtures minimum, sorties stables (température basse), test vert dans le bac à sable.
8. **Pas de promesse** : un rapport dit ce qui a été fait et ce qui reste à faire ; il n'invente ni chiffres ni
   confirmations (règle maison, cf incident Nina Deal du 14.09).
9. **Coût affiché, animation cohérente** : `rate_maic_h` réaliste, sinon l'animation du campus ment.
10. **Une version = un tag** ; une mise à jour repasse le pipeline (allégé si le manifeste ne change pas).

## 5bis. Un agent = un bâtiment (règle Nick 18.09)
Chaque agent livre aussi **le bâtiment** qui le représente dans la ville de la compagnie, décrit dans le bloc
`building:` du manifeste (empreinte, niveaux, forme, verre, toit, élément signature, nom peint au sol). Le dev ne
livre pas de 3D : la ville construit le bâtiment avec ses propres matériaux, selon les guidelines de
`docs/buildings.md`, pour que tout suive le style « campus moderne ». Résultat : la ville d'une compagnie **grandit
avec son nombre de features** — c'est l'inventaire visible de ce qu'elle possède. Vérifié au lint (bloc présent,
valeurs dans les énumérations) et par le jury (lisibilité, cohérence de style sur le rendu automatique).
**Galerie de style** pour choisir : https://myaicompany.ch/gallery/ (composeur + toutes les valeurs rendues).

## 6. Le marché — décision Nick 19.09
- **Ouvert aux devs inscrits sur SOKKAN Missions**, qui peuvent **publier spontanément** un agent qu'ils ont
  construit, sans mission client préalable. C'est le même profil dev (KYC SOKKAN déjà fait, paiement déjà en place).
- Le dev fixe son prix (par lancement ou par mois, en maics). **Il est payé quand des compagnies achètent** :
  relevé mensuel, paiement via SOKKAN Missions comme une mission (les maics dépensés sont convertis au taux
  1 maic = 0,01 CHF, moins la commission plateforme). Proposition de commission : **30 %** sur les ventes du marché
  (le 5 % ne concerne que les encaissements boutique des clients) — **décision Nick 19.09 : 30 %**.
- Deux origines pour un agent : **spontané** (le dev publie) ou **financé par cagnotte** (spec §6 : le premier dev
  validé qui accepte le prix construit ; les financeurs ont une licence perpétuelle ; prix public ensuite
  supérieur au coût financé, avantage premier financeur).
- Un agent peut être **retiré** par son auteur (les compagnies qui l'ont acheté gardent la dernière version) ou par
  Ninabot (violation, sécurité), avec remboursement des abonnements du mois en cours en maics.
- **Notes et usage visibles** : lancements, taux de réussite (rapport livré / arrêt / échec), note des compagnies,
  coût réel médian vs devis. Le classement du marché s'appuie dessus.

## 7. Pipeline de validation (« assez intéressant pour être validé »)
Un agent n'apparaît sur le marché qu'après six étapes ; chaque étape écrit son verdict dans le dépôt de l'agent
(`validation/<version>.json`) et le dev voit où il en est dans son espace SOKKAN.

| Étape | Qui | Vérifie | Verdict |
|---|---|---|---|
| 1. Lint | automate | manifeste valide, FR+EN complets, semver, fixtures présentes, README avec exemples | bloque |
| 2. Bac à sable | automate | les 3 fixtures passent, coût mesuré vs devis (± 20 %), plafond respecté, temps < 10 min | bloque |
| 3. Sécurité | automate + LLM | scopes minimaux, `network` vide ou justifié, pas de secret dans le code, prompts sans exfiltration ni instruction cachée, dépendances (aucune) | bloque ou « à relire » |
| 4. Intérêt | jury (Ninabot, puis 3 devs du marché tirés au sort) | fait quelque chose d'utile qu'aucun agent existant ne fait mieux ; rapport compréhensible ; prix cohérent avec le coût | accepte / renvoie avec commentaires |
| 5. Bêta | 5 compagnies volontaires (opt-in « je teste les nouveaux agents », 50 % de remise) | 2 semaines, ≥ 10 lancements, taux de réussite ≥ 80 %, note ≥ 3,5/5 | publie / renvoie |
| 6. Publication | automate | fiche du marché générée du manifeste, prix affiché, version figée | — |
Délai cible : 5 jours ouvrés hors bêta. Un agent financé par cagnotte saute l'étape 4 (l'intérêt est prouvé par la
cagnotte) mais fait la bêta avec ses financeurs.

## 8. Ce qui existe (18.09.2026 nuit) et ce qui manque
- **Existe** : SDK (§3), bac à sable + runner (§9), runtime réel côté API (`api/agents.py` : un run = un chantier
  `usage` dont le devis est `cap_maic` + prix du dev, clôturé avec la consommation RÉELLE, part du dev calculée
  avec la commission 30 % dans `agent_earning`), catalogue / achat (`per_run` ou `per_month` via `recurring`) /
  « Mes agents » / cagnottes dans le deck (campus Bazar, onglets Agents · Mes agents · Cagnottes), bâtiment de
  l'agent posé sur le campus dès l'achat (`agents_owned`), premier agent réel `agents/resume-semaine` (Ninabot).
- **Pipeline** : étape 1 (lint) et 3 (scan statique AST + prompts) rejouées à chaque import ; étape 2 = fixtures
  dans le bac à sable (`POST /admin/agents/{id}/test`, verdict dans `validation.sandbox`, coût vs devis ± 20 %) ;
  étape 4 = jury humain (`/review {verdict: accept|return, note}`) ; étape 5 = `/beta` + compagnies opt-in
  (`/admin/agents/opt-in {company}`) ; étape 6 = `/publish` (refusé si lint/sécurité/bac à sable KO, sauf `force`).
  Statuts : draft → lint_ok → sandbox_running → sandbox_ok | sandbox_failed → reviewed | returned → beta → published → retired.
- **Manque** : écritures `products`/`contacts` avec prévisualisation, jury automatique (3 devs tirés au sort),
  relevé mensuel des devs (la table `agent_earning` est prête, pas l'export), conversion des 6 actions maison au
  format agent, licence `maic-marketplace-1.0` (juriste), publication depuis un tag Forgejo (aujourd'hui :
  `scripts/publish-agent.sh <dossier> [--test] [--beta] [--publish]`).

## 8b. Banc d'essai local et dépôt public (19.09.2026)
- `agents/sdk/bench.py <dossier> [--live] [--show]` : rejoue les fixtures en appelant `run(ctx, params)` dans le processus
  avec un broker de poche (mémoire/données de la fixture, modèles factices ; `--live` = Infomaniak avec
  `INFOMANIAK_AI_TOKEN`, `report_contains` vérifié seulement en live). Ce n'est pas le bac à sable : c'est l'outil du dev
  pour itérer en secondes avant `publish-agent.sh --test`.
- **Dépôt public `maic-sdk`** (github.com/ninabot-ch/maic-sdk, MIT) : `sdk/` (maic_sdk.py, sandbox_boot.py, bench.py),
  `template/`, `examples/resume-semaine/`, `docs/` (ce fichier + buildings.md). Source de vérité = ce dépôt privé ;
  `scripts/publish-sdk.sh` recopie et pousse.
  après 30 %) → **porte de conformité** (§11 d'actions-spec) appliquée aux agents du marché (critères génériques : répond
  à la demande, langue, rien d'envoyé sans demande + coût/reste à faire) : 86 % sur la démo. La démo publique possède
  gratuitement tous les agents publiés (reseed) et peut les lancer, pas en acheter.
- Corrigé : le statut restait `sandbox_running` après la dernière fixture (transition ajoutée).
- ⚠️ Sécurité (à trancher) : `maic-runner` monte le socket Docker de la VM pour créer les bacs à sable jetables ; un

## 9. Bac à sable et runner (`runner/runner.py`, `agents/sdk/sandbox_boot.py`)
`maic-runner` (conteneur avec le socket Docker, client Docker statique dans l'image) boucle sur `GET /runs/next`
(clé builder), récupère `GET /runs/{id}/bundle` (fichiers de l'agent + env + `sdk/maic_sdk.py`), lance
`docker run -i --network none … python:3.12-slim python -c <sandbox_boot.py>` et lui envoie le bundle (tar.gz base64)
sur stdin. Ensuite chaque ligne JSON écrite par le SDK (`{"op": "llm"|"data"|"memory.search"|"memory.note"|"write"|
"progress"|"spent"}`) est relayée à `POST /runs/{id}/op` et la réponse `{"ok", "result"|"error"}` renvoyée sur
stdin ; `{"op": "done", "report"}` ou `{"op": "error"}` termine → `POST /runs/{id}/done` (rapport, journal stderr,
durée). Le runner ne voit ni clé LLM ni données : tout est décidé dans `agents.op()`. Les `print()` de l'agent
run réel en 6 s, 1 maic de modèle + 4 maic de prix dev, ledger `hold → hold_release → usage_debit`.
- Existe : le modèle d'action côté deck (paramètres typés, devis, consentement, rapport), le ledger (hold / usage /
  escrow / real), l'exécution simulée par le ticker, les paliers de modèles (décision), SOKKAN Missions (devs,
  KYC, paiement — cf mémoire `sokkan-missions-marketplace`).
- Existe depuis le 19.09 (soir) : le gabarit `agents/template/` (manifeste, `run.py`, prompts FR/EN, 3 fixtures,
  README) et l'étape 1 du pipeline `validate.py` (lint sans dépendance), poussés sur Forgejo dans l'org
  `maic-agents` (dépôt gabarit `agent-template`).
- Manque : le SDK et le bac à sable (P2), le pipeline CI étapes 2–6 (Forgejo Actions), la conversion des six
  actions maison au format agent, la fiche marché dans le Bazar, le relevé mensuel des devs, la licence
  `maic-marketplace-1.0` (juriste).
