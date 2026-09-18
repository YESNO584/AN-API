# Le texte des propositions et projets de loi, chez l'Assemblée

**Mesuré le 2026-09-18**, sur 220 documents réellement téléchargés et lus, et
sur l'archive des dossiers législatifs du jour même.

Cette fiche répond à une question précise : *peut-on montrer, à chaque étape du
parcours, le texte tel qu'il était, et ce qui a changé depuis l'étape
précédente ?*

Elle remplace [`textes-pdf-assemblee.md`](textes-pdf-assemblee.md), qui
répondait oui à la même question **en lisant des PDF**. La réponse est
meilleure ici.

## La conclusion en une phrase

**Le texte intégral de chaque version est publié par l'Assemblée en HTML
structuré — articles délimités, tableaux conservés — à une adresse qui se
déduit d'un identifiant que le socle télécharge déjà : 249 textes ont au moins
deux versions comparables, et la comparaison se calcule avec la bibliothèque
standard de Python, sans aucune dépendance nouvelle.**

## D'abord, une correction : il n'existe pas de JSON du texte

L'Assemblée publie bien un JSON par document, et c'est de la vraie donnée
ouverte :

```
https://www.assemblee-nationale.fr/dyn/opendata/PIONANR5L17B0261.json
```

Mais c'est une **fiche signalétique** : titre, auteur, cosignataires, dossier,
commission. Son champ `divisions`, qui porterait le découpage du texte, est
**vide dans les 6 documents testés** (un dépôt, un texte de commission, un
texte adopté, pour une proposition et pour un projet). Le portail
`data.assemblee-nationale.fr` ne propose par ailleurs **aucun jeu de données
« textes »** : dossiers législatifs, amendements, débats, séance, votes,
acteurs, et rien d'autre.

**Le texte, lui, est là :**

```
https://www.assemblee-nationale.fr/dyn/docs/<IDENTIFIANT>.raw
```

C'est le document Word de l'Assemblée converti en HTML. Ce n'est pas du JSON,
mais c'est **structuré** — ce qui est la seule chose qui compte pour le
découper sans deviner.

## Où trouver l'identifiant

Dans l'archive des dossiers législatifs, que le socle télécharge chaque matin.
Chaque étape du parcours **nomme le document qu'elle produit ou qu'elle
examine** (`texteAssocie`, `texteAdopte`) :

```
AN1-DEPOT       texteAssocie  PRJLANR5L17B2609     le texte déposé
AN1-COM-FOND    texteAdopte   PRJLANR5L17BTC2905   le texte de la commission
AN1-DEBATS-DEC  texteAdopte   PRJLANR5L17BTA0314   le texte adopté en séance
```

**Aucun appel réseau supplémentaire pour savoir quoi chercher, et aucune
devinette sur l'étape à laquelle rattacher une version.** Sur 2 219 textes de
loi, **2 218 ont toutes leurs versions rattachées à une étape**.

## Ce que ça couvre

| Textes de loi de la 17e législature | 2 219 |
|---|---:|
| avec 0 version publiée par l'Assemblée (nés au Sénat) | 470 |
| avec 1 seule version — rien à comparer | 1 500 |
| **avec 2 versions ou plus → comparaison possible** | **249** |

Les documents eux-mêmes :

| Documents de texte publiés par l'Assemblée | 2 294 |
|---|---:|
| dépôts (`…B0261`) | 1 795 |
| textes de commission (`…BTC2905`) | 256 |
| textes adoptés en séance (`…BTA0314`) | 243 |
| **à lire pour couvrir les 249 textes comparables** | **795** |

**En comptant les deux chambres, 339 textes ont au moins deux versions** — mais
le site de l'Assemblée ne sert que les siennes : **30 documents du Sénat
demandés, 30 réponses 404**. Le texte sénatorial existe ailleurs, en XML, et
c'est l'objet de la fiche [`monalisa.md`](monalisa.md) (203 textes). Les deux
sources se complètent ; aucune ne se remplace.

## Le fichier répond-il ? La mesure

150 documents tirés au sort (50 dépôts, 50 textes de commission, 50 textes
adoptés) :

| | |
|---|---:|
| Réponse 200 du premier coup | 139 / 150 |
| Réponse 503 — **en demandant trop vite** | 11 |
| Reprises en espaçant les appels de 1,5 s | 10 / 11 |

**Le `robots.txt` de l'Assemblée demande 30 secondes entre deux appels**
(`Crawl-delay: 30`). Ce n'est pas un détail de politesse : c'est ce qui décide
du calendrier de la première passe (voir plus bas).

Poids d'un document : **médiane 51 ko**, jusqu'à 8,8 Mo pour une loi de
finances. Temps de lecture : **0,6 s**. L'en-tête n'offre ni `ETag` ni
`Last-Modified` — mais un texte publié ne change plus, donc le cache se fait
par identifiant.

## Le découpage en articles, et ce qu'il donne

Deux règles, dans cet ordre, et la première suffit presque toujours :

| Règle | Combien de documents |
|---|---:|
| La **classe du paragraphe** dit « ceci est un numéro d'article » (`assnat9ArticleNum`) | 139 / 149 |
| À défaut, un paragraphe dont le texte commence par « Article » | 1, et 3 en complément |

La seconde n'est pas un pis-aller de lecture : les **« petites lois » des
textes budgétaires** suivent un autre gabarit Word, sans classes. Le repère y
est le mot lui-même.

Résultat sur 149 documents lus :

| | |
|---|---:|
| Documents dont on tire au moins un article | 143 |
| **Documents sans aucun article** | **6** |
| — parce que l'Assemblée **n'a pas adopté** le texte : la « petite loi » le dit et ne contient aucun article | 4 |
| — parce que le document publié **n'est qu'une page de garde** | 2 |

Les deux pages de garde ne sont pas un défaut de lecture : **le PDF du même
document est lui aussi vide** (vérifié sur `PIONANR5L17B0499` : ni « Article »,
ni « Exposé des motifs »). C'est l'Assemblée qui n'a publié que la couverture.

**Les tableaux sont conservés en tableaux** — 21 documents sur 139 en portent.
C'est le gain le plus net sur la lecture des PDF, où ils ressortaient aplatis
colonne par colonne, « tous les mots dans le désordre ».

## Comparer deux versions : la mesure

42 paires de versions successives, prises sur 25 textes tirés au sort,
**249 articles** dans les versions d'arrivée. Les articles s'apparient par leur
**numéro** — un document ne porte aucun identifiant stable d'une version à
l'autre.

| | |
|---|---:|
| Articles retrouvés dans la version précédente | **184 (73,9 %)** |
| Articles sans équivalent | 65 |
| **… dont annoncés « (nouveau) » par la source** | **65 — la totalité** |

C'est le résultat qui compte : **l'appariement par numéro ne perd rien**. Les
articles qui n'ont pas d'avant sont ceux que la commission ou la séance vient
d'écrire, et la source le dit elle-même.

Ce que devient un article retrouvé :

| Ampleur du changement | Articles |
|---|---:|
| identique | 24 |
| 95 % du texte en commun ou plus | 56 |
| 70 à 95 % | 61 |
| 30 à 70 % | 24 |
| moins de 30 % | 19 |

## Les pièges, mesurés

**1. La renumérotation est le seul vrai risque de faux avant/après.** Un
article renuméroté se compare au mauvais. Faute d'identifiant stable, on ne
peut pas l'exclure ; on peut le mesurer : **11 articles sur 184** changent si
profondément (moins de 30 % de texte commun, des deux côtés plus de 20 mots)
qu'il s'agit peut-être d'un autre article. **6 % des comparaisons sont donc à
regarder de près**, et c'est la limite à écrire noir sur blanc sur l'écran.

**2. « (Non modifié) » n'est pas du texte, c'est un état.** La mention est un
paragraphe à part, à l'intérieur de l'article. Laissée dans le texte, elle
s'affiche comme un ajout de la commission alors qu'elle dit exactement le
contraire. Même chose pour « (nouveau) » et « (Supprimé) » dans le titre.

**3. La typographie bouge sans que le droit bouge.** Vu : `23‑569‑1` devenu
`23 ‑ 569 ‑ 1` entre deux versions. C'est le même défaut que sur les articles
de loi, et le projet sait déjà quoi en faire — descendre au caractère pour la
ponctuation et les espaces, et n'afficher le mot qu'une fois.

**4. Le numéro d'article ressort découpé.** « Article 1er » s'écrit avec un
`er` en exposant et se lit « Article 1 er ». Sans conséquence sur
l'appariement, qui compare des formes normalisées des deux côtés — mais à
normaliser avant d'afficher.

## Ce que ça coûte

| | |
|---|---:|
| Documents à lire pour les 249 textes comparables | 795 |
| Poids, à 51 ko l'un | ≈ 40 Mo |
| **Première passe, au rythme demandé par le `robots.txt` (30 s)** | **≈ 6 h 40** |
| Nouveaux documents ensuite | **3,1 par jour** (médiane des six derniers mois) |
| Soit, chaque matin | ≈ 2 min |

La première passe ne se fait qu'une fois : un texte publié ne change plus. Elle
peut s'étaler sur plusieurs nuits sans que rien n'attende.

**Aucune dépendance nouvelle.** Le HTML se découpe avec `re` et `html`, deux
modules de la bibliothèque standard, et la comparaison avec `difflib`, comme
partout ailleurs dans ce projet. La lecture des PDF, elle, demandait
`pdfplumber` et **50 Mo installés** — c'eût été la première dépendance du
projet.

## Un exemple réel

`PRJLANR5L17B2609` → `PRJLANR5L17BTC2905`, habilitation de l'assemblée de
Martinique, article 1er, tel que le calcul le rend :

> … dans les limites prévues par sa délibération n° 23‑569‑1 du 21 décembre
> 2023 …, à l'exception ~~de~~ **des** dispositions ayant un impact sur les
> charges de service public de l'énergie …

Un mot. C'est tout ce que la commission a changé à cet article, et c'est
exactement ce que l'écran doit montrer.

## En prime : l'exposé des motifs est dans le même fichier

**43 des 50 dépôts lus** portent leur exposé des motifs, sous un intertitre
`EXPOSÉ DES MOTIFS`, avant le premier article. Les absents sont les textes
transmis par le Sénat, dont le document de l'Assemblée n'est qu'une
transmission — le même constat que sur les PDF, à la même proportion.

Cela ne décide rien : **afficher un exposé de 5 900 caractères sur une fiche
mobile demande de choisir quoi en montrer**, et tronquer, c'est écrire. La
question reste ouverte, mais la matière ne coûte plus un téléchargement de
plus.
