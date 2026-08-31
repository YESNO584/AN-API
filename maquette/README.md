# Maquette — le fil des textes en cours

**Étape 1 du plan** (`../docs/PLAN.md`, §6). Un écran qu'on peut mettre entre
les mains de quelqu'un pour regarder s'il comprend.

Un seul fichier : **`feed.html`**. Il s'ouvre dans un navigateur, au format
téléphone.

**En ligne : <https://yesno584.github.io/AN-API/>** — le socle la publie
comme page d'accueil à chaque mise à jour des données. C'est la façon la plus
simple de la regarder depuis un téléphone, sans rien installer.

## Ce qu'elle montre

**2 150 textes**, rangés par étape du parcours en **colonnes côte à côte** —
une catégorie par colonne, **dans l'ordre où un texte les traverse**. Les
**61 textes arrêtés en chemin** ouvrent le fil — ce n'est pas une étape du
parcours mais une sortie de route, et la mettre en tête laisse les six étapes
se suivre sans être coupées. Viennent ensuite le **dépôt**, la commission, la
séance publique, la navette, sa sortie, l'après-vote, et les **107 lois
promulguées** tout à droite. Le fil se lit donc comme une frise, de la plus
ancienne étape à la plus récente — et la frise du bas en est le reflet exact.

**Le fil s'ouvre sur « Promulguée »**, la catégorie la plus avancée : c'est là
que se passe l'actualité, et les 1 729 textes restés au dépôt sont à un
glissement de là, vers la gauche. L'ordre des colonnes dit le parcours, la
colonne d'ouverture dit l'intérêt — ce sont deux questions différentes.

**Une seule colonne est visible à la fois.** On passe à la suivante en faisant
glisser vers la gauche ou la droite, ou avec les flèches **‹ ›** posées à côté
du nom de la catégorie.

**La frise est accrochée en bas de l'écran, une bonne fois.** Huit traits, dans
l'ordre exact des colonnes : **arrêté en chemin**, puis les six étapes du
parcours, puis **la promulgation**. Ils disent où l'on se trouve et servent à
s'y rendre : toucher un trait mène à sa colonne. Le trait de la promulgation
**s'allume en vert** quand on y est ; le reste du temps il est éteint, comme
les autres. La frise ne figure plus sur chaque carte : tous les textes d'une
colonne étant à la même étape, la répéter n'apprenait rien.

**Une étape sans texte garde son trait**, en pointillé. « Après le vote » —
le contrôle du Conseil constitutionnel — est presque toujours vide : un texte
n'y reste que quelques jours. Le masquer ferait changer la frise de forme d'un
jour à l'autre, et elle cesserait d'être un repère. Le trait se touche quand
même, et dit ce qu'il est.

**Changer d'étape ramène en haut.** Sans quoi, en changeant de colonne après
être descendu dans la liste, on atterrissait au milieu de la suivante. La
remontée est immédiate, sans déroulé : sur un changement de colonne, une
animation donnerait l'impression que la page part toute seule.

**Le tour est sans fin** : après « Arrêté en chemin » vient « Dépôt », et
inversement. Le navigateur refusant de faire défiler au-delà des bords, une
**copie de la colonne d'en face** est posée de chaque côté — prise sur ce qui
est déjà affiché, 25 cartes, pas les 1 729 du dépôt. Dès que le défilement
s'immobilise sur une copie, la page saute sans animation sur la vraie colonne,
à l'autre bout. Le saut ne se voit pas : on tombe sur une image identique à
celle qu'on regardait. Les flèches font le tour elles aussi, et ne sont plus
grisées aux extrémités. Toutes les colonnes commencent en haut, sous
l'en-tête : les textes restent donc alignés d'une colonne à l'autre, et le
défilement vertical reste celui de la page. Une catégorie sans texte — ce qui
arrive dès qu'un filtre est actif — n'a pas de colonne. Chaque colonne charge
ses textes par paquets de 25, pour elle seule : un compteur commun laisserait
les dernières colonnes vides tant qu'on n'a pas tout affiché dans les
premières.

Conséquence assumée de cet alignement : la page est aussi haute que la colonne
la plus fournie, donc une colonne courte laisse du vide sous elle. La seule
façon de l'éviter serait de faire défiler chaque colonne séparément, ce qui
désalignerait les textes.

Un texte arrêté porte le mot de sa source — **rejeté**, **non adopté**,
**retiré**, **caduc**. **Nulle part la page ne dit qu'un texte est fini pour
de bon** : un texte rejeté peut être redéposé, et les sources ne se
prononcent pas là-dessus. L'explication au toucher le dit noir sur blanc.

Une application qui s'appelle « Où en sont les lois » doit montrer celles qui
sont allées au bout : la carte d'une loi promulguée porte son **numéro
officiel**, sa date et un lien vers le **Journal officiel**.

### Les filtres

| Filtre | Ce qu'il permet |
|---|---|
| **Étape** | Les six étapes du parcours |
| **Où le texte se trouve** | Assemblée, Sénat, ou les deux (commission mixte paritaire) |
| **Nature du texte** | Proposition, projet, loi organique, constitutionnelle, budget, ratification… |
| **Dernier mouvement** | Cette semaine, ce mois-ci, ces trois mois — ou à l'arrêt depuis plus d'un an |
| **Issue** | En cours, promulguée, rejetée, non adoptée, retirée, caduque |
| **Votes** | A fait l'objet d'un vote, voté sur le texte entier, adopté, rejeté |
| **Calendrier** | Les textes dont une séance est déjà programmée |
| **Recherche** | Dans les titres |

Ils se combinent, chacun affiche son nombre de textes, ceux qui ne mèneraient
à rien sont grisés, et un bouton efface tout.

### La fiche d'un texte

Toucher un titre ouvre **une fiche**, à l'adresse `#/texte/<identifiant>`,
partageable et ouvrable directement. Elle contient :

- le **titre** et la **description** du texte ;
- son **auteur** — photo, nom, groupe en couleur — et ses **cosignataires** ;
- les **liens officiels** : dossier à l'Assemblée, dossier au Sénat, et le
  **texte de loi au Journal officiel** quand elle est promulguée ;
- le **parcours complet**, étape par étape, datée, **les votes intercalés à
  leur date** — voir la section suivante ;
- les **amendements**, chargés à la demande.

Chaque bloc est un dépliant : la fiche s'ouvre sur le parcours, le reste se
déroule à la demande.

### Le parcours, et pourquoi deux lignes du même jour ne sont pas un doublon

Chaque étape porte **une pastille de chambre** — Assemblée, Sénat, ou « hors
chambre » pour une commission mixte paritaire et le Conseil constitutionnel —
et se déplie sur **ce que l'acte dit de lui-même** : la commission qui s'est
réunie, le rapporteur désigné, le document déposé, **le texte qui sort du
vote**, le motif d'une saisine.

**Aucune de ces phrases n'est écrite par la maquette.** Elle affiche le nom du
champ et recopie la valeur publiée par l'Assemblée. Quand la source ne dit
rien, la fiche le dit : « L'open data ne publie rien de plus sur cette étape
que sa nature et sa date. »

Une chambre siège plusieurs fois par jour. Deux lignes de même nom et de même
date sont donc distinguées par ce qui les sépare vraiment — l'heure
(« 09 h 00 »), ou le nom que l'Assemblée donne à la séance (« 2e séance »).
Les 89 groupes d'actes que rien ne distingue sont fusionnés en amont, par le
socle : voir `../socle/README.md`.

### Les votes sont dans le parcours

Un vote n'est pas une liste à part : il se produit à un moment du parcours, et
c'est ce moment qui l'explique. Les scrutins sont donc intercalés entre les
étapes, à leur date.

**Ils viennent après les étapes du même jour**, pour une raison mesurée :
l'open data ne dit pas à quel moment de la journée un scrutin a eu lieu — son
champ `referenceLegislative` est vide dans les 8 434 scrutins de la
législature. Les placer ailleurs serait une invention.

### Les amendements, et ce qu'on n'affiche pas

**Un amendement n'est pas une version modifiée du texte.** C'est une
instruction, reproduite ici **mot pour mot** :

> Compléter l'alinéa 7 par les mots : « , après avis simple des organisations
> professionnelles représentant les exploitants agricoles ».

**Le texte modifié n'est pas reconstitué, et ne peut pas l'être** : le texte
original des articles n'est pas publié en open data, et appliquer ces
instructions demanderait de comprendre du français juridique. Le résultat
serait un texte de loi fabriqué, faux dans une proportion inconnue et
présenté comme officiel.

Ce qui est fait : **les passages que l'amendement met lui-même entre
guillemets sont colorés** — vert pour ce qu'il ajoute, rouge barré pour ce
qu'il retire ou remplace, d'après le verbe de l'instruction. La page le dit
en toutes lettres au-dessus de la liste. Rien n'est inventé, et le texte
affiché reste celui de la source, à la lettre près.

Deux plafonds, imposés par le volume — un texte compte jusqu'à 19 510
amendements : **150 amendements détaillés par texte**, les adoptés d'abord,
et l'exposé de l'auteur écourté à 400 caractères. Le compte réel est affiché.

## Les explications

**Chaque élément affiché se touche et explique ce qu'il est**, en français
simple : l'étape, la chambre, la nature du texte, la lecture, le dernier
acte, le résultat d'un vote, la date, la frise, et chaque filtre.

Sur un téléphone il n'y a ni survol de souris ni clic droit : l'explication
s'ouvre donc **au toucher**, dans un panneau qui vient du bas. Dans le
panneau des filtres, un petit **ⓘ** à côté de chaque puce évite de confondre
« je veux comprendre » et « je veux filtrer ».

## D'où viennent les données

Du socle (voir `../socle/README.md`), publié chaque matin. La page les lit en
direct au chargement — c'est exactement le chemin que suivra l'application
Flutter, donc la maquette essaie le dispositif autant que le dessin.

**Elle lit à côté d'elle**, par une adresse relative : publiée au même
endroit que les données, elle fonctionne partout où on la copie. Seule
exception, quand on l'ouvre depuis un fichier (`file://`) : il n'y a alors
rien à côté d'elle, et elle vise l'adresse publique.

Il n'y a **plus de préparation hors ligne** : le script qui servait à cela a
disparu, le socle publie tout.

### Viser un socle local

```
feed.html?socle=http://127.0.0.1:8000
```

Utile pour travailler sans réseau, ou pour essayer une modification du socle
avant de la publier. Pour servir une copie locale :

```bash
cd ../socle && ./publier.py && (cd public && python3 -m http.server 8000)
```

En ouvrant alors `http://127.0.0.1:8000/feed.html?socle=http://127.0.0.1:8000`
après y avoir copié la page, tout tient sur une seule adresse.

## Les votes

Quand un texte a été voté, sa carte porte le résultat : **« Adopté — 378 pour,
7 contre, 173 abstentions »**. Le toucher ouvre le **détail par groupe
politique**, sous forme de barres, chargé à la demande depuis le fichier de
détail du texte.

Trois précautions, parce que le sujet se prête aux malentendus :

1. **Un vote sur un amendement n'est pas un vote sur le texte.** La carte
   distingue les deux : « Adopté » n'apparaît que pour un vote sur l'ensemble.
   Un texte qui n'a que des votes d'amendements affiche « 140 votes
   enregistrés — sur des amendements ou des articles ».
2. **Peu de textes ont un vote** : 71 sur 1 990. Le filtre affiche le compte,
   pour que le chiffre se voie au lieu de se deviner.
3. **La position des groupes est recalculée** sur le décompte des voix, parce
   que celle annoncée par la source la contredit dans 3 % des cas.

Les groupes sont **rangés comme dans l'hémicycle, de la gauche à la droite**.
Cet ordre est **mesuré** sur les numéros de siège que l'Assemblée publie, pas
décidé. Leur **couleur, elle, est une convention** d'affichage — l'open data
n'en publie aucune — et la page le dit au toucher. Les barres continuent de
montrer pour / contre / abstention : la couleur dit *qui*, la barre dit *quoi*.

**Il n'y a pas de « votes à venir »**, et la maquette le dit explicitement au
lieu de laisser une rubrique vide : l'Assemblée ne publie un vote qu'une fois
qu'il a eu lieu. Ce qui existe à l'avance, ce sont les séances programmées.

## Ce que la maquette ne fait pas

Ni favoris, ni alertes, ni comptes, ni écran de détail par texte — le titre
renvoie au dossier officiel. Ce sont les étapes suivantes du plan.

## Les trois règles qui font que le fil est juste

Elles ne sont pas ici : elles vivent dans `../socle/extraction.py`, avec
leurs tests. En résumé — les dossiers qui ne fabriquent pas de loi sont
écartés, une saisine de commission le jour du dépôt n'est pas un examen, et
un texte se classe sur les actes de son jour le plus récent, pas sur l'étape
la plus avancée qu'il ait jamais atteinte. Détail dans
`../socle/README.md`.
