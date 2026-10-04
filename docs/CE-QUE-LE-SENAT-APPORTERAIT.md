# Ce que le Sénat pourrait apporter à l'application

**Mesuré le 2026-10-04.** Tous les chiffres de ce document ont été relevés ce
jour-là sur les fichiers publiés par `data.senat.fr` et sur notre propre base.
Les commandes qui les produisent sont dans `tmp/senat/`.

Ce document complète `docs/sources/senat.md`, qui décrit la source elle-même.
Celui-ci répond à une autre question : **qu'est-ce qu'on pourrait montrer, et
pour combien de textes ?**

## En un coup d'œil

| Ce que le Sénat apporterait | Textes concernés | Verdict |
|---|---:|---|
| Un **thème** (le sujet du texte) | 730, dont **les 107 lois promulguées** | **Le moins cher.** 30 thèmes, aucun calcul, dans un fichier déjà téléchargé |
| Les **amendements du Sénat**, texte entier et auteur | 184 textes, dont **70 des 107 lois promulguées** | **Le plus utile.** Le lien est publié par la source, 15,7 Mo |
| Un lien vers **« La loi en clair »**, écrite par le Sénat | 119 | Un lien d'une ligne |
| Les **sénateurs** : nommer, et leur photo | 348 sénateurs | Faisable, mais le Sénat est en recomposition et l'hémicycle ne se range pas |
| **Ce que les groupes ont dit** au Sénat | 205 textes, dont **108 qui n'ont rien aujourd'hui** | Faisable, mais **545 Mo par jour** à récupérer |
| **Qui a voté quoi au Sénat** (1,66 million de votes nominatifs) | — | **Fermé.** Rien ne relie un scrutin à un texte |

**Le chiffre à retenir : 730 de nos 731 textes passés au Sénat y sont
retrouvés, et les 107 lois promulguées aussi.** La couverture n'est pas un
problème. Quand on lit « 33 % de nos textes », ce n'est pas un défaut de
rapprochement : c'est que deux textes sur trois ne sont jamais allés au Sénat
(des propositions déposées et jamais examinées).

## Ce que le Sénat nous donne déjà

Le socle le récupère depuis le 2026-08-31, pour une seule chose : **lui seul
sait dire qu'un texte est fini sans avoir été promulgué.** Vérifié à nouveau
aujourd'hui, c'est toujours vrai et toujours utile — **35 de nos textes** ont
leur statut final grâce à lui :

| Textes | Notre statut | Ce que le Sénat écrit |
|---:|---|---|
| 21 | non adopté | « non adopté » |
| 6 | retiré | « retiré » |
| 5 | *(encore « en cours » chez nous)* | « caduc » |
| 2 | caduc | « caduc » |
| 1 | non adopté | « Non conforme à la constitution » |

Les 5 lignes « encore en cours » ne sont pas un défaut : notre base locale date
du 20 septembre, le fichier du Sénat d'aujourd'hui. Ces textes sont devenus
caducs entre-temps, et la publication du matin les a déjà corrigés.

C'est tout ce qu'on en prend. **Le reste du fichier est jeté**, et il y a
beaucoup dedans.

## 1. Les amendements du Sénat — la vraie trouvaille

**La source publie elle-même le lien entre un amendement du Sénat et le
dossier.** La table des textes amendés porte une colonne `doslegsignet`, qui
est exactement l'adresse de dossier que l'Assemblée publie de son côté. Aucun
rapprochement par titre, aucune devinette.

| | |
|---|---:|
| Amendements du Sénat dans la base AMELI | 273 665 |
| Rattachés à un dossier par la source | **271 520** (99,2 %) |
| Sur **nos** textes | 25 782, sur 184 textes |
| Dont **adoptés** | **6 744**, sur 168 textes |
| Dont **adoptés, sur une loi promulguée** | 70 lois sur 107 |

**Ce que porte chaque amendement**, et c'est exactement ce que l'application
affiche déjà pour l'Assemblée :

- son **texte entier** (le dispositif) — 248 318 amendements en ont un,
  1 129 caractères en moyenne ;
- son **exposé des motifs** — 234 131 en ont un, 1 251 caractères ;
- son **auteur, nommé, avec son groupe politique** — 89 % des adoptés de nos
  textes, cosignataires compris (2 en médiane) ;
- l'**article** qu'il vise, sa **date de dépôt**, et son **sort** (adopté,
  rejeté, retiré, tombé, non soutenu…).

**Ce que ça coûterait : 15,7 Mo**, en 6 744 fichiers de 1,7 Ko en médiane — à
comparer aux 33,7 Mo que pèsent déjà les 12 759 fiches d'amendements de
l'Assemblée. Le modèle d'affichage existe, il n'y a rien à inventer.

Aujourd'hui, la fiche d'un texte montre 94 029 amendements de l'Assemblée sur
ces mêmes 184 textes, et **zéro du Sénat**. Un lecteur qui veut savoir ce que
le Sénat a changé à un texte ne le trouve nulle part.

## 2. Le sujet d'un texte — ce qui manque le plus, et qui ne coûte rien

**L'application n'a aucune notion de sujet.** On peut filtrer par étape, par
chambre, par type, par état — jamais par « santé », « logement » ou
« justice ». Le Sénat, lui, classe chaque dossier.

- **30 thèmes** au total, deux par texte en médiane (cinq au plus) ;
- **730 de nos textes en portent au moins un — soit tous ceux qui ont un lien
  Sénat**, et les 107 lois promulguées ;
- le champ est **dans le fichier CSV qu'on télécharge déjà chaque matin**. Il
  n'y a rien de plus à récupérer.

Les plus courants, sur l'ensemble de la base du Sénat : Société, Pouvoirs
publics et Constitution, Économie et finances fiscalité, Collectivités
territoriales, Questions sociales et santé.

**Un piège mesuré** : trois noms de thème contiennent eux-mêmes une virgule —
« Économie et finances, fiscalité », « PME, commerce et artisanat »,
« Recherche, sciences et techniques ». Découper naïvement sur la virgule donne
33 thèmes au lieu de 30, et en invente trois qui n'existent pas.

**La limite, et elle est réelle :** deux textes sur trois n'ont pas de thème,
parce qu'ils ne sont jamais allés au Sénat. Un filtre par sujet laisserait donc
de côté la majorité du fil. Pour les lois promulguées, en revanche, la
couverture est totale.

## 3. « La loi en clair » — un lien, pas un texte

Le Sénat écrit, pour certaines lois, une explication en langage ordinaire.
**119 de nos textes en ont une.**

Mais **l'open data n'en publie pas le contenu** : seulement une adresse web et
une phrase d'accroche qui dit « Consultez "La loi en clair" pour décrypter le
texte » — 96 caractères en médiane, la même pour tout le monde. Ce n'est pas un
résumé, c'est une invitation.

Ce qu'on peut en faire : **un lien**, à côté du lien vers le texte officiel.
C'est peu de travail et ça mène à une explication écrite par des humains, ce
que l'application ne peut offrir nulle part ailleurs — ses propres descriptions
sont écrites par une IA et le disent.

## 4. Qui a voté quoi au Sénat — la réponse est non, et voici pourquoi

C'est ce qui manquerait le plus : la fiche d'une loi montre le vote de chaque
groupe à l'Assemblée, et **rien** pour le Sénat. Les données existent
pourtant : **4 764 scrutins et 1 657 344 votes nominatifs** de sénateurs.

**Rien ne les relie à un texte.** L'étape 0 l'avait dit le 2026-08-31 ; je l'ai
re-vérifié en cherchant un chemin, et en le chiffrant.

Il existe bien une table qui relie un scrutin à un amendement. Mais elle ne
donne que le **numéro** de l'amendement et l'année de session — et un numéro ne
désigne pas un amendement à lui seul, puisque chaque texte numérote les siens à
partir de 1 :

| Ce qu'on essaie | Scrutins rattachés à un seul texte |
|---|---:|
| Le numéro d'amendement et l'année de session | 990 sur 4 663 — **21 %** |
| En ajoutant une fenêtre de dates de 30 jours | 2 027 — **43 %** |
| En ajoutant le calendrier des séances du Sénat | **impossible : le calendrier est vide** |

La table des séances du Sénat contient **13 lignes**. Celle des dates de
lecture n'en couvre que 421 jours. Aucune des deux ne permet de dire quel texte
était examiné le jour d'un scrutin — alors que c'est exactement la règle qui
marche pour l'Assemblée.

Le seul rattachement qui resterait passe par **l'intitulé du scrutin** :

> sur l'amendement n° I-1334, présenté par M. Claude Raynal, à l'article 15 du
> projet de loi

C'est-à-dire un rapprochement par titre — ce que le projet refuse, et ce que
son propre plan qualifie de « coûteux, fragile, jamais fiable à 100 % ».

**Conclusion : on n'affichera pas les votes du Sénat.** Ce n'est pas un choix
de confort : la donnée est là, mais rien ne dit à quel texte elle appartient.
Mieux vaut ne rien montrer que de se tromper de texte.

## Deux pièges techniques, mesurés

1. **Les deux dumps du Sénat n'ont pas le même encodage.** Celui des
   amendements déclare `LATIN1`, celui des dossiers `UTF8` — dans des fichiers
   publiés par le même service, le même jour. Lu en UTF-8, le premier affiche
   `Rejet?` au lieu de `Rejeté`.
2. **Le texte des amendements est du HTML avec des entités** (`&#233;` pour
   « é »), pas du texte brut. Il faut le nettoyer avant de l'afficher, comme on
   le fait déjà pour les comptes rendus de l'Assemblée.

## 5. Les sénateurs — tout est là, sauf le plan de la salle

**348 sénateurs**, exactement le nombre de sièges, dans un fichier mis à jour
le jour même. Pour chacun : **nom, prénom, civilité, circonscription, série et
photo à 100 %**. Les photos sont 348 images distinctes, 512 × 512, aucune
pastille générique.

### Une exception à une règle du projet, vérifiée

CLAUDE.md dit qu'« une page web ne peut pas aller chercher ces données
elle-même », parce que les portails n'envoient pas l'en-tête qui l'autorise.
**C'est faux pour un fichier du Sénat, et je l'ai vérifié moi-même :**

| Adresse | En-tête `Access-Control-Allow-Origin` |
|---|---|
| `www.senat.fr/api-senat/senateurs.json` | **`*`** — une page web peut le lire |
| `www.senat.fr/senimg/<photo>.jpg` | **`*`** — les photos aussi |
| `data.senat.fr/...csv` et `...zip` | aucun |

Ce fichier n'est pas sous `data.senat.fr` et **sa licence n'est pas vérifiée**.
À régler avant de s'en servir.

### Deux choses que ce fichier a et que les CSV n'ont pas

- **Le numéro de siège** — il n'est dans aucun des 14 fichiers CSV.
- **L'adresse de la photo** — nulle part ailleurs non plus.

### Le Sénat est dans un état transitoire, et l'écran s'en ressentirait

Le renouvellement du 27 septembre 2026 vient d'avoir lieu. Tous les groupes ont
été clos le 30 septembre et les sénateurs ne se sont pas encore redéclarés :

| | Sénateurs |
|---|---:|
| **Sans groupe** (« Aucun ») | **179** |
| Les Républicains | 53 |
| SER | 34 |
| UC | 29 |
| CRCE-K | 14 |
| Les Indépendants | 11 |
| GEST | 9 |
| RDPI | 8 |
| RDSE | 8 |
| Non inscrits | 3 |

Et **280 sénateurs sur 348 ont un numéro de siège** : les 68 qui n'en ont pas
sont exactement les nouveaux arrivants. Un hémicycle dessiné aujourd'hui serait
à moitié gris. Il se remplira de lui-même, mais **la page devrait le dire**
plutôt que de laisser croire à 179 non-inscrits.

### L'ordre gauche-droite ne peut pas se mesurer comme à l'Assemblée

À l'Assemblée, l'ordre des groupes est **mesuré** sur les numéros de siège. Au
Sénat, la même méthode échoue, et c'est mesuré :

- les médianes rangent les groupes **à l'envers** du sens politique ;
- en lisant les sièges dans l'ordre, **le groupe change 152 fois** — ou 51 fois
  si on rend leur groupe d'avant le renouvellement aux sans-groupe actuels.
  Dans un hémicycle rangé par blocs, il changerait 9 fois ;
- les groupes se chevauchent d'un bout à l'autre de la salle : **Les
  Républicains occupent les sièges 8 à 346, UC les sièges 6 à 325** ;
- la numérotation est cyclique (elle tourne rang par rang), et **aucun plan de
  salle n'est publié** : cinq adresses du site ont été essayées, toutes en 404
  ou 403.

Le champ `ordre` du fichier n'est pas non plus gauche-droite : c'est un ordre
protocolaire.

**Une autre règle marche, et elle reste une mesure.** En calculant, sur les
421 scrutins disputés depuis 2024, l'axe qui sépare le mieux les groupes par
leurs votes, on obtient un classement qui porte 64 % de ce qui les sépare :

> GEST · CRCE-K · SER — RDSE — RDPI · UC · Indépendants · LR

Il sépare nettement la gauche, le centre et la droite. **Il ne départage pas
les trois groupes de gauche entre eux**, ni UC et Indépendants : à l'intérieur
de ces blocs, l'ordre resterait une convention assumée, comme les couleurs.

### Ce qui manque

- **Aucune couleur de groupe n'est publiée** — comme à l'Assemblée, ce serait
  une convention d'affichage à assumer.
- **Les dates des mandats en cours** : 151 des 348 actifs n'ont pas encore de
  mandat enregistré, le renouvellement n'étant pas saisi.
- **Ni vote ni parole depuis le 21 juillet 2026** : le Parlement est en
  vacances, les fichiers s'arrêtent là.

### Nommer quelqu'un : ça marche partout

| Nommer… | Rapproché à |
|---|---|
| l'auteur d'un **texte** | 100 % |
| l'auteur d'un **amendement** (avec son groupe) | 89 % des amendements depuis 2024 ; le reste est le Gouvernement et les commissions |
| un **vote nominatif** (prénom, nom, et le groupe **au jour du scrutin**) | **100 %** sur 278 552 votes depuis 2024 |

Tous ces rapprochements sont des clés publiées par la source, pas des
rapprochements par titre.

**Deux pièges relevés**, qui coûteraient cher à redécouvrir :

1. **Ne pas nommer un sénateur par la table `auteur` du dossier législatif** :
   la même personne y figure plusieurs fois (sénateur, député, ministre). Le
   fichier des sénateurs a une seule ligne par personne et fait foi.
2. **Ne pas dater un mandat avec `auteur.datdeb`/`datfin`** : ces colonnes ne
   sont remplies que sur 196 et 123 lignes sur 2 260.

## 6. Ce que les groupes ont dit au Sénat — faisable, et ce n'est pas donné

L'onglet « Débats » d'une fiche ne montre que l'Assemblée. Le Sénat publie
l'équivalent, et **le rattachement d'une parole à un dossier est fait par la
source**, par identifiant, jamais par titre. Vérifié à part : sur les **109 968
sections de discussion du Sénat, 8 seulement** n'ont pas de dossier — 0,007 %.

| | |
|---|---:|
| Nos dossiers avec au moins une prise de parole en « Discussion générale » ou « Explications de vote » | **205 sur 730** |
| dont les lois promulguées | **89 sur 107** |
| dont des dossiers **sans aucune parole côté Assemblée** aujourd'hui | **108** |
| Poids publié, au modèle actuel | **≈ 15 Mo** |

Pour comparer, l'Assemblée pèse aujourd'hui 13 Mo en 172 fichiers. Les 525
dossiers sans parole ne sont pas un échec : 495 n'ont tout simplement pas
encore été débattus en séance.

### Le prix d'entrée : 545 Mo par jour

**L'index des débats ne contient aucune parole.** 73 % des interventions n'ont
aucun texte, 12 % ne portent qu'un renvoi de page (« p. 4042 et suivantes »), et
le reste fait 16 caractères en médiane. Le dernier vrai texte date de 2010.

Le texte mot pour mot est dans une autre archive, de **545 Mo** — dix fois celle
de l'Assemblée, qui fait déjà partie des sources facultatives parce qu'elle
casse. Le serveur accepte les téléchargements partiels, ce qui permettrait de
ne prendre que les derniers jours, **mais cela n'a pas été testé**.

### Trois différences avec l'Assemblée, à ne pas découvrir en route

1. **Le compte rendu du Sénat n'imprime pas le groupe de l'orateur.** Celui de
   l'Assemblée le fait. Il faudrait donc un **troisième fichier** pour le
   retrouver à la date du débat. Ça marche — 100 % des paroles y trouvent un
   groupe unique, et quand l'orateur dit lui-même « au nom du groupe X », le
   fichier dit la même chose **764 fois sur 765**. Mais c'est un fichier de
   plus, qui se périme.
2. **Les sections du Sénat contiennent plus de monde.** 39 % des interventions
   sont du président de séance, 6 % du Gouvernement, 8 % de rapporteurs.
   Seules 47 % sont des orateurs de groupe probables — et « probable » est le
   mot juste : au moins 3,3 % des longues prises de parole sont en fait d'un
   rapporteur ou d'un président de commission dont la qualité n'est pas
   imprimée.
3. **La règle « un orateur par groupe » est fausse au Sénat.** Elle ne tient
   que dans 89,5 % des cas.

Il faudrait aussi **écarter les interjections** : « Tout à fait ! », « Excellent
! » sont enregistrées comme des interventions, et un dixième des prises de
parole fait moins de 12 caractères.

### Deux pièges mesurés dans l'archive du Sénat

- **Un fichier fantôme** : le compte rendu daté du 4 décembre 2026 est une
  copie exacte de celui du 4 décembre 2025. Lire l'archive sans passer par
  l'index compte deux fois le même débat et le date dans le futur.
- **L'index est en retard sur le texte** : il s'arrête au 21 juillet 2026,
  l'archive contient le 1er octobre.

### Ne pas filtrer les sections par leur titre

La source **typecode** les sections : « Discussion générale » et « Explications
de vote » ont un code. Le titre affiché, lui, varie — les comptes rendus
récents écrivent « Vote sur l'ensemble ». Filtrer sur le titre fait perdre 40 %
des interventions.

## Ce que je ferais, dans l'ordre

| | Ce que ça apporte | Ce que ça coûte |
|---|---|---|
| **1. Le thème d'un texte** | Un sujet pour 730 textes et **les 107 lois promulguées** ; le premier filtre par sujet de l'application | Presque rien : le champ est dans un fichier déjà téléchargé chaque matin |
| **2. Les amendements du Sénat** | Ce que le Sénat a changé à un texte : 6 744 amendements adoptés sur 168 textes, avec texte entier, auteur et groupe | Une archive de 154 Mo en plus, 15,7 Mo publiés. Le modèle d'affichage existe déjà |
| **3. Le lien « La loi en clair »** | Une explication écrite par des humains, pour 119 textes | Un lien |
| **4. Les sénateurs** | Nommer l'auteur d'un amendement du Sénat, avec sa photo et son groupe | Un fichier léger, lisible directement par une page web |
| **5. Les paroles du Sénat** | L'argumentaire de 205 textes, dont 108 qui n'en ont aucun aujourd'hui | **545 Mo par jour**, et trois règles d'affichage à inventer |
| — | **Qui a voté quoi au Sénat** | **Impossible** sans rapprocher par titre |

Les quatre premiers points se tiennent. Le cinquième est un vrai projet, à
décider pour lui-même. Le dernier est fermé, et il vaut mieux le savoir.

## Ce qui reste à vérifier avant de s'en servir

- **La licence du fichier des sénateurs** : il n'est pas publié sous
  `data.senat.fr` et sa licence n'a pas été vérifiée.
- **Le téléchargement partiel de l'archive des débats** : le serveur dit
  l'accepter, personne ne l'a essayé.
- **Un dossier du Sénat pour deux des nôtres** : le signet `pjl24-869` est
  partagé par deux de nos dossiers, qui recevraient les mêmes paroles.
- **Quatre textes budgétaires** (`pjlf2026`, `plfss2026` et leurs
  prédécesseurs) portent une adresse de dossier d'une autre forme, que la
  règle de rapprochement actuelle ne reconnaît pas.
