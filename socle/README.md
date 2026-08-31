# Le socle — récupérer, ranger, servir

**Étape 2 du plan** (`../docs/PLAN.md`, §6). Elle vient **avant** l'application
Flutter : sans elle, un téléphone devrait télécharger et décortiquer une
archive de 10 Mo à chaque ouverture, et la future version web ne pourrait
lire aucune donnée.

## Les trois pièces

| Fichier | Ce qu'il fait |
|---|---|
| `extraction.py` | Lit l'archive de l'Assemblée et classe chaque dossier. **Ne télécharge rien, n'écrit nulle part.** C'est ici que vivent les règles, et elles sont testées |
| `recuperer.py` | Le programme quotidien : télécharge si ça a changé, range dans la base, écrit au journal |
| `publier.py` | Écrit la base en fichiers tout prêts — **c'est ce qui est mis en ligne** |
| `serveur.py` | Sert la base en direct. **Outil de développement local**, pas ce qui tourne en production |
| `schema.sql` | Le modèle de données |
| `test_extraction.py` | 76 tests sur les règles de lecture |

## Démarrer

```bash
./recuperer.py      # construit parlement.db (~3 Mo). Compter une minute
./publier.py        # écrit public/ — ce qui sera mis en ligne
./serveur.py        # http://127.0.0.1:8000, pour travailler en local
./test_extraction.py
```

La base **n'est pas versionnée** : c'est un fichier de données, reconstruit en
une commande. Seul le code l'est.

## Le faire tourner tous les jours

Le programme est fait pour être déclenché, pas pour tourner en permanence.
Une ligne de `cron` suffit :

```
17 6 * * *  cd /chemin/vers/socle && ./recuperer.py >> recuperer.log 2>&1
```

**Il évite le travail inutile, à deux niveaux.** Il envoie à l'Assemblée
l'`ETag` de la dernière fois ; si rien n'a bougé, le serveur répond « 304 » et
les 10 Mo ne repassent pas. Et si l'archive arrive quand même, il compare son
empreinte à la précédente avant de toucher à la base.

**Pourquoi les deux, et pas seulement l'`ETag` :** l'archive est servie par
**plusieurs machines qui ne publient pas la même génération du fichier**.
Constaté le 2026-08-31 — six appels d'affilée ont renvoyé, en alternance :

```
10 276 665 octets   Last-Modified: Mon, 31 Aug 2026 06:16:30 GMT
10 276 672 octets   Last-Modified: Mon, 31 Aug 2026 10:16:26 GMT
```

Le « 304 » ne tombe donc que lorsque l'appel atterrit sur la machine qui a la
même copie que nous — environ une fois sur deux. Ce n'est pas un défaut du
programme, c'est la source. Le journal montre les deux cas.

**Pour voir si ça se passe bien :**

```bash
./recuperer.py --journal
```

```
début                      statut     dossiers   étapes  message
2026-08-31T18:39:12+00:00  succes         2859    10634  8434 scrutins
```

Une panne laisse une ligne `echec` avec son message. `GET /api/sante` renvoie
la même chose, pour une surveillance à distance.

En cas d'échec au milieu du rangement, **la base ne bouge pas** : l'écriture
se fait en une seule transaction, tout ou rien. Il n'y a jamais de base à
moitié remplie.

## Le modèle de données

Celui du §3.1 du plan : **un dossier, des étapes datées, chacune rattachée à
une chambre.** C'est la forme dans laquelle l'Assemblée publie — il n'y a rien
à recalculer, et **aucun rapprochement à faire avec le Sénat** : l'Assemblée
publie elle-même l'adresse du dossier correspondant.

```
dossier      uid, titre, type, est_loi, chambre_initiale, statut, etape,
             date_dernier_mouvement, chambre, lecture, dernier_acte,
             conclusion, prochaine_date, url_an, url_senat, loi_numero…
etape        dossier_uid, code, lecture, libelle, chambre, date, rang,
             numero (1..6), conclusion, future, precision, details
vote         uid, dossier_uid, date, type, portee, objet, sort,
             pour, contre, abstentions, non_votants…
vote_groupe  vote_uid, sigle, nom, membres, position, pour, contre…
source       ce qu'on sait de chaque source, pour le téléchargement conditionnel
journal      une ligne par exécution
```

### Deux étapes du même jour ne sont pas un doublon

Une chambre siège plusieurs fois dans la journée. L'open data publie alors
plusieurs actes de même nom et de même date, que rien ne distingue à l'écran.
Mesuré le 2026-08-31 sur les **385 groupes d'actes** qui partagent un code et
une date :

| Ce qui les distingue | Groupes | Ce que le socle en fait |
|---|---:|---|
| L'heure — commission le matin, l'après-midi, le soir | 100 | `precision` = « 09 h 00 » |
| La réunion — la séance publique est datée à minuit | 196 | `precision` = « 2e séance », nom donné par l'agenda |
| Rien : même réunion, deux points à l'ordre du jour | 89 | fusionnés, une seule ligne |

C'est la raison d'être de la sixième source, `Agenda.json.zip` : elle seule
nomme les séances. Sur les **382 réunions à départager, 382 y figurent**,
toutes avec leur heure de début et 369 avec leur quantième.

La fusion ne s'applique qu'aux actes dont **tout ce que la fiche montre** est
identique — libellé, lecture, conclusion, précision et détails. Deux
nominations de rapporteur le même jour dans deux commissions différentes
restent deux lignes : leurs détails les distinguent.

### Ce qu'une étape dit d'elle-même

La colonne `details` porte, en JSON, ce que l'acte publie : la commission qui
s'est réunie, le texte qui sort du vote, le rapporteur désigné, le motif d'une
saisine du Conseil constitutionnel, le numéro de la loi.

**Rien n'y est rédigé.** Chaque valeur est recopiée de l'open data ou d'un
référentiel qu'il désigne. Une clé absente veut dire que la source ne dit
rien — pas qu'il n'y a rien à dire. `socle/test_extraction.py` en fait un
test, pour que personne n'y glisse plus tard une phrase inventée.

### L'issue d'un texte

Un texte finit rarement par une promulgation. Le socle distingue :

| Issue | Textes de loi | D'où vient l'information |
|---|---:|---|
| `en_cours` | 1 955 | déduit : rien n'annonce une fin |
| `promulgue` | 107 | Assemblée — acte `PROM-PUB` |
| `retire` | 59 | Assemblée (`RTRINI`) ou Sénat (« retiré ») |
| `non_adopte` | 22 | **Sénat** — « non adopté », « Non conforme à la constitution » |
| `rejete` | 5 | Assemblée — la dernière décision connue est un rejet |
| `caduc` | 2 | **Sénat** — « caduc » |

**Aucun de ces états ne dit qu'un texte est fini pour de bon**, et le code
n'emploie nulle part le mot « définitif ». Un texte rejeté ou non adopté peut
être redéposé ; les sources ne se prononcent pas là-dessus, la page non plus.
Un test le vérifie.

**Le Sénat est récupéré pour cette seule raison.** L'Assemblée n'écrit jamais
qu'un texte est terminé hors promulgation ou retrait ; sans le Sénat,
**29 textes finis restaient affichés comme en cours**. Et il faut nuancer les
rejets : sur les 27 textes de la législature ayant connu un rejet, **19 ont
continué leur parcours** — seuls comptent ceux dont plus rien n'a suivi.

### Les votes, et ce qu'ils ne disent pas

Le socle récupère les **8 434 scrutins publics** de la législature, avec le
décompte par groupe politique. Trois choses à savoir avant de s'en servir :

1. **Peu de textes en ont un.** 71 des 1 990 textes en cours, soit 3,6 %. La
   plupart sont adoptés à main levée, ou jamais examinés.
2. **7 216 scrutins portent sur un amendement**, 212 seulement sur un texte
   entier. D'où la colonne `portee` : sans elle, un affichage laisserait
   croire qu'un texte a été adopté alors qu'un seul de ses amendements l'a
   été.
3. **La position annoncée d'un groupe n'est pas fiable** — elle contredit
   son propre décompte dans 3 % des cas. `vote_groupe.position` est donc
   **recalculée** sur les voix. Détail et chiffres dans
   `../docs/sources/assemblee-nationale.md`.

**Il n'y a pas de votes à venir**, et ce n'est pas un manque du socle :
l'Assemblée ne publie un vote qu'une fois qu'il a eu lieu.

**Les votes du Sénat ne sont pas repris**, alors qu'ils existent : son dump
`dosleg.zip` contient 4 764 scrutins et 1,66 million de votes nominatifs.
Mais **aucune table ne relie un scrutin à un dossier** — seul l'intitulé en
clair le nomme, ce qui obligerait à un rapprochement par titre, « coûteux,
fragile, jamais fiable à 100 % » selon le §3.2 du plan. Ce qui est repris,
c'est le résultat par texte (`adopté` / `non adopté`), rattaché sans
devinette. Détail dans `../docs/sources/senat.md`.

### Les amendements : affichés, jamais reconstitués

Le socle récupère les **109 854 amendements** de la législature, répartis sur
289 dossiers. Chacun est rangé avec son article, son auteur, son groupe et son
sort.

**Ce que le socle ne fait pas, et ne doit pas faire :** reconstituer le texte
modifié. Un amendement n'est pas une différence entre deux textes, c'est une
instruction — « Compléter l'alinéa 7 par les mots : « … » ». Et le texte
original des articles **n'est pas publié en open data** (vérifié le
2026-08-31). Le reconstituer produirait un texte de loi fabriqué par nous,
faux dans une proportion inconnue, et présenté comme officiel.

Ce qui est fait : la colonne `morceaux` découpe l'instruction en marquant ce
que la source met **elle-même** entre guillemets — `ajout`, `retrait` ou
`neutre`, d'après le verbe qui gouverne la phrase. C'est une aide de lecture,
annoncée comme telle à l'écran. **Un test vérifie que la coloration
reconstitue le texte à l'identique**, donc qu'aucun mot n'est perdu ni ajouté.

**Deux plafonds à la publication**, imposés par le volume — un dossier compte
jusqu'à 19 510 amendements :

| | |
|---|---:|
| Amendements détaillés par texte | `AMENDEMENTS_MAX` = **150**, les adoptés d'abord |
| Longueur de l'exposé sommaire | `EXPOSE_MAX` = **400** caractères |

Le dispositif, lui, est toujours complet : c'est la partie qui dit ce que
l'amendement fait. Le compte réel est publié à côté, jamais masqué.

### L'ordre des groupes est mesuré, leur couleur est une convention

**L'ordre.** Chaque vote publie le **numéro de siège** de chaque député. Sur
61 152 numéros relevés le 2026-08-31, les groupes se rangent proprement — le
RN autour de la place 72, LFI autour de la 603. L'hémicycle est numéroté de la
droite vers la gauche : lu à l'envers, il donne l'ordre politique habituel.

```
LFI-NFP · GDR · EcoS · LIOT · SOC · NI · Dem · EPR · HOR · DR · UDR · RN
   603    586   512   456   448  392  345  301  231  184  103   72
```

Rien n'est écrit à la main : si un groupe naît, disparaît ou change de place,
l'ordre suit tout seul. Les médianes se calculent sur un histogramme et non
sur une liste dépliée — les numéros se comptent par millions sur une
législature.

**La couleur.** L'open data n'en publie aucune. Celles du socle sont une
**convention d'affichage**, rassemblées dans `COULEURS_GROUPES`
(`extraction.py`) — **le seul endroit à corriger** si un choix ne convient
pas. Un groupe absent de cette table, passé ou futur, reçoit une couleur
calculée sur sa position, du rouge à gauche au bleu à droite.

**La base garde tout**, y compris les dossiers qui ne fabriquent pas de loi et
les textes promulgués. Les colonnes `est_loi` et `statut` le disent ; c'est à
l'affichage de trier. Un socle qui jette des données oblige à tout recharger
le jour où l'on change d'avis.

## Les adresses servies

```
GET /                     la liste de ce qui suit
GET /api/sante            la base est-elle à jour, et de quand date-t-elle
GET /api/etapes           les six étapes, et combien de textes à chacune
GET /api/textes           la liste     (filtres ci-dessous)
GET /api/textes/<uid>     un texte et tout son parcours, les deux chambres
```

Filtres de `/api/textes` :

| Filtre | Valeurs | Défaut |
|---|---|---|
| `etape` | 1 à 6 | toutes |
| `chambre` | `assemblee`, `senat` | les deux |
| `statut` | `en_cours`, `promulgue`, `retire`, `tous` | `en_cours` |
| `lois` | `1` (que les lois), `0` (tout) | `1` |
| `recherche` | des mots du titre | — |
| `limite` / `debut` | 1 à 500 | 100 / 0 |

Exemple :

```bash
curl 'http://127.0.0.1:8000/api/textes?etape=4&chambre=senat&limite=5'
```

## L'en-tête qui débloque le web

Le serveur répond avec `Access-Control-Allow-Origin: *`. **C'est exactement ce
qui manque aux portails du Parlement**, et c'est ce qui permettra à
l'application Flutter *web* de lire les données — l'application mobile, elle,
n'en a pas besoin.

## Comment c'est mis en ligne : des fichiers, pas un serveur

**Aucune machine n'est louée.** Les données ne changent qu'une fois par jour
et personne ne les modifie : il n'y a rien à calculer en direct. GitHub
exécute le programme chaque matin, écrit les fichiers, et les sert.

C'est `.github/workflows/donnees.yml` qui l'orchestre :

```
tous les matins   →  les tests          (si un test casse, on ne publie pas)
                  →  ./recuperer.py     (télécharge et range)
                  →  ./publier.py       (écrit public/)
                  →  un garde-fou       (moins de 500 textes = on ne publie pas)
                  →  mise en ligne
```

Le garde-fou existe parce qu'une publication réussie de données vides serait
pire qu'un échec : l'application afficherait un écran vide sans que rien ne
signale la panne.

### Ce qui est publié

| Fichier | Taille | Compressé | Contenu |
|---|---:|---:|---|
| `index.html` | 29 Ko | — | **La maquette** (`../maquette/feed.html`, recopiée ici). Publiée à côté des données, elle les lit par une adresse relative |
| `etat.json` | 581 o | — | D'où viennent les données, de quand, et si le dernier chargement s'est bien passé |
| `etapes.json` | 846 o | 477 o | Les six étapes du parcours et leurs comptes |
| `groupes.json` | 1,9 Ko | — | Les groupes politiques, **rangés de la gauche à la droite de l'hémicycle**, avec leur couleur d'affichage |
| `textes.json` | 829 Ko | **121 Ko** | **Le fichier principal** : les 1 990 textes en cours |
| `promulgues.json` | 106 Ko | — | Les 107 lois déjà promulguées |
| `arretes.json` | 57 Ko | — | Les 88 textes **arrêtés en chemin** : rejetés, non adoptés, retirés, caducs |
| `textes/<uid>.json` | 18 Mo | — | Un fichier par texte : parcours, votes, auteur, cosignataires (médiane 4 Ko) |
| `amendements/<uid>.json` | 30 Mo | — | Les amendements d'un texte, chargés seulement si on les ouvre (médiane 90 Ko, 289 fichiers) |

**L'application charge `textes.json` une fois** — 121 Ko sur le réseau — puis
filtre et cherche toute seule, instantanément et même hors connexion. Elle ne
va chercher le fichier de détail que si l'on ouvre un texte.

Le dossier `public/` **n'est pas versionné** : il se régénère en une commande.

### C'est en ligne

**Adresse : <https://yesno584.github.io/AN-API/>** — la maquette s'y ouvre
directement, sur téléphone comme sur ordinateur.

| | |
|---|---|
| **La maquette** | <https://yesno584.github.io/AN-API/> |
| L'état | <https://yesno584.github.io/AN-API/etat.json> |
| Les six étapes | <https://yesno584.github.io/AN-API/etapes.json> |
| **Les textes en cours** | <https://yesno584.github.io/AN-API/textes.json> |
| Les lois promulguées | <https://yesno584.github.io/AN-API/promulgues.json> |
| Un texte | `https://yesno584.github.io/AN-API/textes/<uid>.json` |

Vérifié le 2026-08-31, sans être connecté :

```
content-type: application/json; charset=utf-8
content-encoding: gzip
content-length: 126121            ← les 1 990 textes, compressés
access-control-allow-origin: *    ← une page web peut donc lire
```

**Le dépôt doit rester public.** C'est ce qui rend tout cela gratuit et
lisible sans mot de passe. Le repasser en privé casserait les deux à la fois :
GitHub Pages exigerait un abonnement, et l'application ne pourrait plus rien
lire.

Pour republier sans attendre le lendemain :
`Actions → Données du Parlement → Run workflow`, y compris depuis un
téléphone.

## Ce que le socle ne fait pas

- **Ni comptes, ni favoris, ni authentification.** C'est l'étape 4.
- **Ni les scrutins, ni les débats, ni les parlementaires.** Le plan dit de
  commencer par les dossiers législatifs ; les débats, très volumineux
  (56 Mo à l'Assemblée, 545 Mo au Sénat), viennent en dernier.
- **Ni les données du Sénat directement.** Inutile pour l'instant :
  l'Assemblée publie déjà le parcours dans les deux chambres. Voir
  `../docs/sources/senat.md` pour ce que le Sénat apporterait en plus.
- **Il ne garde pas d'historique entre deux exécutions en ligne.** La machine
  de GitHub est neuve à chaque fois : la base est reconstruite, et le journal
  ne contient que l'exécution en cours. Pour suivre les pannes dans la durée,
  ce sont les exécutions de GitHub qu'il faut regarder, pas le journal.

## Source et licence

Dossiers législatifs de l'Assemblée nationale, sous **Licence Ouverte
(Etalab)**. Détail et mesures dans `../docs/sources/assemblee-nationale.md`.
