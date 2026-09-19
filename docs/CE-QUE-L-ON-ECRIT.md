# Ce que l'on écrit, et ce que l'on recopie

**Relevé le 2026-09-10** sur `maquette/feed.html`, `socle/extraction.py`,
`socle/legi.py`, `socle/publier.py` et `socle/descriptions.json`. Écrit pour
répondre à une question simple : dans tout ce que l'application affiche,
qu'est-ce qui vient du Parlement, et qu'est-ce qui vient de nous ?

## En une phrase

**Deux rubriques de l'application sont écrites par une intelligence
artificielle — la description, en haut de la fiche d'un texte, et le résumé
des débats, en tête de l'onglet « Débats » — et toutes deux le disent à
l'écran.** Tout le reste est recopié de la source, écrit à la main dans le
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

## Les deux exceptions, et rien d'autre

### 1. La description d'un texte

C'est la seule entorse à la règle, et elle est délibérée. Une fiche s'ouvrait
sur un titre officiel — « Projet de loi portant diverses dispositions
d'adaptation au droit de l'Union européenne… » — qui ne dit pas de quoi le
texte parle. La description répond à cette question en deux phrases.

**Ce qu'elle est**

| | |
|---|---|
| Où elle s'affiche | En haut de la fiche d'un texte, sous les étiquettes, avant les liens vers les sources. Nulle part ailleurs |
| Quelle forme elle a | **Trois parties, dans cet ordre.** Un **contexte** d'un paragraphe au plus — ce qui se passait avant le texte, et pourquoi il arrive — puis une accroche d'une phrase, puis **une puce par mesure concrète** — trois à six selon la loi. Un pavé se saute, une liste se parcourt. Une accroche seule reste valable : une loi qui autorise l'approbation d'un traité n'a qu'une chose à dire, et le contexte est facultatif |
| Le **nom d'usage**, quand le texte en a un | Au-dessus du contexte : « Ripost », « le nom qu'on lui donne en séance ». Un texte connu sous un nom ne se cherche pas sous son intitulé officiel — et ce nom **n'est écrit nulle part dans la source**. Il est donc **contrôlé** : `assembler_descriptions.py` le cherche lui-même, mot entier, dans les prises de parole publiées, et **refuse un nom qu'il n'y trouve pas trois fois**. Le compte affiché est relevé, jamais écrit. C'est la même mécanique que les positions de vote du résumé des débats |
| Ce qu'elle met en avant | **Ce qui change, pas l'état d'arrivée.** « La protection ne visait que les salariées engagées dans une procédure médicale de procréation ; elle vise désormais tous les salariés en projet parental » plutôt que la règle nouvelle seule. Quand la source ne porte pas d'avant — l'article est créé — la puce dit ce que la loi instaure, sans inventer un état antérieur |
| Comment elle est écrite | Pour quelqu'un sans formation juridique. **Aucun numéro d'article ni nom de code dans les puces** : ils ne disent rien au lecteur et l'écran juste en dessous les affiche déjà tous. La citation ne sert que là où le mot exact fait la règle — un délai, un seuil, une définition |
| Comment elle est signalée | Une icône et une mention sous la liste — « Générée par une IA ». Au survol sur un ordinateur, la mention complète ; au toucher sur un téléphone, une explication qui dit d'où elle vient, qu'elle peut se tromper, quand elle a été écrite et par quel modèle |
| D'où elle vient | `socle/descriptions.json`, un fichier **versionné**, écrit hors ligne. C'est la seule donnée du projet qui ne vienne pas d'une source publique |
| Sur quoi elle s'appuie | **Le texte réel des articles**, lu dans les fichiers publiés : ce que la loi ajoute au droit, mot pour mot, et ce qu'elle en retire. Pas le titre, qui ne dit rien — « Projet de loi portant diverses dispositions d'adaptation au droit de l'Union européenne » en est la démonstration |
| Sur quoi **le contexte** s'appuie | **Les mêmes fichiers publiés, et rien d'autre** : les morceaux « retiré » des articles, qui sont la rédaction d'avant mot pour mot, le parcours du texte, et ce que les orateurs ont dit en séance. **Jamais une connaissance extérieure** — ni actualité, ni chiffre, ni événement qui ne soit pas dans les données du projet. Cette règle-là n'est pas contrôlable par un programme : elle tient à la rédaction, et c'est pourquoi elle est écrite ici |
| Ce qui se passe s'il n'y en a pas | La rubrique ne s'affiche pas. Pas de cadre vide, pas de phrase d'attente |

**Ce qu'elle ne fait pas**

- Elle **ne remplace aucun texte de la source**. Le titre, le parcours, les
  votes, les prises de parole et le texte des articles restent au mot près.
- Elle **ne s'étend pas d'elle-même ailleurs**. Étendre l'exception à une
  autre rubrique demande une décision écrite ici, pas une initiative de
  session. Une seule l'a été depuis : le résumé des débats, ci-dessous.
- Elle **n'est pas produite par la chaîne de publication**. Aucun appel à un
  service d'IA, aucune clé d'accès, aucune dépendance : le fichier est déjà
  écrit quand la publication le lit.
- Elle **ne vieillit pas toute seule**. Une description écrite avant qu'un
  texte n'avance dans son parcours reste telle quelle. Sa date est stockée et
  affichée ; rien ne la périme automatiquement.

**Une entrée peut aussi être écrite par une personne.** Le fichier porte alors
`origine: "humain"`, et la mention à l'écran change en conséquence. C'est prévu
dès maintenant pour que remplacer une description générée par une description
rédigée ne demande aucun changement de code. Le champ `modele` nomme le modèle
qui a écrit, quand on le connaît ; il reste vide sinon, et la fiche se tait
alors plutôt que d'annoncer un vide.

**Comment les régénérer**, en deux commandes :

```
.claude/scripts/faits_pour_descriptions.py --sortie <dossier> --avec-paroles
.claude/scripts/assembler_descriptions.py --lots <dossier>/*.json --origine ia
```

Le premier récolte le texte réel des articles, loi par loi ; il dit toujours
combien d'articles il a lus sur combien, et échantillonne les grandes lois
moitié-moitié — les articles que la loi a écrits elle-même, et les articles de
code les plus réécrits. `--avec-paroles` y joint un échantillon des prises de
parole : c'est la seule matière d'un nom d'usage, et la meilleure d'un
contexte. Le second contrôle la forme de ce qui a été rédigé entre les deux et
refuse une entrée qui ne tient pas, plutôt que de publier une description à
moitié écrite. **Les lots s'ajoutent à ce qui existe déjà** : ajouter un
contexte à dix textes ne touche pas aux autres.

### 2. Le résumé des débats d'un texte

**Décidé le 2026-09-19**, à la demande explicite de l'auteur du projet. C'est
la seconde entorse à la règle, et la dernière en date. Un texte discuté compte
jusqu'à 69 prises de parole : on les publie entières, mot pour mot, mais
personne ne lit soixante-neuf discours pour savoir ce que les groupes ont dit.

**Ce qu'il est**

| | |
|---|---|
| Où il s'affiche | En tête de l'onglet « Débats » d'un texte, **au-dessus des prises de parole complètes**, qui restent affichées en dessous, entières et inchangées. Nulle part ailleurs |
| Quelle forme il a | Les groupes rangés par camps — « Ont voté pour », « Ont voté contre », « Se sont abstenus », « Se sont partagés » — puis, sous chaque groupe, **au plus quatre arguments**, une phrase chacun |
| **Ce que l'IA n'écrit pas** | **Le camp.** La position de chaque groupe est relevée dans le scrutin publié par l'Assemblée, par `assembler_resumes.py`, et jamais reprise de la rédaction. Un résumé ne peut donc pas se tromper sur un vote, seulement sur un argument |
| Sur quoi il s'appuie | **Les prises de parole publiées de ce groupe**, et elles seules : discussion générale et explications de vote, telles que le compte rendu les imprime |
| Comment il est signalé | Une icône et la mention « Généré par une IA » sous le résumé ; au toucher, une explication qui dit d'où viennent les arguments, que l'IA peut se tromper, que le classement des camps vient du scrutin, et quand le résumé a été écrit |
| D'où il vient | `socle/resumes_debats.json`, fichier **versionné**, écrit hors ligne, comme les descriptions |
| Ce qui se passe s'il n'y en a pas | La rubrique ne s'affiche pas, et l'onglet reste exactement ce qu'il était |

**Ce qu'il ne fait pas**

- Il **ne relie jamais une parole à un vote**. Le camp vient du scrutin, les
  arguments viennent des paroles, et les deux ne se commentent pas l'un
  l'autre. La raison est mesurée : le 2026-09-02, l'UDR a voté *pour* les soins
  palliatifs pendant que son orateur disait « votera contre » — il parlait de
  l'autre texte de la même séance. Un résumé peut donc ranger un groupe dans
  un camp dont ses phrases semblent s'écarter : c'est la source qui le dit.
- Il **ne classe pas les arguments en « pour » et « contre »** selon leur
  contenu. Cela demanderait d'interpréter les phrases, donc d'écrire à la
  place des orateurs.
- Il **ne remplace pas les paroles**. Elles sont sous lui, entières.
- Il **n'invente pas un groupe**. Un groupe qui a voté sans parler n'apparaît
  pas ; un groupe qui a parlé sans être au scrutin est affiché à part, sous
  « Groupes absents de ce scrutin ».
- Il **n'est pas produit par la chaîne de publication**. Aucun appel à un
  service, aucune clé, aucune dépendance.

**Comment les régénérer**, en deux commandes, comme les descriptions :

```
.claude/scripts/faits_pour_resumes.py --sortie <dossier> --combien 20
.claude/scripts/assembler_resumes.py --lots <dossier>/*.json --origine ia
```

Le premier récolte les paroles d'un texte, groupe par groupe, et relève le
scrutin ; il ne rédige rien. Le second contrôle la forme — quatre arguments au
plus, une phrase chacun, un groupe qui a réellement parlé — **inscrit les
positions de vote lues dans la source**, et refuse une entrée qui ne tient
pas.

**Portée mesurée le 2026-09-19** : 205 textes ont des prises de parole, 136 ont
un scrutin sur l'ensemble, **129 ont les deux** — eux seuls portent les camps.
Les 76 autres affichent les mêmes arguments, rangés comme dans l'hémicycle,
avec une phrase qui dit qu'aucun scrutin public n'a eu lieu sur l'ensemble.

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
| « Qui vote quoi », « Filtres », « Chercher dans les titres… » | **N** |
| « **2 151** textes, dont 107 devenus des lois » | **C** (les chiffres) + **N** (les mots) |
| Le pied de page entier (source, licence, « Rien n'est écarté ») | **N** |
| « Texte déposé », « Texte de la commission », « Texte adopté par l'Assemblée » | **N** — la source nomme le document « Proposition de loi » à chaque étape, ce qui ne distinguerait pas les versions |
| « Dernière mise à jour : … » | **C** — la date à laquelle **les données** ont été récupérées, pas celle de la mise en ligne. Les deux diffèrent : une modification de la maquette republie le site avec les données de la veille |

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
| Les étiquettes « Les deux chambres », « Projet de loi », « Promulguée » | **N** (les mots) + **C** (le classement) | |
| L'étiquette « Procédure accélérée » et sa date | **S** | la source publie l'acte `AN1-PROCACC` ou `SN1-PROCACC` dans le parcours ; nous ne faisons que le remonter en haut de la fiche. 158 textes de loi sur 2 218 la portent |
| **Le nom d'usage (« Ripost »), en tête de la description** | **S** pour le nom, **IA** pour l'avoir repéré | le nom est **retrouvé dans les prises de parole publiées** par `assembler_descriptions.py`, mot entier ; un nom introuvable est refusé. Le compte de citations est **C** |
| **Le contexte, l'accroche et les mesures** | **IA** | `socle/descriptions.json` — voir l'exception ci-dessus |
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

### L'onglet « Texte »

| | |
|---|---|
| Les trois titres de partie (« Texte déposé », « Ce que … a changé », « …, à jour ») | **N** (les mots) + **S** (le nom de la version, tel que la source le nomme) |
| Leur date | **S** |
| **Le texte des articles** | **S**, **mot pour mot** — c'est le document publié par l'Assemblée, rien n'est reformulé |
| Le vert et le rouge des différences | **C** — comparaison mot à mot entre deux versions de la source, la même que celle du parcours |
| « Modifié », « Nouveau », « Retiré », « Inchangé » | **C** — notre lecture de la comparaison |
| « Le texte de ce projet ou de cette proposition n'est pas publié ici… » | **N** |

La **« formule »** du document — la phrase de la source qui dit ce que le texte
vise (« visant à offrir des réponses immédiates… ») — est publiée telle quelle
sous la clé `formule`. Elle l'était déjà, mais sous la clé `description`, où la
description écrite par une IA venait l'écraser : deux textes de nature
différente partageaient un seul nom. Elles ont désormais chacune le leur.

### Ce que les groupes en ont dit

| | |
|---|---|
| **Le résumé, en tête de l'onglet** | **IA** pour les arguments, **S** pour les camps de vote — voir l'exception n° 2 ci-dessus |
| « Groupes rangés d'après le scrutin du 23 octobre 2025 sur l'ensemble du texte — adopté » | **C** (la date et le sort viennent du scrutin) + **N** (les mots) |
| « Ont voté pour », « Ont voté contre », « Se sont abstenus », « Se sont partagés » | **N** — le rangement, lui, est **S** |
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

### L'hémicycle

L'écran s'ouvre par le bouton en forme d'arcs, à côté du calendrier. Le
**dessin** est la seule image de l'application qui ne recopie rien. La source
publie le **numéro du siège** de chaque député — 576 sur 577 — mais pas la
position de ce siège dans la salle : c'est cette position, et elle seule, que
le dessin invente. Les proportions et l'ordre, eux, sont justes.

| | |
|---|---|
| « L'Assemblée nationale », « dép. » | **N** |
| « 577 députés, 12 groupes » | **C** — un compte des députés rattachés à chaque groupe |
| L'ordre des groupes, de la gauche à la droite | **C** — **mesuré** sur les numéros de siège (voir `socle/README.md`) |
| Sigle et nom complet de chaque groupe | **S** |
| La couleur de chaque groupe | **N** — convention d'affichage, `COULEURS_GROUPES` |
| **La place d'un siège dans le dessin** | **N** — une convention : 12 rangées d'arcs remplies de la gauche à la droite. La source donne le numéro du siège, pas l'endroit où il se trouve dans la salle |
| Le dessin « par siège » | **C** — chaque député placé d'après **son** numéro, les 650 numéros dans leur ordre. L'ordre est une donnée, la géométrie des arcs reste une convention |
| « 576 députés à leur numéro de siège, 74 sièges vides — 1 député sans numéro, donc absent du dessin. » | **C** (les trois chiffres) + **N** (les mots) |
| « groupe / siège », le bouton du dessin | **N** |
| « 220 F / 357 H », et le compte de chaque groupe | **C** — compté **à l'affichage** sur la civilité (« Mme » / « M. ») que la source imprime devant chaque nom. Rien d'autre n'est publié là-dessus, et rien n'est ajouté. Un député sans civilité n'est compté d'aucun côté |
| « Ce dessin est une convention » (au toucher du ⓘ) | **N** — l'écran dit lui-même ce qui est mesuré et ce qui est dessiné |

### Les députés d'un groupe

Toucher un groupe, sous le dessin, ouvre la liste de ses députés.

| | |
|---|---|
| Civilité, prénom, nom | **S** |
| Le département et le numéro de circonscription | **S** |
| Le numéro de siège (« siège 585 ») | **S** — seul le zéro de remplissage de la source est enlevé (« 077 » → 77). 576 députés sur 577 en ont un ; le dernier n'en affiche aucun |
| **La photo** | **S** (le fichier est celui du site de l'Assemblée) + **C** (son adresse, calculée sur l'identifiant du député — l'open data ne la publie pas). Chargée depuis le site de l'Assemblée, pas depuis notre socle ; une photo absente laisse une pastille grise, jamais une image brisée |
| « 1re circonscription », « 3e circonscription » | **C** — la source donne « 1 », « 3 » ; seule la forme est à nous |
| L'ordre de la liste (par nom, puis par prénom) | **C** — la source ne classe pas. Les accents sont ignorés pour classer seulement : « Bénard » vient avant « Brugerolles », et le nom affiché garde les siens |
| « 17 députés, classés par nom », « Retour à l'hémicycle » | **N** |
| « La liste des députés de ce groupe n'est pas encore publiée… » | **N** |

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
