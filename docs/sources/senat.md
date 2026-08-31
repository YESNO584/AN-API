# Sénat — `data.senat.fr`

**Vérifié le 2026-08-31.** Chiffres relevés sur les fichiers téléchargés ce
jour-là.

## Son rôle : compléter, pas porter le produit

Le Sénat publie des données propres, à jour et utilisables. Mais **pour
suivre le parcours d'un texte, l'open data de l'Assemblée suffit déjà** :
c'est lui qui décrit les étapes des deux chambres (voir
`assemblee-nationale.md`).

Le Sénat apporte trois choses que l'Assemblée n'a pas :

1. **L'état d'un dossier en un mot**, directement exploitable pour un
   affichage (voir ci-dessous).
2. **Une profondeur historique** : les dossiers remontent à 1959.
3. **Le point de vue du Sénat** sur ses propres textes — notamment les
   propositions de loi déposées chez lui, qui ne sont pas encore à
   l'Assemblée.

## Licence

Licence propre au Sénat, consultable sur `data.senat.fr/licence/`. Elle
n'impose pas le repartage sous la même licence, contrairement à l'ODbL de La
Fabrique de la Loi.

## Le jeu central : la liste des dossiers législatifs

| | |
|---|---|
| **Adresse** | `https://data.senat.fr/data/dosleg/dossiers-legislatifs.csv` |
| **Format** | CSV, séparateur `;`, **encodage latin-1** (pas UTF-8 — un piège classique) |
| **Taille** | 3,6 Mo, 12 424 dossiers |
| **Période** | **16 janvier 1959 → 25 août 2026** |
| **Mise à jour** | Quotidienne (relevée à 01 h 14 le jour du test) |

Colonnes : `Titre`, `Type de dossier`, `Date initiale`, `URL du dossier`,
`État du dossier`, `Décision du CC`, `Date de la décision`, `Date de
promulgation`, `Numéro de la loi`, `Thèmes`.

**Il n'y a pas d'identifiant Sénat en colonne.** La clé utilisable est
`URL du dossier`, de la forme
`http://www.senat.fr/dossier-legislatif/ppl25-937.html`. C'est précisément
la valeur que l'Assemblée publie de son côté, donc le rapprochement se fait
là-dessus — attention à la variante ancienne `/dossierleg/`, qu'il faut
normaliser.

### Le champ le plus utile : « État du dossier »

Il donne l'étape en clair, sans calcul. Sur les 982 dossiers ouverts depuis
2024 :

| Dossiers | État |
|---:|---|
| 576 | Première lecture (Sénat) |
| 133 | promulgué |
| 86 | Première lecture (AN) |
| 65 | *(vide)* |
| 55 | adopté |
| 27 | non adopté |
| 14 | retiré |
| 10 | Deuxième lecture (AN) |
| 7 | Deuxième lecture (Sénat) |
| 6 | caduc |
| 1 chacun | Commission mixte paritaire, Nouvelle lecture (Sénat), Non conforme à la constitution |

Sur l'ensemble des 12 424 dossiers, deux valeurs dominent et méritent d'être
comprises avant tout affichage : **4 841 « caduc »** (textes tombés en fin de
législature) et **4 333 « promulgué »**. Un fil des textes en cours doit
écarter les deux.

Volume annuel de dossiers ouverts : 350 en 2022, 418 en 2023, 331 en 2024,
408 en 2025, 243 en 2026 jusqu'à fin août.

## Les autres jeux de données

Tailles et dates relevées le 2026-08-31 ; tous à jour du jour même.

| Jeu | Adresse | Taille | Contenu |
|---|---|---:|---|
| DOSLEG complet | `/data/dosleg/dosleg.zip` | 16,0 Mo | Base PostgreSQL complète des dossiers |
| Liste des dossiers | `/data/dosleg/dossiers-legislatifs.csv` | 3,6 Mo | **Le fichier à utiliser** |
| Propositions de loi | `/data/dosleg/ppl.csv` | 3,8 Mo | Propositions déposées au Sénat |
| Lois promulguées | `/data/dosleg/promulguees.csv` | 1,3 Mo | |
| Rapports | `/data/dosleg/rapports.csv` | — | Rapports législatifs et d'information |
| Amendements (AMELI) | `/data/ameli/ameli.zip` | **154 Mo** | |
| Débats (index) | `/data/debats/debats.zip` | 33,7 Mo | Dump SQL de 318 Mo — un **index** des interventions, pas le texte intégral |
| Comptes rendus intégraux | `/data/debats/cri.zip` | **545 Mo** | Le texte intégral des débats |
| Questions | `/data/questions/questions.zip` | **282 Mo** | |
| Sénateurs | `/data/senateurs/ODSEN_*.csv` | ~20 Mo au total | Une trentaine de fichiers, en CSV, JSON et XLS |

## Les débats — mesure du volume

Mesuré sur les 199 journées de séance de 2025 et 2026 contenues dans
`cri.zip`, balises retirées :

| | Par **journée** de séance |
|---|---:|
| Texte utile, médiane | **461 597 caractères** |
| Texte utile, moyenne | 512 724 caractères |
| La plus courte | 2 362 caractères |
| La plus longue | 1 380 630 caractères |
| Fichier XML brut, médiane | 996 Ko |

Journées de séance : **126 en 2025** (année pleine), 73 en 2026 au moment du
test.

**Un fichier par journée** (`cri/d20260721.xml`), là où l'Assemblée publie
**un fichier par séance**. Les chiffres des deux chambres ne se comparent
donc pas ligne à ligne. Rapporté à l'année, les volumes sont du même ordre :
67,4 millions de caractères au Sénat en 2025, contre 63,1 millions à
l'Assemblée.

Comme à l'Assemblée, **l'archive contient des dates futures** — jusqu'à
décembre 2026 lors du test. Ce sont les séances programmées.

## Deux pièges vérifiés

1. **L'encodage est le latin-1, pas l'UTF-8.** Lu en UTF-8, le fichier
   affiche `promulgu?` et `?tat du dossier`. C'est la première chose à
   corriger dans tout programme qui le lit.
2. **`debats.zip` n'est pas les débats.** C'est un index structuré des
   interventions (qui a parlé, sur quoi, avec un lien). Le texte intégral
   est dans `cri.zip`, quinze fois plus gros.

## Une adresse morte à ne pas recopier

La page `data.senat.fr/donnees/travaux-legislatifs-base-dosleg/`, citée
depuis le menu du site, renvoie une **erreur 404**. La bonne adresse est
`data.senat.fr/dosleg/`.
