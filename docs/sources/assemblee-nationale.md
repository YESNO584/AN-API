# Assemblée nationale — `data.assemblee-nationale.fr`

**Vérifié le 2026-08-31.** Tous les chiffres viennent de fichiers réellement
téléchargés et comptés ce jour-là.

## Pourquoi c'est la source principale

Trois raisons, dans l'ordre :

1. **Elle contient le parcours dans les deux chambres.** Un dossier de
   l'Assemblée décrit aussi les étapes passées au Sénat. Ce n'était pas
   attendu — le plan supposait qu'il faudrait rapprocher deux sources.
2. **Elle donne le lien vers le dossier du Sénat**, ce qui résout le
   problème du recollement (voir plus bas).
3. **Elle est mise à jour tous les jours.** Les fichiers testés portaient
   tous une date de modification du jour même.

## Licence

Licence Ouverte (Etalab). Réutilisation libre, y compris commerciale, avec
mention de la source. **C'est plus permissif que l'ODbL de La Fabrique de la
Loi**, qui obligeait à repartager sous la même licence.

## Le jeu de données central : les dossiers législatifs

| | |
|---|---|
| **Adresse** | `https://data.assemblee-nationale.fr/static/openData/repository/17/loi/dossiers_legislatifs/Dossiers_Legislatifs.json.zip` |
| **Format** | ZIP de fichiers JSON (une variante `.xml.zip` existe) |
| **Taille** | 10,3 Mo compressé, 55 Mo décompressé |
| **Contenu** | 3 055 dossiers, dont **2 859 pour la 17e législature** (celle en cours), et 10 125 fichiers au total en comptant les documents |
| **Mise à jour** | Quotidienne |

Le `17` dans l'adresse est le numéro de la législature. Les précédentes sont
sous `/archives-16e/`, `/archives-anterieures/`.

### Un détail de service à connaître avant d'automatiser

**L'archive est servie par plusieurs machines qui ne publient pas la même
génération du fichier.** Six appels d'affilée, le 2026-08-31, ont renvoyé en
alternance :

```
10 276 665 octets   Last-Modified: Mon, 31 Aug 2026 06:16:30 GMT   ETag "9ccf39-…"
10 276 672 octets   Last-Modified: Mon, 31 Aug 2026 10:16:26 GMT   ETag "9ccf40-…"
```

Conséquence pour un programme qui récupère les données tous les jours : le
téléchargement conditionnel (`If-Modified-Since`) **fonctionne** — le serveur
répond bien « 304 » — mais seulement quand l'appel tombe sur la machine qui a
la même copie que nous. Il faut donc aussi comparer le contenu reçu, sans quoi
on rebâtit sa base pour rien une fois sur deux. C'est ce que fait
`../../socle/recuperer.py`.

### Ce que contient un dossier

```
dossierParlementaire
├── uid                     DLR5L17N53259        identifiant du dossier
├── legislature             "17"
├── titreDossier
│   ├── titre               le titre long, en français
│   ├── titreChemin         une version courte, utilisable comme adresse
│   └── senatChemin         ← l'adresse du même dossier au Sénat
├── procedureParlementaire  le type (projet, proposition, ratification…)
└── actesLegislatifs        l'arbre des étapes (voir ci-dessous)
```

### Les étapes, telles qu'elles sont publiées

Les étapes forment un arbre. Le premier niveau donne la grande phase, les
niveaux suivants le détail. Exemple réel, un texte allé au bout :

```
AN1     1ère lecture (1ère assemblée saisie)
   AN1-DEPOT              2025-12-02   dépôt
   AN1-COM-FOND-SAISIE    2025-12-02   saisine de la commission
   AN1-COM-FOND-RAPPORT   2026-01-14   dépôt du rapport
   AN1-DEBATS-SEANCE      2026-01-20   séance publique
   AN1-DEBATS-DEC         2026-01-20   décision
SN1     1ère lecture (Sénat)
   SN1-DEPOT              2026-01-20
   SN1-COM-FOND-RAPPORT   2026-04-08
   SN1-DEBATS-SEANCE      2026-04-15
   SN1-DEBATS-DEC         2026-04-15
PROM    promulgation
   PROM-PUB               2026-04-21
```

**Chaque étape porte son propre libellé en français** (`libelleActe.nomCanonique`) :
« 1ère lecture », « Lecture unique », « Nouvelle Lecture »… Il n'y a donc
aucune table de correspondance à inventer ni à deviner.

### Où en sont les textes aujourd'hui

Étape de l'acte daté le plus récent, sur les 2 859 dossiers de la 17e
législature :

| Dossiers | Code | Étape |
|---:|---|---|
| 1 489 | `AN1` | 1re lecture à l'Assemblée |
| 544 | `SN1` | 1re lecture au Sénat |
| 430 | `ANLUNI` | Lecture unique |
| 251 | `AN20` | Travaux (voir l'avertissement ci-dessous) |
| 107 | `PROM` | Promulgué |
| 22 | `AN21` | Débat (voir l'avertissement) |
| 7 / 4 | `AN2` / `SN2` | 2e lecture |
| 2 | `CC` | Conseil constitutionnel |
| 1 | `CMP` | Commission mixte paritaire |
| 1 | `SNNLEC` | Nouvelle lecture au Sénat |

**Avertissement, à ne pas rater :** `AN20` (« Travaux ») et `AN21`
(« Débat ») **ne sont pas des étapes de fabrication d'une loi.** Ce sont des
travaux de l'Assemblée qui n'aboutissent à aucun texte. Les 273 dossiers
concernés doivent être écartés d'un fil qui prétend suivre des lois, sinon
l'affichage mélange deux choses différentes.

**Autre avertissement :** certaines dates sont **dans le futur** — le fichier
contient les séances déjà programmées. Un tri par date la plus récente fait
donc remonter des étapes qui n'ont pas encore eu lieu. À traiter
explicitement.

## Le rapprochement avec le Sénat — résolu

C'est le point que le plan donnait pour le plus risqué. Il ne l'est pas.

- **910** des 3 055 dossiers de l'Assemblée portent un champ `senatChemin`,
  c'est-à-dire l'adresse du dossier correspondant sur `senat.fr`.
- Rapprochés du fichier `dossiers-legislatifs.csv` du Sénat : **901
  retrouvés directement (99,0 %)**, et **les 9 restants après normalisation**
  de l'adresse — ils utilisent l'ancienne forme `/dossierleg/` au lieu de
  `/dossier-legislatif/`. Soit **100 % au total**.
- Les 2 145 dossiers sans `senatChemin` ne sont pas un échec : ce sont les
  textes qui ne sont pas encore allés au Sénat, ou qui n'iront pas.

**Conséquence :** la stratégie C du §3.2 du plan (« recoller nous-mêmes par
titre, date et numéro ») est sans objet. Le rapprochement se fait sur une
adresse publiée par l'Assemblée elle-même.

## Les autres jeux de données

Tailles et dates relevées le 2026-08-31. Tous étaient à jour du jour même ou
de la veille.

| Jeu | Taille | Ce que c'est |
|---|---:|---|
| `Dossiers_Legislatifs.json.zip` | 10,3 Mo | Les dossiers et leurs étapes — **le cœur** |
| `Scrutins.json.zip` | 26,3 Mo | 8 434 scrutins publics de la législature |
| `Amendements.json.zip` | **297 Mo** | Tous les amendements. Volumineux, à ne charger que si nécessaire |
| `syseron.xml.zip` | 55,8 Mo | Les comptes rendus de séance (débats) |
| `Agenda.json.zip` | 7,8 Mo | L'agenda des réunions |
| `AMO10_…json.zip` | 4,9 Mo | Les députés en exercice et leurs mandats |

## Les scrutins

8 434 scrutins pour la 17e législature, répartis ainsi :

| Année | Scrutins |
|---|---:|
| 2024 (depuis juillet) | 525 |
| 2025 (année pleine) | **4 422** |
| 2026 (jusqu'au 31 août) | 3 487 |

- **8 339 sont des scrutins publics ordinaires**, 72 des scrutins solennels,
  23 des motions de censure.
- **5 585 rejetés, 2 849 adoptés.**
- L'immense majorité porte sur **des amendements**, pas sur des lois
  entières. C'est la confirmation du §8.2 du plan : afficher « les votes »
  sans trier n'a aucun intérêt pour un lecteur non spécialiste.

### Sur quoi portent les scrutins (mesuré le 2026-08-31)

| Scrutins | Portée |
|---:|---|
| 7 216 | un **amendement** |
| 866 | un **article** |
| **212** | **le texte entier** |
| 81 | une motion (rejet préalable, censure) |
| 59 | autre chose — une demande de suspension de séance, par exemple |

**212 votes sur un texte entier, sur 8 434 scrutins.** C'est le chiffre à
retenir avant de promettre « les votes » à un lecteur : ce qu'il cherche
— « ce texte a-t-il été adopté ? » — n'existe que 212 fois.

### Rattacher un vote à un texte : deux liens, ni l'un ni l'autre suffisant

| Sens du lien | Textes en cours retrouvés |
|---|---:|
| Le scrutin nomme son dossier (`objet.dossierLegislatif`) | 34 |
| Le dossier cite son scrutin (`voteRefs` sur un acte) | 68 |
| **Les deux réunis** | **71** |

Sur 1 990 textes en cours, **71 ont au moins un vote enregistré — 3,6 %.**
Ce n'est pas une lacune de la récupération : la plupart des textes sont
adoptés à main levée, ou jamais examinés.

### Un champ à ne pas croire : la position annoncée d'un groupe

Chaque scrutin donne, pour chaque groupe politique, une
`positionMajoritaire` — « pour », « contre », « abstention » — **et le
décompte des voix qui va avec**. Les deux ne concordent pas toujours.

Sur **101 208** positions de groupe examinées le 2026-08-31 :

| | |
|---|---:|
| D'accord avec leur décompte | 87 165 (86 %) |
| **En désaccord** | **3 033 (3 %)** |
| Indécidables (aucun votant, ou ex æquo) | 11 010 |

Un cas réel : un groupe annoncé **« pour »** dont **2 membres ont voté pour
et 16 contre**. Afficher cette position reviendrait à écrire une
contrevérité à l'écran.

**Conséquence pour le code :** `socle/extraction.py` ignore ce champ et
recalcule la position sur le décompte, qui, lui, ne se contredit pas.

### Les numéros de siège donnent l'ordre de l'hémicycle

Chaque vote publie, pour chaque député, son **numéro de place**
(`decompteNominatif.….votant.numPlace`). Sur **61 152** numéros relevés le
2026-08-31, les groupes se rangent sans ambiguïté :

| Groupe | Siège médian |
|---|---:|
| RN | 72 |
| UDR | 103 |
| DR | 184 |
| HOR | 231 |
| EPR | 301 |
| Dem | 345 |
| NI | 392 |
| SOC | 448 |
| LIOT | 456 |
| EcoS | 512 |
| GDR | 586 |
| LFI-NFP | 603 |

**L'hémicycle est numéroté de la droite vers la gauche.** Trier par numéro
décroissant donne donc l'ordre politique habituel, gauche → droite, **sans
qu'aucune liste soit écrite à la main** — ce qui compte, puisque les groupes
naissent et disparaissent en cours de législature.

Deux réserves : les **non-inscrits** sont dispersés dans tout l'hémicycle
(places 23 à 486), leur médiane n'a donc pas la même valeur informative ; et
des identifiants de groupes **dissous** apparaissent dans les votes anciens
sans figurer dans les données actuelles, qui ne décrivent que les groupes
existants.

**Aucune couleur n'est publiée.** Toute couleur affichée est une convention
de l'application, pas une donnée.

### Un rejet n'est pas une fin, et rien ne dit qu'il l'est

L'Assemblée enregistre les rejets, mais **n'écrit jamais qu'un texte est
terminé** autrement que par une promulgation ou un retrait. Mesuré le
2026-08-31 :

| | |
|---|---:|
| Conclusions contenant « rejet » | 43 |
| Textes de loi ayant connu un rejet | **27** |
| dont le parcours a **continué** ensuite | **19** |
| dont plus rien n'a suivi | 8 |
| Décisions du Conseil constitutionnel | 38, dont **1 « non conforme »** |

**Dans 19 cas sur 27, le texte a poursuivi sa route après avoir été rejeté.**
Un rejet en première lecture n'est donc pas un point final, et prendre l'un
pour l'autre serait une erreur de fond.

Pour les 8 autres, rien dans les données ne distingue « rejeté et abandonné »
de « rejeté et en attente ». Le socle les marque `rejete` — c'est-à-dire
« la dernière décision connue est un rejet » — et **ne dit pas que c'est
définitif**, parce que la source ne le dit pas.

C'est le Sénat, et lui seul, qui emploie des mots de fin : `non adopté`,
`caduc`, `retiré`. Voir `senat.md`.

### Les amendements ne sont pas des différences, et le texte des articles n'est pas publié

**Vérifié le 2026-08-31.** C'est le point qui interdit d'afficher un texte
modifié en rouge et barré, et il vaut la peine d'être écrit une fois pour
toutes.

Un amendement se présente ainsi, mot pour mot :

> « Compléter l'alinéa 7 par les mots : « , après avis simple des
> organisations professionnelles représentant les exploitants agricoles ». »

> « À l'alinéa 2, substituer à la référence : « L. 1174‑3 » la référence :
> « L. 1174‑1 ». II. – En conséquence, procéder à la même substitution à
> l'alinéa 9. »

**C'est une instruction en français juridique, pas un « avant / après ».**
Reconstituer le texte modifié demanderait deux choses :

1. **Le texte original des articles.** Il n'est pas dans l'open data. Les
   7 070 documents de l'archive ne portent que des métadonnées ; le champ
   `divisions`, qui pourrait contenir le texte découpé, est vide dans les
   6 763 cas utiles et ne désigne, dans les 307 autres, que des annexes.
   L'Assemblée publie ses textes en pages web, pas en données.
2. **Un programme capable d'interpréter ces instructions** — « substituer
   aux mots », « rédiger ainsi », « en conséquence, procéder à la même
   substitution ». C'est de la compréhension de langue, pas de la lecture de
   données.

Le résultat serait **un texte de loi fabriqué par nous, faux dans une
proportion inconnue, et présenté comme officiel.** C'est exactement le risque
décrit au §8.4 du plan. Ce n'est donc pas fait, et cela ne devrait pas
l'être sans une source du texte des articles.

**Ce qui est fait à la place :** l'instruction est affichée telle quelle, et
les passages que la source met elle-même entre guillemets sont colorés — vert
pour ce qui est ajouté, rouge barré pour ce qui est retiré ou remplacé,
d'après le verbe de l'instruction. Un test vérifie que la coloration
reconstitue le texte à l'identique, donc qu'aucun mot n'est perdu ni ajouté.

### Volume des amendements

| | |
|---|---:|
| Amendements de la législature | **109 854** |
| Dossiers concernés | 289 |
| Médiane par dossier | 60 |
| Record | **19 510** sur un seul dossier |
| Sans dispositif (irrecevables, cavaliers) | environ 1 sur 4 |

C'est ce record qui impose un plafond à la publication : tout servir ferait
un fichier de plusieurs dizaines de méga-octets pour un écran de téléphone.

### Les photos des députés

Elles ne sont pas dans l'open data, mais le site les sert à une adresse qui
se déduit de l'identifiant :

```
https://www2.assemblee-nationale.fr/static/tribun/17/photos/<identifiant sans PA>.jpg
```

Testé le 2026-08-31 sur douze députés tirés au hasard : **dix réponses, deux
coupures réseau, aucune absente.** Elles ne portent pas d'en-tête
`Access-Control-Allow-Origin`, ce qui n'empêche pas de les afficher — une
image n'y est pas soumise, contrairement à une lecture de données.

### Les votes à venir n'existent pas

L'agenda de l'Assemblée (`Agenda.json.zip`) a été examiné le 2026-08-31 :
**26 réunions à venir**, toutes des auditions en commission ou des réunions
internes. Aucune séance publique, aucun texte à l'ordre du jour, aucun vote
annoncé — et `pointsODJ` vide dans les 26 cas.

**Un vote n'apparaît dans les données qu'une fois qu'il a eu lieu.** Ce qui
existe et regarde vers l'avant, ce sont les séances déjà programmées, rien
de plus. Une rubrique « votes à venir » serait donc vide, ou devinée.

## Les débats — la mesure qui conditionne les coûts

Mesuré sur les 601 comptes rendus de séance de la 17e législature
(juillet 2024 → juillet 2026), balises retirées :

| | Par séance |
|---|---:|
| Texte utile, médiane | **197 918 caractères** |
| Texte utile, moyenne | 198 431 caractères |
| La plus courte | 3 164 caractères |
| La plus longue | 402 340 caractères |
| Fichier XML brut, médiane | 511 Ko |

**Total sur deux ans : 119,3 millions de caractères.**

Nombre de séances : 68 en 2024 (depuis juillet), **314 en 2025**, 219 en 2026
jusqu'à fin juillet.

**Attention à l'unité.** Ces fichiers sont **par séance**, pas par journée.
Une journée compte souvent deux ou trois séances. Le Sénat, lui, publie un
fichier par journée — les deux chiffres ne se comparent donc pas directement.

En 2025, année pleine : **314 séances, 63,1 millions de caractères**.

Le calcul de coût des deux chambres réunies est dans
[`README.md`](README.md).
