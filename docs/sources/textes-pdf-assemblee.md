# Les textes de l'Assemblée en PDF — lire le texte pour en tirer un avant/après

**Mesuré le 2026-08-31**, sur 75 fichiers PDF réellement téléchargés depuis
`assemblee-nationale.fr` et comparés aux mêmes textes publiés en XML par le
Sénat.

Fiche jumelle : [`monalisa.md`](monalisa.md), qui traite du même besoin côté
Sénat, où le texte existe déjà en XML.

## La conclusion en une phrase

**Oui, on peut lire les PDF de l'Assemblée et en tirer un avant/après article
par article : 86 % des articles ressortent mot pour mot, et cela porterait la
comparaison de 203 à 319 textes** — mais il faut écrire les règles de lecture
et accepter que les tableaux restent illisibles.

## Pourquoi cette question se pose

L'Assemblée ne publie pas le texte de ses lois sous forme structurée. Son open
data ne donne que des fiches signalétiques ; le texte lui-même n'existe qu'en
document Word (sur `docparl.assemblee-nationale.fr`, refusé par le proxy de
sortie) et en **PDF**, à une adresse publique.

Or c'est du côté de l'Assemblée que se joue l'essentiel : sur 2 151 textes de
loi, Monalisa n'en couvre que 203 pour une comparaison, parce qu'il ne
contient que les versions imprimées par le Sénat.

## Ce que ça couvrirait

Les versions successives d'un texte à l'Assemblée sont **listées dans
l'archive que le socle télécharge déjà tous les jours** — aucun appel réseau
supplémentaire pour le savoir :

```
PIONANR5L17B1148      la proposition déposée
PIONANR5L17BTC1640    le texte de la commission
PIONANR5L17BTA0163    le texte adopté en séance
```

L'adresse du PDF se déduit de cet identifiant (`l17b1148_proposition-loi.pdf`,
`l17b1640_texte-adopte-commission.pdf`, `l17t0163_texte-adopte-seance.pdf`).
**Règle vérifiée sur 40 identifiants tirés au sort : 40 réponses 200.**

| Textes de loi de la 17e législature | 2 151 |
|---|---:|
| avec 0 version à l'Assemblée (nés au Sénat) | 459 |
| avec 1 seule version — rien à comparer | 1 443 |
| **avec 2 versions ou plus → comparaison possible** | **249** |

Croisé avec le Sénat :

| | |
|---|---:|
| Comparaison possible côté Assemblée (PDF) | 249 |
| Comparaison possible côté Sénat (Monalisa) | 203 |
| Les deux à la fois | 133 |
| **Au moins un des deux côtés** | **319** (15 %) |

Lire les PDF ajoute donc **116 textes** que Monalisa ne couvre pas, et surtout
complète le parcours des 133 textes où l'on ne voyait aujourd'hui que la
moitié Sénat.

État de ces 319 : 197 en cours, 107 promulgués, 15 finis sans être adoptés.

## Est-ce fidèle ? La mesure

Le Sénat réimprime en XML le texte que l'Assemblée lui transmet. Les deux
documents disent la même chose : tout écart vient de la lecture du PDF. C'est
l'étalon.

**Sur 30 textes adoptés par l'Assemblée, 295 articles :**

| | |
|---|---:|
| Articles retrouvés dans les deux sources | 295 / 295 |
| **Articles dont le PDF donne exactement les mêmes mots** | **254 (86,1 %)** |
| Mots en écart, tous articles confondus | 352 |

Ce qui reste tient en quatre causes, toutes identifiées :

1. **Les tableaux** (barèmes, tableaux d'application outre-mer). Le PDF les
   aplatit colonne par colonne : les mots y sont tous, dans le désordre.
   C'est la seule cause qu'on ne sait pas corriger proprement.
2. **Les articles groupés** : « Articles 5 et 5 bis (Supprimés) » annonce deux
   articles sur une ligne. Règle à écrire.
3. **Les intertitres en minuscules** (« Dispositions pénales ») se collent à
   l'article précédent. Règle à écrire.
4. **De la typographie** : un signe moins Unicode au lieu d'un trait d'union,
   un point détaché après un chiffre romain. Corrigé en normalisant.

En corrigeant les points 2 à 4, on approcherait 95 %. Les tableaux resteront.

## Ce qu'il faut pour lire un PDF

### Une bibliothèque

`pdfplumber` (Python). Testée contre `pypdf`, qui insère des espaces au milieu
des mots dans ces PDF justifiés (« remp lacé », « l'intit ulé ») : inutilisable
ici. `pdfplumber` rend un texte propre.

Coût : **≈ 50 Mo installés** (pdfminer.six, Pillow, cryptography). C'est la
première dépendance non standard du projet, qui n'en a aucune aujourd'hui.
À installer aussi dans la publication quotidienne GitHub.

### Des règles de lecture, écrites à la main

Le PDF ne dit pas « ceci est un article ». Il a fallu écrire, et **chaque
règle vient d'un défaut constaté, pas d'une supposition** :

| Règle | Le défaut qu'elle corrige |
|---|---|
| Repérer une ligne « Article 4 (nouveau) » comme un début d'article | rien ne découpe le texte sans ça |
| Jeter les caractères de la zone privée Unicode | l'Assemblée numérote les alinéas dans la marge avec une police maison : ces glyphes ne sont pas du texte |
| Recoller un mot coupé en fin de ligne | « quatre-vingt- » + « seize » ressortait en deux morceaux |
| Ignorer les lignes tout en capitales | « TITRE V » et son intitulé se collaient à l'article précédent |
| Traiter « (Supprimé) » comme un état, pas comme du texte | un article supprimé se comparait à son ancienne version |
| N'arrêter la lecture à « Signé : » qu'après le premier article | un projet de loi porte la signature d'un ministre **dès sa page de garde** : la lecture s'arrêtait avant le premier article, et le fichier ressortait vide |
| Jeter les en-têtes de page « – 3 – » | ils tombaient au milieu des phrases |

Environ **80 lignes de Python**, à couvrir de tests comme le reste des règles
du socle.

### Du temps et de la place

| | |
|---|---:|
| PDF à télécharger pour les 249 textes | 795 |
| Poids médian d'un PDF | 89 ko |
| Poids total | ≈ 70 Mo |
| Temps de lecture d'un PDF | 1,8 s |
| Première passe complète | ≈ 25 min |

Un texte publié ne change plus : après la première passe, seuls les nouveaux
textes sont à lire, quelques-uns par jour. Rien à verser dans git, comme le
reste des données.

## Ce qui ne marchera pas

Sur 40 PDF tirés au sort, **1 est une image scannée** (une page, aucun texte
dedans). Aucune règle ne le lira ; il faudrait de la reconnaissance de
caractères, c'est-à-dire une autre dépendance et une autre fiabilité. À ce
taux, une vingtaine de textes sur 795 seraient concernés.

Deux autres cas résistent : les **lois de finances et de financement de la
sécurité sociale**, qui commencent par un sommaire où chaque ligne ressemble
à un début d'article, et dont le corps est fait de tableaux.

## Un exemple réel

`DLR5L17N51218`, « Faciliter l'accès des demandeurs d'asile au marché du
travail » — un texte **que Monalisa ne couvre pas**, du texte déposé
(`l17b0771`) au texte de la commission (`l17b0935`) :

> ~~Après la première occurrence du mot : « asile », la fin de l'article
> L. 554-1 du~~ **Le** code de l'entrée et du séjour des étrangers et du droit
> d'asile est ainsi ~~rédigée~~ **modifié : 1° L'article L. 554-1 est ainsi
> rédigé** : « **Art. L. 554-1. – I. – L'accès au marché du travail est
> autorisé au demandeur d'asile** à compter de ~~l'introduction~~
> **l'enregistrement** de sa demande […] » **; 2° (nouveau) L'article
> L. 554-3 est abrogé.**

Comme côté Sénat, le calcul est une comparaison mot à mot avec `difflib`,
bibliothèque standard de Python : aucun modèle de langage, aucun coût.

## Une limite qui n'est pas celle du PDF

Deux versions ne s'apparient que par leur **numéro d'article** : un PDF ne
porte pas d'identifiant stable, contrairement au XML du Sénat. Un article
renuméroté en cours de route sera donc comparé au mauvais. C'est le principal
risque de faux avant/après, et il est plus élevé qu'avec Monalisa, où 71 % des
articles s'apparient par identifiant.

## L'exposé des motifs est dans le PDF de dépôt

**Mesuré le 2026-09-01**, sur 40 dépôts tirés au sort parmi les 1 692 dont
notre base identifie le document.

C'est la réponse à une question posée séparément : *le titre d'un texte ne dit
presque rien, existe-t-il une description plus parlante ?* Les données ouvertes
de l'Assemblée n'en contiennent aucune. **Le PDF de dépôt, lui, porte l'exposé
des motifs — l'argumentaire écrit par les auteurs, avant le premier article.**

| | |
|---|---:|
| PDF lus | 40 |
| **Textes déposés d'abord à l'Assemblée : exposé présent** | **32 / 32 — 100 %** |
| Textes transmis par le Sénat : exposé absent | 7 |
| Texte retiré par son auteur | 1 |

Les 7 absences ne sont pas un défaut de lecture : ce sont des textes
**« ADOPTÉE PAR LE SÉNAT »**, dont le document de l'Assemblée n'est qu'une
transmission. Leur exposé des motifs existe, mais dans le document de dépôt du
Sénat. La règle est donc simple : **l'exposé est dans le document de dépôt de
la chambre d'origine.**

Longueur, sur les 32 : **médiane 5 900 caractères**, de 2 300 à 19 200. Aucun
n'est un résumé d'une ligne — c'est un texte suivi, de plusieurs paragraphes.

### Où il se trouve dans le fichier

Entre le titre et le premier article, sous un intertitre `EXPOSÉ DES MOTIFS`.
Il se termine à `PROPOSITION DE LOI` / `PROJET DE LOI` ou au premier
`Article 1er`. Deux repères de garde, lus dans les PDF eux-mêmes :

- `ADOPTÉE PAR LE SÉNAT` en tête ⇒ pas d'exposé, ne pas chercher ;
- `Ce texte a été retiré par son auteur` ⇒ le document est presque vide.

### L'adresse d'un document

```
https://www.assemblee-nationale.fr/dyn/<législature>/textes/l<lég>b<numéro sur 4 chiffres>_<genre>.pdf
```

`<genre>` vaut `proposition-loi` ou `projet-loi`, et se déduit de la référence
du texte associé à l'étape de dépôt (`PION…` ⇒ proposition, `PRJL…` ⇒ projet).
Exemple : `PIONANR5L17B0261` donne
`https://www.assemblee-nationale.fr/dyn/17/textes/l17b0261_proposition-loi.pdf`.

**Attention :** `…/dyn/docs/…` renvoie 404 — et un 404 de l'Assemblée fait
64 660 octets, donc un téléchargement qui « réussit » sans vérifier le code
HTTP écrit une page d'erreur dans un fichier `.pdf`.

### Ce que ça coûterait

Un appel par texte, une seule fois (un dépôt ne change plus). 40 PDF ont pris
environ 3 minutes en séquentiel. Le PDF médian pèse 60 ko.

**Décision non prise :** afficher un exposé de 5 900 caractères sur une fiche
mobile demande de choisir quoi en montrer — et le tronquer, c'est écrire un
résumé, donc du texte qui ne vient plus des sources.
