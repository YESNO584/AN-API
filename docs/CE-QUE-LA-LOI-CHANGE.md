# Montrer ce qu'une loi change au droit — ce qui est faisable

**Mesuré le 2026-09-01.** Cette note traite **uniquement** de la comparaison
entre le droit avant la loi et le droit après. La comparaison entre versions
successives d'un texte en cours de navette est mise de côté — voir la fin de
cette page.

## La réponse en une phrase

**C'est fait.** Les chiffres ci-dessous sont ceux de la récupération complète
du 2026-09-02 : les 419 archives du dépôt lues, **72 de nos 107 lois changent
le droit écrit**, et pour chacune l'application affiche article par article la
rédaction d'avant et celle d'après.

| | |
|---|---:|
| Archives lues | 419 (le socle de 1,1 Go + 418 quotidiennes) |
| **Lois qui changent le droit** | **72 sur 107** |
| Articles changés | 5 713 |
| **dont comparables** (rédaction d'avant retrouvée) | **4 287 — 75 %** |
| créés par la loi : rien à comparer, c'est normal | 1 425 |
| **rédaction d'avant désignée mais introuvable** | **1** |
| Articles par loi — médiane | 10 |
| La plus grosse : loi de finances pour 2025 | **1 056 articles** |

Ce que les lois font : **4 164 modifications**, 1 078 créations, 457
abrogations, 101 transferts ou déplacements.

Les 35 lois sans changement se répartissent en **23 ratifications de traités**
— elles n'ont rien à modifier, c'est leur nature — et 12 lois qui créent des
règles autonomes sans les insérer dans un code : une loi spéciale de budget,
l'élévation d'Alfred Dreyfus au grade de général, la reconnaissance d'un
préjudice.

## Ce qu'on peut montrer, concrètement

Pour la loi n° 2026-813 (protection des mineurs sur les réseaux sociaux),
lue dans les fichiers :

> **Cette loi modifie 7 articles.**
>
> | Article | Où | En vigueur le |
> |---|---|---|
> | article 6 | LOI n° 2004-575 du 21 juin 2004 | 26 août 2026 |
> | article L495-1 | Code de l'éducation | 1er septembre 2026 |
> | article L511-5 | Code de l'éducation | 1er septembre 2026 |
> | … | | |

Et pour chacun, les deux rédactions superposées, comme ici sur l'article
L401-1 du code de l'éducation (extrait réel, gras = ce que la loi ajoute) :

> Dans chaque école et établissement d'enseignement scolaire public, un projet
> d'école ou […] Il détermine également les modalités d'évaluation des
> résultats atteints. **Le projet d'école ou d'établissement comporte une
> partie portant sur l'utilisation des technologies numériques […] ainsi que
> des actions menées auprès des élèves, du personnel et des parents en matière
> de sensibilisation aux effets nocifs d'une exposition non raisonnée aux
> écrans et au caractère addictif des réseaux sociaux.**

## Quatre choses différentes qu'une loi peut faire

C'est le point à comprendre avant de dessiner l'écran : **« avant/après » ne
s'applique qu'à un cas sur quatre.** Compté sur nos lois :

| Ce que fait la loi | Liens comptés | Ce qu'on affiche |
|---|---:|---|
| **MODIFIE** un article existant | 2 711 | Un avant **et** un après — la superposition |
| **CREE** un article | 631 | Pas d'avant. Seulement le texte neuf |
| **ABROGE** un article | 170 | Pas d'après. Seulement ce qui disparaît |
| **TRANSFERE** / **DEPLACE** | 38 | Même texte, ailleurs. À signaler, pas à comparer |
| *CITATION* | *5 520* | *La loi cite l'article sans y toucher. À ignorer* |

Les citations sont deux fois plus nombreuses que les modifications : **les
compter comme des changements ferait dire à l'application n'importe quoi.**

## La couverture

| | |
|---|---:|
| Lois promulguées suivies | 107 |
| **Lois qui changent le droit écrit** | **64** |
| Lois qui ne changent aucun article | 43 |

Sur les 43, **23 sont des ratifications de traités** — vérifié : aucune ne
touche à un article de code, et c'est normal, elles autorisent la France à
signer un accord. Les 20 autres sont soit des lois autonomes (elles créent des
règles sans les insérer dans un code), soit hors de la fenêtre d'archives
utilisée pour cette mesure.

Combien d'articles par loi :

| | |
|---|---:|
| Médiane | **8 articles** |
| Le minimum | 1 article (13 lois sont dans ce cas) |
| Le maximum | **574 articles** — la loi de finances pour 2025 |

Les lois de finances et de sécurité sociale écrasent tout : cinq d'entre elles
occupent les premières places, de 166 à 574 articles. **Un écran conçu pour
huit articles doit prévoir le cas des cinq cents.**

Qualité des superpositions, sur 2 446 paires déjà calculées :

| | |
|---:|---|
| 1 488 | retouche — plus de 90 % de texte commun |
| 744 | modification franche — 50 à 90 % |
| 195 | réécriture — moins de 50 % |
| 19 | texte identique (seule la place a changé) |

**Part de texte commun, médiane : 94 %.** Les écarts sont donc courts : on voit
précisément ce qui bouge, sans noyer le lecteur.

## D'où viennent les données

`echanges.dila.gouv.fr/OPENDATA/LEGI/` — le jeu **LEGI**, publié par la DILA
sous licence ouverte. Aucun compte, aucune clé, aucune limite d'appels.

Deux choses y sont publiées :

| | Poids | Ce que c'est | Ce qu'il couvre |
|---|---:|---|---|
| **Un socle**, `Freemium_legi_global_20250713` | 1,1 Go | Tout le droit, **toutes rédactions confondues** | Du passé jusqu'au 13 juillet 2025 |
| **418 archives quotidiennes** | 1,8 Go au total | Ce qui a changé ce jour-là | Du 12 juillet 2025 à aujourd'hui |

**Le socle contient bien l'histoire, pas seulement le droit en vigueur.** Je
l'ai vérifié en le lisant : sur les 60 000 premières rédactions rencontrées,
**58 432 sont des rédactions périmées**, et la plus ancienne commence en 1866.
(Cette proportion vaut pour le début du fichier, pas pour l'ensemble ; ce qui
compte est que les rédactions passées y sont, en nombre.)

C'est ce qui rend la couverture complète atteignable : nos lois vont du
15 novembre 2024 au 24 août 2026. **32 sont antérieures au socle** — leur
histoire y est. **75 lui sont postérieures** — les quotidiennes les portent.

Chaque rédaction d'article dit elle-même quelle loi l'a changée :

```xml
<LIEN num="2" numtexte="2026-813" sens="cible" typelien="MODIFIE">
```

« L'article 2 de la loi n° 2026-813 a modifié cet article. » Le raccordement
avec notre base est donc immédiat : `dossier.loi_numero` contient déjà ce
numéro. **Rien à deviner, rien à rapprocher par le titre.**

## Ce que ça coûte

| | |
|---|---|
| Téléchargement, une fois | 2,9 Go (socle + quotidiennes) |
| Téléchargement, ensuite | 1 à 4 Mo par jour |
| **Lire le socle en entier** | **15,7 minutes**, mesuré |
| Place sur le disque | **Aucune, si on lit en flux** |
| Dépendances nouvelles | **Aucune** — `tarfile` et `difflib` sont dans Python |
| Modèle de langage | Aucun. La comparaison est un calcul mot à mot |

La lecture complète du socle a été faite, chronométrée : **942 secondes**, soit
15,7 minutes, pour **2 557 045 fichiers dont 1 750 418 rédactions d'articles**,
et **9,5 Go de données décompressées qui n'ont jamais touché le disque**.

**Le piège est la place disque, et il se contourne.** Déplié, le socle occupe
**9,5 Go** — et 2,5 millions de fichiers minuscules, ce qui est pire que le
volume pour un système de fichiers. Il ne faut donc pas le déplier : on lit
l'archive compressée en flux, fichier par fichier, et on ne garde que les
rédactions qui nous concernent. C'est mesuré, pas supposé : la passe complète
ci-dessus n'a écrit rien du tout sur le disque.

Quinze minutes tiennent largement dans une exécution GitHub Actions, et ce
traitement ne se refait pas : ensuite, seules les archives quotidiennes de 1 à
4 Mo sont à lire.

## L'ordre dans lequel je le ferais

1. **Une passe sur le socle et les quotidiennes**, en flux, pour construire un
   index : pour chaque numéro de loi, la liste des rédactions d'articles
   qu'elle a touchées, et de quelle façon. C'est le seul traitement lourd, et
   il ne se fait qu'une fois.
2. **Pour chaque rédaction touchée, retrouver celle d'avant.** Elle est
   désignée par l'article lui-même, dans sa liste `<VERSIONS>` — c'est le
   repère fiable. *Ne pas* passer par les liens portés par la loi : mesuré,
   ils désignent parfois une rédaction prévue pour bien plus tard.
3. **Normaliser les espaces avant de comparer.** Légifrance retouche la
   typographie ; sans cette précaution, « 222-33,222-33-2 » devenu
   « 222-33, 222-33-2 » apparaît comme un changement et masque le vrai.
4. **Publier un fichier par loi**, à côté des fichiers déjà publiés.
5. **Afficher** : d'abord le compte (« cette loi modifie 7 articles, en crée 2 »),
   puis chaque article dépliable, avec les deux rédactions superposées.

## Trois choses à décider, qui ne sont pas techniques

- **Les entrées en vigueur différées.** Une loi promulguée peut ne s'appliquer
  qu'en 2029. Le fichier le dit (`VIGUEUR_DIFF`). C'est une information à
  montrer, pas une anomalie — mais il faut choisir comment.
- **Les lois de finances.** 574 articles ne se parcourent pas à la main sur un
  téléphone. Il faut soit regrouper par code, soit n'en montrer qu'un extrait.
- **Les 43 lois qui ne changent aucun article.** Leur fiche doit dire pourquoi
  — « ce texte autorise la ratification d'un traité » — et non rester vide.

## Ce qui est mis de côté, et qu'on reprendra

**Ce que les parlementaires ont changé au texte pendant son parcours** — le
texte déposé contre le texte voté. C'est la question « B », explicitement
reportée par l'utilisateur le 2026-09-01.

Ce qu'on sait déjà à son sujet, pour ne pas le redécouvrir :

- **C'est calculable entre deux étapes consécutives** : 203 textes côté Sénat
  (XML Monalisa, gratuit et structuré), 249 côté Assemblée (les PDF, lisibles
  à 86 %), 319 en tout.
- **Ce qui ne marche pas, c'est de sauter les étapes** : comparer le dépôt à la
  loi promulguée n'a presque aucun sens, parce que les articles sont
  renumérotés en chemin, et deux versions ne s'apparient que par leur numéro.
- Voir `sources/monalisa.md`, `sources/textes-pdf-assemblee.md` et
  `QUE-VOTE-T-ON.md`.

**Et l'argumentaire contradictoire** — exposé des motifs, amendements, débats —
est une troisième brique, à ajouter après. L'exposé des motifs est déjà
localisé : il est dans le PDF de dépôt, présent pour 100 % des textes déposés
d'abord à l'Assemblée (`sources/textes-pdf-assemblee.md`). Les 109 854
amendements, avec leur texte et leur sort, sont **déjà en base**.
