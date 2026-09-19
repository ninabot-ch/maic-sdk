# resume-semaine — Résumé de la semaine

**Ce qu'il fait** — relit les prospects, commandes, factures et contacts des 7, 14 ou 30 derniers jours, y ajoute ce que la Bibliothèque sait, et rend un résumé en trois parties : ce qui s'est passé, à faire cette semaine, un fait à retenir. **Pour qui** — la Bibliothèque, tout fondateur qui veut un point hebdomadaire sans ouvrir quatre onglets. **Exemple** — période 7 jours, ton sobre → « 3 prospects (2 boutiques déco), 1 commande de 480 CHF payée, facture F-2026-0011 en attente depuis 12 jours : relancer Ravel ».

**Coût observé** — 4 à 8 maic par lancement (palier `tool`, un seul appel). **Limites** — ne modifie rien ; n'envoie rien ; ne lit pas les fichiers.

## Droits demandés et pourquoi
- `reads: leads, orders, invoices, contacts` — les quatre listes que le résumé compte et cite.
- `reads: memory` — les notes de la Bibliothèque donnent le contexte (prix, délais, priorités).
- `writes: memory` — les 1 à 3 faits de fin de rapport sont gardés comme note d'agent.

## Publier
1. `python3 validate.py` doit être vert (le lint est aussi rejoué à l'import).
2. `scripts/publish-agent.sh agents/resume-semaine` puis test des fixtures et publication (docs/agents.md §7).
