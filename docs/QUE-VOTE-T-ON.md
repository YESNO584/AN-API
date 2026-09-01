# Peut-on savoir exactement ce qui est voté ?

**Mesuré le 2026-08-31**, sur les 8 434 scrutins de l'Assemblée, les 4 764 du
Sénat, les 10 700 étapes enregistrées, et 36 lois promulguées retrouvées dans
le Journal officiel.

## La réponse en trois phrases

**Oui pour les décisions : à chaque lecture, l'open data nomme le texte mis
aux voix et le texte qui en sort — 392 lectures sur 465 (84 %), les deux
chambres confondues.** Oui aussi pour le détail : le texte de chaque
amendement et son sort sont connus pour 90 482 amendements. **Non pour un
seul point, et il est mineur : le détail nominal d'un vote (qui a voté quoi)
n'existe que quand il y a eu scrutin public**, ce qui est rare.

Ce qui manque n'est donc pas l'information sur *ce qui est voté* : c'est le
**contenu** des textes nommés. Voir [`sources/monalisa.md`](sources/monalisa.md)
et [`sources/textes-pdf-assemblee.md`](sources/textes-pdf-assemblee.md).

## « Avant/après » veut dire deux choses, et les deux marchent

C'est la distinction qui manquait à la première version de cette note.

**Décidé le 2026-09-01 : on traite d'abord le second cas** — ce que la loi
change au droit — et on reprendra le premier plus tard. Voir
[`CE-QUE-LA-LOI-CHANGE.md`](CE-QUE-LA-LOI-CHANGE.md), qui reprend cette
question seule et dit ce qui est faisable.

**L'avant/après du texte en discussion** — la version qui entre dans une
étape et celle qui en sort. **Calculable**, et déjà démontré : 203 textes côté
Sénat (Monalisa), 249 côté Assemblée (les PDF), 319 en tout. La seule chose
qui ne marche pas est de sauter les étapes : comparer le dépôt à la loi
finale, parce que les articles sont renumérotés en route.

**L'avant/après de la loi qui est modifiée** — l'article du code tel qu'il
était, et tel qu'il devient. **Calculable aussi**, et c'est la superposition
la plus lisible des deux : 2 446 articles de code modifiés par nos lois
promulguées, dont 97 % avec leur version antérieure disponible, 94 % de texte
commun en médiane. Voir [`sources/droit-consolide.md`](sources/droit-consolide.md).

## Ce que dit chaque source

### Les décisions : complètes, dans les deux chambres

Une lecture se termine par un acte de décision. L'open data en compte 649 pour
la 17e législature, et **616 portent leur conclusion (95 %)** : adoptée,
rejetée, modifiée, conforme.

| | Actes de décision | Avec conclusion |
|---|---:|---:|
| Assemblée | 304 | 274 (90 %) |
| Sénat | 218 | 217 (100 %) |
| Commission mixte paritaire, Conseil constitutionnel | 127 | 125 (98 %) |

**C'est le point important : le résultat d'une lecture ne dépend pas de
l'existence d'un scrutin public.** La plupart des textes sont votés à main
levée, sans scrutin ; la décision est quand même publiée.

### Le texte mis aux voix : nommé, mais pas fourni

Pour chaque lecture, les actes citent les documents concernés. En les
rassemblant par lecture :

| | Lectures avec décision | Dont le texte voté **et** le texte issu du vote sont nommés |
|---|---:|---:|
| Assemblée | 202 | 152 (75 %) |
| Sénat | 218 | 199 (91 %) |
| CMP et autres | 45 | 41 (91 %) |
| **Total** | **465** | **392 (84 %)** |

Autrement dit : on sait dire « le 25 juin 2025, l'Assemblée a voté sur le
texte n° 1640 issu de sa commission, et en a tiré le texte adopté n° 163 ».
Ce que l'open data ne donne pas, c'est **ce qu'il y a dedans**.

### Les scrutins : un détail précieux, mais partiel et mal raccordé

**Aucun scrutin ne dit sur quelle version du texte il porte.** Le champ prévu
pour ça, `referenceLegislative`, est **vide dans les 8 434 scrutins** de
l'Assemblée. Vérifié, pas supposé.

Pire pour le raccordement : **5 826 scrutins sur 8 434 (69 %) ne nomment même
pas leur dossier** — ils ne portent qu'un libellé en toutes lettres. En
croisant avec les dossiers qui, eux, citent leurs scrutins, le socle en
rattache aujourd'hui 2 748, soit un tiers.

Sur quoi vote-t-on, quand on vote par scrutin public ?

| Objet du scrutin | Assemblée | Sénat (depuis juillet 2024) |
|---|---:|---:|
| Amendement | 7 218 | 402 |
| Article | 872 | 69 |
| **L'ensemble du texte** | **212** | **174** |
| Motion de procédure | 81 | 35 |
| Autre | 51 | 16 |

Deux enseignements :

- **Le scrutin public sert surtout à trancher des amendements**, pas à adopter
  des textes. À l'Assemblée, 86 % des scrutins portent sur un amendement ou
  un article.
- **Le Sénat s'en sert bien moins**, mais proportionnellement bien plus pour
  le vote final : 174 de ses 696 scrutins portent sur l'ensemble d'un texte.

Côté Sénat, le raccordement est encore plus mauvais : **aucune table ne relie
un scrutin à un dossier.** La table `scr` ne contient qu'un intitulé libre.
Le rapprochement ne pourrait se faire que sur ce texte.

### Les amendements : c'est là que le détail existe déjà

Le socle stocke **109 854 amendements**, avec leur texte complet et l'article
visé. **90 482 portent leur sort** : adopté, rejeté, tombé, retiré, non
soutenu.

Et le raccordement fonctionne : sur les scrutins d'amendement qui nomment leur
dossier, **2 197 sur 2 260 (97 %) retrouvent l'amendement correspondant** par
son numéro.

## Le repli : les lois promulguées

### Le texte officiel est récupérable, mais pas là où on le croit

`legifrance.gouv.fr` **refuse les accès automatiques** : 403 et une page
« Just a moment… » de protection anti-robot, sur l'adresse même que publie
l'Assemblée. Ce n'est pas le proxy : aucune erreur de relais.

En revanche, la DILA publie le Journal officiel en open data, et **ça marche** :
`echanges.dila.gouv.fr/OPENDATA/JORF/`. Voir
[`sources/journal-officiel.md`](sources/journal-officiel.md).

Le raccordement est immédiat : chaque loi y porte son **numéro** (`2026-813`)
et son **NOR** (`ECOX2602236L`), les deux déjà présents dans notre base.

### Mais comparer une loi à son texte d'origine ne veut presque rien dire

C'est le résultat le plus utile de cette mesure. Sur 26 lois promulguées en
2026, comparées article par article :

| Comparaison | Articles au même numéro | **Dont au même contenu** |
|---|---:|---:|
| Texte déposé → loi promulguée | 77 % | **15 %** |
| Dernier texte adopté → loi promulguée | 84 % | **67 %** |

**Un texte est renuméroté de fond en comble pendant son parcours.** Sur la loi
n° 2026-813 (réseaux sociaux et mineurs), le texte déposé avait 7 articles, la
loi en a 3 : l'article 1er du dépôt et l'article 1er de la loi n'ont que 2 %
de mots en commun — ce ne sont pas les mêmes dispositions.

Le « diff original contre loi finale » que l'on imagine spontanément produirait
donc surtout de faux écarts. **La comparaison qui a du sens est celle de deux
versions consécutives**, étape par étape.

### Un bonus du Journal officiel

Le texte publié signale les dispositions censurées :

> [Dispositions déclarées non conformes à la Constitution par la décision du
> Conseil constitutionnel n° 2026-911 DC du 14 août 2026.]

C'est la seule source qui dise ce que le Parlement a voté **et** que le
Conseil constitutionnel a retiré.

## Il y a bien un avant et un après — deux, même

Ma réponse précédente a brouillé un point. « Avant/après » recouvre deux
choses, et **les deux sont calculables** :

1. **L'avant/après du texte en discussion** — ce que la commission ou la
   séance ont changé. Marche entre deux versions **consécutives** : c'est le
   diff Monalisa côté Sénat et le diff PDF côté Assemblée. Ce qui ne marche
   pas, c'est seulement de sauter toutes les étapes d'un coup (dépôt → loi
   finale), à cause de la renumérotation.
2. **L'avant/après du droit lui-même** — l'article de code avant et après la
   loi. **2 446 paires calculées, 97 % de celles attendues**, avec 94 % de
   texte commun en médiane : des différences courtes et lisibles. Voir
   [`sources/droit-consolide.md`](sources/droit-consolide.md).

## Ce que je recommande

**Par ordre de valeur rendue rapportée à l'effort :**

1. **Afficher, pour chaque lecture, ce qui a été décidé et sur quel texte.**
   Les données sont déjà en base — 616 décisions, 392 lectures avec leur avant
   et leur après nommés. Aucun téléchargement nouveau, aucune dépendance.
2. **Afficher le détail des amendements** : texte, auteur, sort. Déjà en base
   aussi, pour 90 482 amendements.
3. **Ensuite seulement, le contenu des textes** — Monalisa côté Sénat (gratuit,
   structuré), les PDF côté Assemblée (86 % de fidélité, une dépendance).
   C'est là que se trouve le vrai coût, et c'est ce qui permet le diff.
4. **Le droit consolidé** (`sources/droit-consolide.md`) : pour chaque loi
   promulguée, l'article de code avant et après. C'est la superposition la
   plus parlante pour un lecteur, et elle ne demande aucune dépendance —
   seulement de la place disque pendant le traitement.
5. **En dernier, le Journal officiel** : 1,6 Go pour l'historique. Utile pour
   le texte officiel et les censures constitutionnelles, mais **pas** pour un
   diff contre le texte d'origine, qui n'a pas de sens.

Le rattachement des 5 686 scrutins orphelins à leur dossier est un chantier à
part : le rapprochement par titre exact en retrouve 1 556 sans ambiguïté ;
une méthode plus souple en retrouve davantage mais se trompe souvent. À ne
tenter que si le détail nominal des votes devient un besoin réel.
