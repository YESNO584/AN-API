# Le droit consolidé — l'avant/après de la loi modifiée (jeu de données LEGI)

**Mesuré le 2026-08-31**, sur 125 archives quotidiennes réellement
téléchargées (mai à août 2026), soit 139 164 versions d'articles.

## La conclusion en une phrase

**Oui : quand une loi modifie un code, on peut superposer l'article avant et
l'article après, exactement — 2 446 articles modifiés par nos lois
promulguées, dont 97 % avec leur version antérieure disponible.**

## Ce que c'est

`echanges.dila.gouv.fr/OPENDATA/LEGI/` publie **le droit en vigueur**, article
par article, dans toutes ses versions successives.

Un fichier d'article n'est pas « l'article L401-1 » : c'est **une version** de
cet article, avec sa date d'entrée en vigueur et sa date de fin. Toutes les
versions du même article se citent mutuellement.

Chaque version porte :

| | |
|---|---|
| `<NUM>` | le numéro d'article (`L401-1`) |
| `<CONTEXTE>` | le code et l'endroit exact (partie, livre, titre, chapitre) |
| `<DATE_DEBUT>` / `<DATE_FIN>` | la période où cette rédaction s'applique |
| `<VERSIONS>` | **toutes les versions de l'article, dans l'ordre** — c'est ce qui donne l'« avant » |
| `<LIENS>` | les textes qui l'ont modifié, avec **le numéro de la loi et son article** |
| `<BLOC_TEXTUEL>` | le texte, en entier |
| `<NOTA>` | les conditions d'entrée en vigueur, en clair |

Exemple de lien, lu tel quel dans le fichier :

```xml
<LIEN ... num="2" numtexte="2026-813" sens="cible" typelien="MODIFIE">
```

« L'article 2 de la loi n° 2026-813 a modifié cet article. » Le raccordement
avec nos dossiers est donc immédiat : le numéro de loi est déjà dans notre
base (`dossier.loi_numero`).

## Ce que ça couvre

| | |
|---|---:|
| Lois promulguées dans notre base | 107 |
| **Retrouvées dans le droit consolidé** | **63** |
| Articles de code qu'elles modifient | 2 446 |
| Médiane d'articles modifiés par loi | 7 |
| La plus grosse : loi de finances pour 2025 | 346 articles |

Les 44 lois absentes ne sont pas un trou : **23 sont des ratifications de
traités**, qui ne modifient aucun code — il n'y a rien à superposer. Sur les
84 lois qui touchent au droit existant, 63 sont couvertes (75 %) **avec quatre
mois d'archives seulement**. Une reprise complète en couvrirait davantage.

## L'avant est disponible, et c'est la bonne surprise

Sur les 2 512 articles modifiés qui ont une version antérieure, **2 446
(97 %) ont cette version antérieure présente dans les mêmes archives
quotidiennes**.

La raison : quand une loi modifie un article, l'archive du jour republie
**aussi l'ancienne version**, dont la date de fin vient de changer. On n'a
donc **pas besoin du socle de 1,1 Go** pour calculer les comparaisons — il ne
sert qu'à connaître l'état complet du droit à un instant donné.

## La qualité des comparaisons

Sur les 2 446 paires :

| | |
|---:|---|
| 1 488 | retouche — plus de 90 % de texte commun |
| 744 | modification franche — entre 50 et 90 % |
| 195 | réécriture — moins de 50 % |
| 19 | texte identique (seule la numérotation a bougé) |

**Part de texte commun, médiane : 94 %.** Autrement dit, les écarts sont
courts et lisibles : on voit précisément ce qui change. Taille médiane d'un
article : 259 mots avant, 287 après.

## Deux exemples réels

**Code de l'éducation, article L401-1**, modifié par l'article 3 de la loi
n° 2026-813 — en vigueur au 1er septembre 2026 :

> Dans chaque école et établissement d'enseignement scolaire public, un projet
> d'école ou […] Il détermine également les modalités d'évaluation des
> résultats atteints. **Le projet d'école ou d'établissement comporte une
> partie portant sur l'utilisation des technologies numériques au sein de
> l'école ou de l'établissement ainsi que des actions menées auprès des
> élèves, du personnel et des parents en matière de sensibilisation aux effets
> nocifs d'une exposition non raisonnée aux écrans et au caractère addictif
> des réseaux sociaux, notamment au regard des enjeux de santé publique.**

**Code pénal, article 711-1**, modifié par l'article 2 de la même loi :

> […] sont applicables, dans leur rédaction résultant de la loi n°
> ~~2026-798~~ **2026-813** du ~~18~~ **24** août 2026 visant à ~~offrir des
> réponses immédiates aux phénomènes troublant l'ordre public…~~ **protéger
> les mineurs des risques auxquels les expose l'utilisation des réseaux
> sociaux,** en Nouvelle-Calédonie, en Polynésie française et dans les îles
> Wallis et Futuna.

## Trois pièges, mesurés

1. **L'« avant » fiable est celui que l'article désigne lui-même**, c'est-à-dire
   la version qui précède dans sa propre liste `<VERSIONS>`. Les liens portés
   par la *loi* (`typelien="MODIFICATION"`) peuvent désigner une version
   programmée pour plus tard — sur l'article 131-35-1 du code pénal, ils
   pointent une rédaction applicable en 2029, pas celle que la loi vient de
   créer.
2. **Légifrance renormalise la typographie.** Sur ce même article, la
   comparaison signale « 222-33,222-33-2 » devenu « 222-33, 222-33-2 » : du
   bruit qui masque la seule vraie modification (l'ajout de la référence
   « 223-14 »). Il faudra normaliser les espaces avant de comparer.
3. **Une version peut n'entrer en vigueur que plus tard** (`VIGUEUR_DIFF`,
   date de début dans le futur). C'est une information à afficher, pas une
   anomalie : la loi est promulguée, l'article ne s'applique pas encore.

## Ce que ça ne dit pas

Le droit consolidé ne montre que le résultat, **une fois la loi promulguée**.
Il ne dit rien d'un texte en discussion.

Les deux comparaisons répondent à deux questions différentes, et se
complètent :

| La question | La source |
|---|---|
| Qu'est-ce que les parlementaires ont changé au texte ? | les versions successives du texte — [`monalisa.md`](monalisa.md), [`textes-pdf-assemblee.md`](textes-pdf-assemblee.md) |
| Qu'est-ce que ça change au droit ? | le droit consolidé, cette fiche |

## Ce que ça coûte

| | |
|---|---:|
| Socle complet du droit en vigueur | 1,1 Go — **pas nécessaire pour les comparaisons** |
| Une archive quotidienne | 1 à 4 Mo |
| Quatre mois d'archives | 572 Mo compressés |
| Décompressés | 13 Go |
| Versions d'articles indexées | 139 164 |

C'est le point de vigilance : **le volume décompressé**. Il faut lire les
archives sans tout déplier, ou effacer au fur et à mesure.

Aucune dépendance nouvelle : `tar` et la bibliothèque standard suffisent.
