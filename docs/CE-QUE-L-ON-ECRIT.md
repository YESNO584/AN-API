# Ce que l'on écrit, et ce que l'on recopie

**Relevé le 2026-09-10** sur `maquette/feed.html`, `socle/extraction.py`,
`socle/legi.py`, `socle/publier.py` et `socle/descriptions.json`. Écrit pour
répondre à une question simple : dans tout ce que l'application affiche,
qu'est-ce qui vient du Parlement, et qu'est-ce qui vient de nous ?

## En une phrase

**Une seule rubrique de l'application est écrite par une intelligence
artificielle — la description, en haut de la fiche d'un texte — et elle le dit
à l'écran.** Tout le reste est recopié de la source, écrit à la main dans le
code, ou calculé. Aucun texte de la source n'est reformulé nulle part.

## Les quatre catégories

| Marque | Ce que c'est | Qui l'a écrit |
|---|---|---|
| **S** | **Source** — le mot pour mot de l'Assemblée, du Sénat ou du droit consolidé | Le Parlement, la DILA |
| **N** | **Nous** — libellés, explications, avertissements, fixés une fois pour toutes dans le code | Un humain, à la main |
| **C** | **Calculé** — comptes, pourcentages, dates mises en forme, classements | Le programme, à partir de la source |
| **IA** | **La description d'un texte, et rien d'autre** | Une intelligence artificielle, hors ligne |

Un **C** n'est jamais une phrase inventée : c'est un chiffre, une date, ou le
choix d'un mot dans une liste fermée écrite à l'avance.

## L'exception : la description d'un texte

C'est la seule entorse à la règle, et elle est délibérée. Une fiche s'ouvrait
sur un titre officiel — « Projet de loi portant diverses dispositions
d'adaptation au droit de l'Union européenne… » — qui ne dit pas de quoi le
texte parle. La description répond à cette question en deux phrases.

**Ce qu'elle est**

| | |
|---|---|
| Où elle s'affiche | En haut de la fiche d'un texte, sous les étiquettes, avant les liens vers les sources. Nulle part ailleurs |
| Comment elle est signalée | Une icône et une mention sous le texte — « Générée par une IA ». Au survol sur un ordinateur, la mention complète ; au toucher sur un téléphone, une explication qui dit d'où elle vient et qu'elle peut se tromper |
| D'où elle vient | `socle/descriptions.json`, un fichier **versionné**, écrit hors ligne. C'est la seule donnée du projet qui ne vienne pas d'une source publique |
| Sur quoi elle s'appuie | Le titre du texte, sa nature, et ce que la loi change au droit — tous lus dans les données publiées |
| Ce qui se passe s'il n'y en a pas | La rubrique ne s'affiche pas. Pas de cadre vide, pas de phrase d'attente |

**Ce qu'elle ne fait pas**

- Elle **ne remplace aucun texte de la source**. Le titre, le parcours, les
  votes, les prises de parole et le texte des articles restent au mot près.
- Elle **ne s'étend pas ailleurs**. Étendre l'exception à une autre rubrique
  demande une décision écrite ici, pas une initiative de session.
- Elle **n'est pas produite par la chaîne de publication**. Aucun appel à un
  service d'IA, aucune clé d'accès, aucune dépendance : le fichier est déjà
  écrit quand la publication le lit.
- Elle **ne vieillit pas toute seule**. Une description écrite avant qu'un
  texte n'avance dans son parcours reste telle quelle. Sa date est stockée et
  affichée ; rien ne la périme automatiquement.

**Une entrée peut aussi être écrite par une personne.** Le fichier porte alors
`origine: "humain"`, et la mention à l'écran change en conséquence. C'est prévu
dès maintenant pour que remplacer une description générée par une description
rédigée ne demande aucun changement de code.

## Ce que la chaîne de publication ne fait toujours pas

Les descriptions sont écrites **hors ligne** et déposées dans un fichier. Le
programme qui récupère, range et publie les données, lui, n'appelle aucun
modèle de langage. Quatre constats, vérifiables en une commande chacun :

| Ce qui a été vérifié | Résultat |
|---|---|
| Recherche de `anthropic`, `openai`, `gpt`, `llm`, `claude`, `mistral`, `cohere`, `ollama` dans tout le code | Aucune occurrence |
| Les `import` de tous les fichiers de `socle/` | Bibliothèque standard de Python uniquement |
| La publication quotidienne (`.github/workflows/donnees.yml`) | Aucun `pip install` : rien n'est installé, donc rien ne peut appeler un service |
| La comparaison de deux rédactions d'un article | `difflib`, module standard (`socle/legi.py`, `morceaux`) — le code le dit : « aucun modèle de langage, aucun coût, et un résultat qui ne dépend que des deux textes » |

## L'inventaire, écran par écran

Les textes entre guillemets montrent la **forme** de ce qui s'affiche. Sauf
quand une valeur est attribuée à une mesure, **leurs chiffres, dates et
numéros sont fictifs** : ils illustrent la mise en page, ils ne décrivent pas
l'état des données un jour donné. Les chiffres qui, eux, sont vérifiés sont
rassemblés en fin de document.

### Bandeau, en-tête, pied de page

| Texte affiché | |
|---|---|
| « Maquette — données réelles, lues en direct sur le socle du projet » | **N** |
| « Où en sont les lois », « Filtres », « Chercher dans les titres… » | **N** |
| « **2 151** textes, dont 107 devenus des lois » | **C** (les chiffres) + **N** (les mots) |
| Le pied de page entier (source, licence, « Rien n'est écarté ») | **N** |
| « Dernière mise à jour : … » | **C** (date de la publication) |

### La carte d'un texte, dans le fil

| Texte affiché | | D'où il vient |
|---|---|---|
| Le titre du texte | **S** | `titreDossier.titre`, seuls les espaces de bord retirés |
| « Assemblée nationale », « Sénat », « Les deux chambres » | **N** | la source ne donne que `AN` / `SN` |
| « Proposition de loi », « Budget de l'État »… | **N** | version raccourcie du libellé de procédure. **Un type absent de notre table s'affiche mot pour mot** (**S**) |
| Le sigle du groupe de l'auteur | **S** | |
| Le point de couleur du groupe | **N** | convention d'affichage — l'open data n'en publie aucune, et la page le dit |
| « 1re lecture », « Nouvelle lecture » | **S** | `libelleActe.libelleCourt` |
| Le dernier acte (« Dépôt », « Renvoi en commission ») | **S** | `libelleActe.nomCanonique` |
| La conclusion (« Adopté », « Modifié ») | **S** | `statutConclusion.libelle` |
| « 12 mars 2026 » | **C** | date de la source, au format français |
| « à l'arrêt depuis 2 ans » | **C** | calcul sur la date de la source |
| « prévu le 14 octobre 2026 » | **C** | date d'un acte futur de la source |
| « Rejeté », « Non adopté », « Caduc », « Retiré » | **N** | les trois derniers **reprennent le mot du Sénat** ; « Rejeté » est notre déduction à partir des actes |
| « le Sénat écrit « caduc » » | **S** | citation littérale de son champ *État du dossier* |
| « loi n° 2026-796 » | **S** | `codeLoi` |
| « texte officiel » (lien) | **N** (le mot) + **S** (l'adresse) | |

### Le bandeau de vote sur la carte

| | |
|---|---|
| « Adopté » / « Rejeté » | **N**, choisi d'après le code `sort` de la source |
| « 172 pour · 68 contre · 12 abst. » | **S** |
| « 43 votes enregistrés · sur des amendements ou des articles » | **C** + **N** |

### Ce qu'une loi change, sur la carte

Tout ce bloc est **calculé** à partir du droit consolidé, avec nos mots autour :

- « S'applique depuis le 1er janvier 2026 » — **C**
- « Ne s'applique pas encore en entier — 14 articles sur 130 entrent en vigueur le… » — **C**
- « 3 articles attendent un décret pour s'appliquer. » — **C**
- « Ne modifie aucun article de loi existante — ce texte autorise la
  ratification d'un traité. » — **N**, et la raison n'est donnée que quand le
  **type de dossier de la source** l'explique de lui-même
- « Voir les 130 articles qu'elle change et les 5 qu'elle ajoute › » — **C**

### Colonnes, frise du bas, onglets

| | |
|---|---|
| « Dépôt », « Commission », « Séance publique », « Navette », « Sortie de navette », « Après le vote », « Promulguée », « Arrêté en chemin » | **N** — ce sont **nos** noms d'étapes, pas ceux de la source |
| « étape 3 sur 6 », « parcours terminé », « plus examinés » | **C** — notre classement des codes d'actes |
| Le compte de textes sous chaque colonne | **C** |
| Onglets « Textes » et « Travaux » | **N** |
| Noms des colonnes de *Travaux* (« Commission d'enquête », « Mission d'information »…) | **S** — libellés de procédure de la source |
| Leurs sous-titres (« Une enquête aux pouvoirs renforcés, sur un sujet précis ») | **N** — 9 en tout |

### Le panneau des filtres

Les libellés sont **N** (« Où le texte se trouve », « Dernier mouvement »,
« À l'arrêt depuis 1 an », « Tout effacer »…), les chiffres à côté sont **C**.
Une exception : *Nature du texte* affiche le libellé de la source (**S**)
quand il ne figure pas dans notre table de raccourcis.

### La fenêtre d'explication (le bouton ⓘ)

**Tout ce qui s'affiche ici est écrit par nous.** C'est le plus gros bloc de
prose à nous dans l'application, et c'est sa raison d'être : chaque élément
affiché doit pouvoir dire, en français simple, ce qu'il est.

| Famille | Combien | Où |
|---|---:|---|
| Descriptions d'étape (`ETAPES`) | 8 | `maquette/feed.html` |
| Descriptions d'issue (`ISSUES`) | 4 | `maquette/feed.html` |
| Descriptions de nature de texte (`TYPES`) | 10 | `maquette/feed.html` |
| Descriptions de chambre (`CHAMBRES`) | 3 | `maquette/feed.html` |
| Explications générales (`EXPLICATIONS`) | 15 | `maquette/feed.html` |
| Descriptions de portée de vote (`PORTEES`) | 5 | `maquette/feed.html` |
| Descriptions de genre d'événement (`GENRES`) | 5 | `maquette/feed.html` |
| Descriptions de champ d'étape (`CHAMPS_ETAPE`) | 11 | `maquette/feed.html` |
| Descriptions d'issue publiées avec les données (`FINS`) | 6 | `socle/extraction.py` |
| Descriptions de portée publiées avec les données (`PORTEES`) | 5 | `socle/extraction.py` |
| Descriptions de catégorie de travaux (`TRAVAUX`) | 9 | `socle/publier.py` |

La **valeur** montrée en haut de cette fenêtre vient toujours des données.

### La fiche d'un texte

| | | |
|---|---|---|
| Le titre | **S** | |
| **La description, sous les étiquettes** | **IA** | `socle/descriptions.json` — voir l'exception ci-dessus |
| « Générée par une IA », et l'explication au toucher | **N** | |
| « Dossier à l'Assemblée », « Dossier au Sénat », « Texte au Journal officiel » | **N** (les mots) + **S** (les adresses) | |
| Auteur et cosignataires : civilité, prénom, nom, nom du groupe | **S** | |
| « Auteur du texte », « et 42 autres. » | **N** / **C** | |
| Le parcours : date, libellé de l'acte, lecture, conclusion | **S** | |
| La précision d'étape (« 2e séance », « 15:00 ») | **C** | reformulation d'**un mot** de la source : l'agenda écrit « Deuxième », nous écrivons « 2e séance » |
| Le nom des champs dépliés (« Qui s'est réuni », « Le texte qui en sort ») | **N** | |
| **Leur valeur** (organe, numéro de document, rapporteurs, saisine, décision) | **S** | seule retouche : la ponctuation de tête de la « formule » du document est enlevée |
| « L'open data ne publie rien de plus sur cette étape que sa nature et sa date. » | **N** | |
| Détail d'un vote : objet du scrutin, sigles, décomptes | **S** | |
| L'ordre des groupes, de la gauche à la droite de l'hémicycle | **C** | **mesuré** sur les numéros de siège, pas publié par la source |
| « Groupes rangés comme dans l'hémicycle… », « n'a pas voté » | **N** | |
| « Aucun scrutin public sur ce texte… » | **N** | |

### Les amendements

| | |
|---|---|
| L'avertissement en tête du bloc | **N** |
| Numéro, article visé, sort, nom et groupe de l'auteur | **S** |
| **Le dispositif** — l'instruction de l'amendement | **S**, mot pour mot, balises HTML retirées |
| Le vert et le rouge dessus | **C** — nous colorons ce que **la source met elle-même entre guillemets**, en suivant le verbe de l'instruction. Le code l'annonce comme « une aide de lecture, pas une vérité juridique ». **Le texte modifié n'est jamais reconstitué** |
| L'exposé sommaire | **S**, coupé à 400 caractères |
| « 150 amendements affichés sur 19 510 » | **C** |

### Ce que les groupes en ont dit

| | |
|---|---|
| L'avertissement en tête | **N** |
| Nom de l'orateur, qualité, sigle du groupe, nom de la section, date | **S** |
| **Le texte de la prise de parole** | **S**, **entier** — rien n'est coupé (médiane 4 260 caractères) ; le « Lire la suite » ne fait que replier à l'écran |
| « Les comptes rendus n'ont pas pu être récupérés ce matin… » | **N** |

### L'écran « ce que cette loi change »

| | |
|---|---|
| Tuiles « modifiés / créés / abrogés / nouveaux » | **N** (les mots) + **C** (les comptes) |
| Nom du code (« Code de l'éducation ») | **S** |
| « Textes non codifiés » | **N** — notre repli quand la source ne nomme rien |
| Pastille « modifié », « créé », « abrogé », « transféré », « déplacé » | **N** — traduction du mot de la source (`MODIFIE`…), une fois pour toutes |
| Pastille « nouveau » | **N** — un article que la loi a écrit elle-même |
| « Article 12 » | **S** |
| Un article sans numéro | **S** — le **début de son propre texte**, coupé à 62 caractères |
| « 19 % du texte a changé » | **C** |
| « 340 mots, texte nouveau » | **C** |
| « rédaction précédente non retrouvée » | **N** — un trou dans nos données, dit comme tel |
| « texte pas encore publié par la source » | **N** — la source a livré l'article sans son texte |
| « 7 articles retouchés sans changement de fond — seule la ponctuation ou les espaces ont bougé. » | **N** + **C** |
| L'avertissement final sur les articles seulement cités | **N** |

### L'écran d'un article de loi

| | |
|---|---|
| « Article 12 », ou le début du texte à défaut | **S** |
| « Code pénal — rédaction en vigueur le 1er janvier 2026 » | **N** (les verbes) + **S**/**C** (le code et la date) |
| « à une date non encore fixée » | **N** |
| Les quatre encadrés d'avertissement (article sans numéro, texte en attente, article créé, rédaction précédente non retrouvée) | **N** |
| Boutons « Ce qui change / Texte en vigueur / Texte précédent » et la légende des couleurs | **N** |
| **Le texte de l'article, avant et après** | **S** — le texte officiel publié par la DILA, seuls les espaces normalisés |
| Le barré rouge et le souligné vert | **C** — `difflib`, mot à mot, descendu au caractère quand seule la ponctuation bouge |
| Pour un article que la loi a écrit : ses renvois sont retirés | **S moins une coupe**, repérée sur la **structure** de la source (`<blockquote>`), pas sur ses mots. Un article de code n'est jamais coupé — il sert à une comparaison |
| Le « nota » sous l'article | **S**, mot pour mot |
| « Lire l'article sur Légifrance › » | **N** (le mot) + **C** (l'adresse, déduite de l'identifiant) |

### Le calendrier

| | |
|---|---|
| Noms de mois et de jours | **C** (mise en forme française, avec « 1er ») |
| « Séance publique », « Commission », « Décision », « Scrutin public », « Promulgation » | **N** — notre classement des codes d'actes |
| Le titre du texte de chaque événement | **S** |
| La ligne de résultat sous l'événement | **S** (libellé de l'acte, décompte du vote) |
| « Aucune séance ni aucun vote ce mois-ci… » | **N** |

### Messages d'attente et de panne

« Chargement… », « Données indisponibles », « Fiche indisponible : … »,
« Aucun texte ne correspond. Essayez d'enlever un filtre. » — tous **N**.

## Les trois seuls endroits où un texte de la source est modifié

Aucun n'est une réécriture, mais ils doivent être connus.

| Où | Ce qui est fait | Pourquoi |
|---|---|---|
| L'exposé sommaire d'un amendement (`socle/publier.py`, `EXPOSE_MAX`) | Coupé à 400 caractères, avec « … » et un drapeau qui le dit | Il pèse les trois quarts d'un fichier d'amendements. Le dispositif, lui, est toujours entier |
| Un article sans numéro (`socle/legi.py`, `intitule_de_secours`) | Nommé par les 62 premiers caractères de son propre texte | « Article » suivi de rien ne dit rien. L'écran prévient que ce n'est pas un intitulé officiel |
| Les articles qu'une loi a écrits (`socle/legi.py`, `sans_les_renvois`) | Leurs renvois sont retirés | Le renvoi répète, en liste de références illisible, ce qui est déjà affiché sous forme de l'article modifié |

S'y ajoutent deux reformulations d'**un seul mot**, assumées : « Première » →
« 1re séance » pour les séances, et `MODIFIE` → « modifié » pour les articles.

## La règle, pour la suite

Quatre lignes à tenir quand on ajoute quelque chose à l'écran :

1. **Rien de la source n'est réécrit.** Si un texte est trop long, on le
   coupe et on le dit ; on ne le résume pas.
2. **Ce que nous écrivons est fixe et se lit dans le code.** Aucun texte
   affiché n'est fabriqué à la volée à partir du contenu d'un texte de loi.
3. **Un calcul n'est jamais présenté comme une donnée.** Un pourcentage, un
   classement ou une couleur qui vient de nous le dit, dans la fenêtre
   d'explication.
4. **L'exception reste une exception.** La description est le seul texte
   écrit par une IA, elle le dit à l'écran, et l'étendre à une autre rubrique
   se décide ici — en modifiant ce document — avant d'écrire une ligne de
   code.

## Les chiffres vérifiés

**Relevés le 2026-09-10**, chacun par une commande sur le dépôt. Les autres
chiffres du document sont des exemples de mise en page.

| Chiffre | Ce qu'il compte | Où il se vérifie |
|---|---:|---|
| Descriptions d'étape | 8 | `ETAPES`, `maquette/feed.html` |
| Descriptions d'issue | 4 | `ISSUES`, `maquette/feed.html` |
| Descriptions de nature de texte | 10 | `TYPES`, `maquette/feed.html` |
| Descriptions de chambre | 3 | `CHAMBRES`, `maquette/feed.html` |
| Explications générales | 15 | `EXPLICATIONS`, `maquette/feed.html` |
| Descriptions de portée de vote | 5 | `PORTEES`, `maquette/feed.html` |
| Descriptions de genre d'événement | 5 | `GENRES`, `maquette/feed.html` |
| Descriptions de champ d'étape | 11 | `CHAMPS_ETAPE`, `maquette/feed.html` |
| Descriptions d'issue publiées avec les données | 6 | `FINS`, `socle/extraction.py` |
| Descriptions de portée publiées avec les données | 5 | `PORTEES`, `socle/extraction.py` |
| Descriptions de catégorie de travaux | 9 | `TRAVAUX`, `socle/publier.py` |
| Mots de pastille traduits de la source | 5 + 1 | `ACTIONS`, `socle/publier.py` (`MODIFIE`…`DEPLACE`, plus « nouveau ») |
| Coupure de l'exposé sommaire | 400 caractères | `EXPOSE_MAX`, `socle/publier.py` |
| Coupure du nom d'un article sans numéro | 62 caractères | `INTITULE_MAX`, `socle/legi.py` |
| Amendements détaillés par texte | 150 | `AMENDEMENTS_MAX`, `socle/publier.py` |
| Record d'amendements sur un seul dossier | 19 510 | mesure notée dans `socle/publier.py` |
| Longueur médiane d'une prise de parole | 4 260 caractères | mesure notée dans `socle/publier.py` |
| Textes suivis | 2 151 | `docs/CE-QUE-L-ON-SUIT.md`, mesuré le 2026-09-01 |
| Lois promulguées | 107 | `docs/CE-QUE-L-ON-SUIT.md`, mesuré le 2026-09-01 |
| Descriptions écrites | 107 | `socle/descriptions.json` — 107 par une IA, 0 par une personne |
| Rubriques de l'application concernées par l'exception | 1 | la description sur la fiche d'un texte |

Et les quatre constats sur la chaîne de publication — celle qui récupère,
range et publie les données —, refaits le 2026-09-10 :

| Constat | Résultat |
|---|---|
| Noms de fournisseurs et de bibliothèques cherchés dans `socle/`, `maquette/`, `.github/` et `docs/` | 0 occurrence |
| Modules importés par les 8 fichiers Python de `socle/` | 24 modules, **tous de la bibliothèque standard**, plus `extraction` et `legi` du projet |
| Fichier de dépendances (`requirements.txt`, `pyproject.toml`, `package.json`…) | Aucun dans le dépôt ; la publication n'exécute aucun `pip install` |
| Fichiers extérieurs chargés par la maquette (`<script src>`, `<link href>`) | Aucun : `feed.html` est un seul fichier |
