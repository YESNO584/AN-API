# LEGI — le droit en vigueur, version par version

**Mesuré le 2026-08-31**, sur 125 archives quotidiennes réellement
téléchargées (mai à août 2026), soit 139 164 versions d'articles.

Adresse : `https://echanges.dila.gouv.fr/OPENDATA/LEGI/`

## La conclusion en une phrase

**C'est la source qui permet la superposition avant/après : chaque article de
code y existe en plusieurs versions datées, et le fichier dit lui-même quelle
version précède, et quelle loi a fait le changement.**

## Pourquoi c'est la bonne source pour un avant/après

Une loi dit rarement quelque chose en propre. Elle dit :

> Au 6° du II de l'article 131-35-1 du code pénal, après la référence
> « 223-13, », est insérée la référence « 223-14, ».

Lire ça ne montre rien. Ce qu'on veut voir, c'est **l'article 131-35-1 avant
et après**. LEGI contient exactement ça.

## Ce que contient un fichier d'article

Chaque fichier est **une version** d'un article, pas l'article. Il porte :

| | |
|---|---|
| `<NUM>` | le numéro : `131-35-1` |
| `<TITRE_TXT>` | le texte porteur : `Code pénal` |
| `<ETAT>`, `<DATE_DEBUT>`, `<DATE_FIN>` | en vigueur, abrogé, différé, et depuis quand |
| `<CONTEXTE>` | la place exacte dans le code : partie, livre, titre, chapitre |
| `<BLOC_TEXTUEL>` | **le texte complet de cette version** |
| `<VERSIONS>` | **toutes les versions de cet article**, dans l'ordre — c'est là qu'on trouve celle d'avant |
| `<LIENS>` | les textes qui l'ont modifié, avec le **numéro de la loi et son article** |
| `<NOTA>` | les conditions d'entrée en vigueur, en clair |

Le lien vers la loi est explicite :

```xml
<LIEN ... num="2" numtexte="2026-813" sens="cible" typelien="MODIFIE">
```

Traduction : *l'article 2 de la loi n° 2026-813 a modifié cet article.* Et
`2026-813` est déjà dans notre base, en `dossier.loi_numero`.

## Ce que ça donne, mesuré

Sur les seuls incréments de mai à août 2026 :

| | |
|---|---:|
| Articles modifiés par une de nos lois promulguées | 2 518 |
| dont la version antérieure est disponible | **2 446 (97 %)** |
| articles créés, donc sans avant | 6 |
| version antérieure absente | 66 |

Et la comparaison de ces 2 446 paires :

| Nature du changement | Nombre |
|---|---:|
| Retouche — plus de 90 % du texte en commun | 1 488 |
| Modification franche — 50 à 90 % | 744 |
| Réécriture — moins de 50 % | 195 |
| Texte identique (seule la numérotation change) | 19 |

Taille médiane d'un article : **259 mots avant, 287 après**, avec **94 % de
texte commun**. Autrement dit, des différences courtes et lisibles, pas des
pavés illisibles.

## Couverture par loi

| | |
|---|---:|
| Lois promulguées dans notre base | 107 |
| Lois dont on retrouve les articles modifiés | **63** |
| Articles modifiés retrouvés au total | 2 446 |
| Médiane d'articles modifiés par loi | 7 |

Les 44 lois absentes ne sont pas un manque :

| Type de loi | Retrouvée | Absente |
|---|---:|---:|
| **Ratification d'un traité** | 0 | **23** |
| Proposition de loi ordinaire | 38 | 13 |
| Projet de loi ordinaire | 13 | 5 |
| Loi organique | 6 | 3 |
| Lois de finances et de financement | 6 | 0 |

**Les 23 lois de ratification ne modifient aucun code : il n'y a rien à
superposer, et c'est normal.** Les 21 autres absences viennent de ce que je
n'ai téléchargé que quatre mois d'incréments ; leurs articles n'ont pas été
retouchés dans cette fenêtre.

Les lois de finances sont les plus lourdes : **346 articles modifiés** pour le
budget 2025, 276 pour celui de 2026.

## Le coût, et la bonne surprise

| | |
|---|---:|
| Socle complet du droit en vigueur | 1,1 Go, une fois |
| Incrément quotidien | 1 à 4 Mo |
| Quatre mois d'incréments | 572 Mo compressés, 13 Go décompressés |

**La bonne surprise : le socle de 1,1 Go n'est pas nécessaire pour les
avant/après.** Quand un article est modifié, l'incrément livre la nouvelle
version **et republie l'ancienne** (sa date de fin a changé). Vérifié sur des
versions de 2018 et 2019 : elles étaient bien dans les incréments de 2026.

Il faut en revanche décompresser beaucoup pour extraire peu : 13 Go pour
2 446 paires utiles. Un tri à la volée, sans tout écrire sur le disque,
s'impose.

Aucune dépendance nouvelle : `tar` et la bibliothèque standard suffisent.

## Un piège à connaître

Le fichier de **la loi** contient aussi des liens `MODIFIE` / `MODIFICATION`
censés désigner l'avant et l'après. **Ne pas s'y fier.** Testé sur la loi
n° 2026-813 : ils désignaient des versions à effet 2029, pas celles que cette
loi a créées.

**La méthode sûre est l'inverse** : partir de la version d'article qui cite la
loi, et prendre la version qui la précède dans sa propre liste `<VERSIONS>`.
C'est celle qui a produit les 2 446 paires ci-dessus.

## Deux exemples réels

**Code de l'éducation, article L401-1** — modifié par l'article 3 de la loi
n° 2026-813. Avant : version en vigueur depuis 2019. Après : depuis le
1er septembre 2026.

> Dans chaque école et établissement d'enseignement scolaire public, un projet
> d'école ou […] Il détermine également les modalités d'évaluation des
> résultats atteints. **Le projet d'école ou d'établissement comporte une
> partie portant sur l'utilisation des technologies numériques au sein de
> l'école ou de l'établissement ainsi que des actions menées auprès des
> élèves, du personnel et des parents en matière de sensibilisation aux effets
> nocifs d'une exposition non raisonnée aux écrans et au caractère addictif
> des réseaux sociaux, notamment au regard des enjeux de santé publique.**

**Code pénal, article 711-1** — modifié par l'article 2 de la même loi :

> les livres Ier à V du présent code sont applicables, dans leur rédaction
> résultant de la loi n° ~~2026-798 du 18~~ **2026-813 du 24** août 2026
> ~~visant à offrir des réponses immédiates aux phénomènes troublant l'ordre
> public…~~ **visant à protéger les mineurs des risques auxquels les expose
> l'utilisation des réseaux sociaux,** en Nouvelle-Calédonie, en Polynésie
> française et dans les îles Wallis et Futuna.

Comme ailleurs, le calcul est une comparaison mot à mot avec `difflib` :
aucun modèle de langage, aucun coût.

## Ce que ça ne dit pas

LEGI ne montre que le résultat **une fois la loi promulguée**. Il ne dit rien
d'un texte en cours de discussion : pour voir ce que la commission ou la
séance ont changé, il faut comparer les versions du texte lui-même — voir
[`monalisa.md`](monalisa.md) et [`textes-pdf-assemblee.md`](textes-pdf-assemblee.md).

Les deux sont complémentaires, et répondent à deux questions différentes :

- **« qu'est-ce que les parlementaires ont changé au texte ? »** → les
  versions successives du texte ;
- **« qu'est-ce que ça change au droit ? »** → LEGI.
