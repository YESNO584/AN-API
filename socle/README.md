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
| `serveur.py` | Sert la base à l'application, en JSON, avec l'en-tête qui autorise une page web à lire |
| `schema.sql` | Le modèle de données |
| `test_extraction.py` | 21 tests sur le classement des étapes |

## Démarrer

```bash
./recuperer.py      # construit parlement.db (~3 Mo). Compter une minute
./serveur.py        # http://127.0.0.1:8000
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
2026-08-31T11:07:30+00:00  succes         2859    10700
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
dossier   uid, titre, type, est_loi, chambre_initiale, statut, etape,
          date_dernier_mouvement, url_an, url_senat, loi_numero…
etape     dossier_uid, code, lecture, libelle, chambre, date, rang,
          numero (1..6), conclusion, future
source    ce qu'on sait de la source, pour le téléchargement conditionnel
journal   une ligne par exécution
```

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

## Ce que le socle ne fait pas

- **Ni comptes, ni favoris, ni authentification.** C'est l'étape 4.
- **Ni les scrutins, ni les débats, ni les parlementaires.** Le plan dit de
  commencer par les dossiers législatifs ; les débats, très volumineux
  (56 Mo à l'Assemblée, 545 Mo au Sénat), viennent en dernier.
- **Ni les données du Sénat directement.** Inutile pour l'instant :
  l'Assemblée publie déjà le parcours dans les deux chambres. Voir
  `../docs/sources/senat.md` pour ce que le Sénat apporterait en plus.
- **Il ne se lance pas tout seul.** Le déclenchement quotidien et
  l'hébergement restent à décider — c'est la question 8 du §10 du plan.

## Source et licence

Dossiers législatifs de l'Assemblée nationale, sous **Licence Ouverte
(Etalab)**. Détail et mesures dans `../docs/sources/assemblee-nationale.md`.
