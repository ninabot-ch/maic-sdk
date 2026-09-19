# Bâtiments — un agent = un bâtiment (règle Nick, 18.09.2026)

> « Quand on fabrique un agent, on fabrique le bâtiment qui va avec, selon des guidelines pour que ça suive le
> style ; ça permet aux gens de faire grandir leur ville / company avec leur nombre de features. »

## 1. Principe
La ville du deck n'est pas un décor : c'est **l'inventaire visible de la compagnie**. Chaque agent qu'une compagnie
possède (acheté au Bazar, financé par cagnotte, ou offert) pose **son bâtiment** sur le campus de son `campus:`.
Plus une compagnie a de features, plus sa ville est dense. Un agent retiré → bâtiment démonté (animation), une
version majeure → façade rafraîchie. Le dev qui livre un agent livre donc **le manifeste du bâtiment** en même temps
(bloc `building:` de `agent.yaml`, §3). Il ne livre pas de modèle 3D : le bâtiment est **décrit**, la ville le
**construit** avec ses propres matériaux (`deck/city.js`), ce qui garantit le style.

## 2. Guidelines de style (ce que la validation vérifie, étape 1 lint + étape 4 jury)
1. **Procédural, jamais importé.** Pas de `.glb`, pas de texture externe : un bâtiment = une combinaison de
   primitives (`box`, `slab`, `cylinder`, `ring`, `dome`, `curved-roof`, `terrace`) et de matériaux de la ville.
2. **Matériaux de la palette seulement** : verre `blue | teal | slate | warm | plum | olive` (`GL`), opaques
   `core` (blanc chaud), `white`, `dark`, `concrete`, `solar`, `lawn`. Pas de couleur libre : l'accent de la
   compagnie ne teinte que le **logo au sol**, jamais la façade.
3. **Style « campus moderne »** (Silicon Valley, verre, toits végétalisés ou solaires, anneaux, terrasses) :
   pas de pixel-art, pas de médiéval, pas de gratte-ciel (hauteur max 4 niveaux, la tour du Studio reste la plus
   haute de la ville).
4. **Empreinte** : `1x1` (petit outil), `2x1` (agent courant), `2x2` (agent lourd, abonnement mensuel). Le campus
   place le bâtiment sur ses lots libres, dans l'ordre d'acquisition ; quand le campus est plein, il s'agrandit
   d'une rangée (les campus sont construits à l'échelle 1 puis agrandis, K = 1.25).
5. **Lisible en iso** : une silhouette reconnaissable à zoom 1 (un élément signature : anneau, dôme, auvent,
   cheminée solaire, terrasse, parabole…). Pas de détail < 0,05 unité.
6. **Nom peint au sol** devant le bâtiment (même mécanique que les campus : canvas → plane, y = .062), dans la
   langue de la compagnie. Optionnel : `glyph` (un caractère ou emoji) sur le toit.
7. **Le bâtiment vit** : en veille = éclairé faiblement ; en marche (job actif) = fenêtres allumées + motes de
   consommation au-dessus, au rythme de `rate_maic_h` ; échec = clignotement rouge 5 s ; construction = monte du sol
   en 1,2 s ; démontage = inverse.
8. **Cohérence de campus** : le bâtiment reprend la teinte de verre dominante de son campus par défaut
   (`glass: campus`), une autre teinte doit être justifiée dans le README (« pourquoi ce bâtiment se distingue »).
9. **Un agent = un bâtiment, pas plus.** Un agent multi-fonctions reste un bâtiment (avec `2x2` au plus).
10. **Accessibilité** : `reduced` (préférence système) → pas d'animation, bâtiment posé directement.

## 3. Bloc `building:` du manifeste (obligatoire depuis le 18.09.2026)
```yaml
building:
  footprint: 2x1              # 1x1 | 2x1 | 2x2
  levels: 2                   # 1..4
  shape: slab                 # slab | ring | dome | hall | terraces | tower-low | pavilion
  glass: campus               # campus | blue | teal | slate | warm | plum | olive
  roof: green                 # flat | green | solar | curved | dome
  signature: awning           # un élément : awning | ring | dome | chimney | terrace | dish | canopy | atrium | none
  glyph: "🛠"                  # optionnel, ≤ 2 caractères, posé sur le toit
  label: {fr: "Prix photo", en: "Photo pricing"}   # ≤ 16 caractères, peint au sol
```
Le lint (`validate.py`) vérifie la présence du bloc, les valeurs dans les énumérations, `levels ≤ 4`, `label`
FR + EN ≤ 16 caractères. Le jury (étape 4) juge la lisibilité et la cohérence de style sur le rendu automatique
(`scripts/render-building.py` à venir : capture iso du bâtiment seul et posé dans son campus).

## 4. Galerie de style — https://myaicompany.ch/gallery/ (livrée 18.09.2026)
`public/gallery/index.html`, FR/EN. Rend avec le **même kit** que le deck (`createBuildingKit` exporté par
`deck/city.js`, mêmes matériaux, même lumière) : un composeur (campus, footprint, levels, shape, glass, roof,
signature, glyph, label, état ; aperçu orbitable ; YAML à copier dans `agent.yaml`) puis une carte par forme (7),
toit (5), signature (9), verre (7), empreinte × niveaux (6) et état (3, animés). Un seul renderer WebGL recopié
dans les canvas 2D des cartes. ⚠️ L'import du kit est versionné par `build-proto.sh` (`/proto/city.js?v=<md5>`).

## 5. Ce que ça implique côté deck
**Codé le 18.09 (nuit)** dans `deck/city.js` : `createBuildingKit()` (matériaux + `build(spec, lot)`) et, dans
`createCity`, l'allocation des lots (anneaux 1..3 autour de la plaza, côté opposé au centre-ville d'abord, jamais à
travers une route, l'arbre de la cellule est retiré), les états veille / marche / échec / construction / démontage,
les motes au-dessus des bâtiments en marche, `setAgents(list)` et la synchro depuis `getState().agents_owned`.
`/state.agents_owned` (API) = actions maison déjà lancées ; les 8 actions portent leur bloc `building:` dans
le deck. Reste : les vrais agents du Bazar (bloc porté par leur manifeste).
