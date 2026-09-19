# Maquette — le fil des textes en cours

**Étape 1 du plan** (`../docs/PLAN.md`, §6). Un écran qu'on peut mettre entre
les mains de quelqu'un pour regarder s'il comprend.

Un seul fichier : **`feed.html`**. Il s'ouvre dans un navigateur, au format
téléphone.

**En ligne : <https://yesno584.github.io/AN-API/>** — le socle la publie
comme page d'accueil à chaque mise à jour des données. C'est la façon la plus
simple de la regarder depuis un téléphone, sans rien installer.

## Deux onglets, en bas de l'écran

**Textes** — les 2 150 textes qui peuvent devenir une loi, rangés par étape.
C'est l'onglet décrit ci-dessous, et il n'a pas changé.

**Travaux** — les **708 dossiers qui n'aboutissent à aucune loi** : commissions
d'enquête, missions et rapports d'information, résolutions, motions de censure,
pétitions, discours. Ils étaient écartés du fil ; **plus rien n'est écarté**.

Même machinerie de colonnes pour les deux, mais les colonnes ne disent pas la
même chose. Côté textes, une colonne est une **étape** — et l'ordre raconte un
parcours. Côté travaux, une colonne est une **catégorie** : ces dossiers ne
traversent rien, ils *sont* ce qu'ils sont. La frise du bas le reflète : elle
n'y allume aucune étape « déjà passée », parce qu'il n'y en a pas.

La recherche et les filtres ne s'affichent que sur l'onglet des textes : ils
portent sur des étapes et des chambres, qui n'ont pas de sens ici.

## Le calendrier

Un bouton en haut à droite de l'en-tête ouvre le calendrier : **2 323 séances,
commissions, décisions, votes et promulgations**, de juillet 2024 à septembre
2026. Une vue mois, les jours porteurs marqués d'un à trois points, la liste du
jour choisi en dessous. **Chaque ligne mène à la fiche de son texte.**

Une décision affiche son résultat quand un scrutin public a eu lieu :
« adopté — 187 pour, 0 contre, 0 abstention ».

**Ce qu'il ne peut pas montrer, et pourquoi.** Presque rien à venir. Mesuré le
2026-09-02 : **1 seule étape future** dans toute la base, **0 vote futur**, et
sur les 7 512 réunions de l'agenda de l'Assemblée, **35 sont à venir, dont une
seule nomme un texte**. La raison est simple : le Parlement est en vacances
jusqu'à l'ouverture de la session, et l'open data ne publie une réunion qu'une
fois convoquée. Le calendrier se remplira de lui-même à la rentrée — il n'y a
rien à corriger, mais il ne faut pas promettre un agenda prévisionnel.

## L'hémicycle

Le second bouton de l'en-tête, en forme d'arcs, ouvre la **composition de
l'Assemblée** : les 577 sièges dessinés en arcs, coloriés par groupe, de la
gauche à la droite, puis la liste des 12 groupes avec leur sigle, leur nom
complet et leur effectif. **Toucher un groupe ouvre la liste de ses députés** —
nom et circonscription, classés par nom. **Toucher les sièges d'un groupe dans
le dessin l'isole** : les autres s'effacent sans disparaître, et les retoucher
les rend.

**Ce qui est mesuré, et ce qui est dessiné.** L'effectif d'un groupe est un
compte de députés ; l'ordre des groupes est calculé sur les numéros de siège
publiés par l'Assemblée (voir `socle/README.md`). Mais **la place d'un siège
dans le dessin n'est pas une donnée** : l'open data ne dit pas où chaque
député s'assied. Les 12 rangées d'arcs, remplies de la gauche à la droite,
sont une convention — les proportions sont justes, le plan de salle ne l'est
pas. L'écran le dit lui-même au toucher du ⓘ, et `docs/CE-QUE-L-ON-ECRIT.md`
le classe ligne par ligne.

Le dessin ne charge rien de plus : il lit `groupes.json`, déjà chargé au
démarrage pour colorier les votes. La liste des députés d'un groupe, elle, est
un fichier à part (`groupes/<ref>.json`), lu seulement quand on ouvre le
groupe — 12 fichiers, 113 Ko en tout, dont aucun n'est chargé tant qu'on ne
demande rien.

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

Une application qui s'appelle « Qui vote quoi » doit montrer celles qui
sont allées au bout : la carte d'une loi promulguée porte son **numéro
officiel**, sa date et un lien vers le **Journal officiel**.

### La couleur du groupe de l'auteur

Chaque carte du fil porte le sigle du groupe de l'auteur, précédé d'un point
de sa couleur — 1 344 des 1 982 textes en cours. Un point plutôt qu'une
pastille pleine : **la couleur d'un groupe est une convention d'affichage**,
l'open data n'en publie aucune, et la donner en fond la ferait passer pour
une donnée.

Les autres textes n'affichent rien : un projet de loi déposé par le
Gouvernement, ou une proposition déposée par un sénateur, n'a pas de groupe à
l'Assemblée. C'est une absence réelle, pas une donnée manquante.

### Les filtres

Les puces suivent **le même ordre que le fil et que la frise** : arrêté en
chemin, les six étapes, la promulgation. Trois vues d'une même chose ne
peuvent pas s'ordonner de trois façons.

Le bandeau du haut reste collé en haut de l'écran, à hauteur constante :
mesuré, il partait avec le défilement et l'en-tête blanc venait prendre sa
place — ce qui donnait l'impression qu'il rétrécissait.

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

- pour une loi promulguée, **quand elle s'applique** — « S'applique depuis
  le … », « Ne s'applique pas encore en entier » — **au-dessus du titre** :
  c'est la première chose qu'on vient vérifier devant une loi ;
- le **titre** du texte, puis **l'étape où il se trouve** ou son issue ;
- la **description** du texte ;
- les **liens officiels** : dossier à l'Assemblée, dossier au Sénat, et le
  **texte de loi au Journal officiel** quand elle est promulguée ;
- son **auteur** — photo, nom, groupe en couleur — et ses **cosignataires** ;
- puis **les onglets** : le vote, les articles, ce que les groupes en ont dit,
  le parcours, les amendements.

### Les onglets du bas de fiche

**Vote** — le vote sur l'ensemble du texte, celui qui décide, **avec le détail
par groupe déjà affiché** : l'objet du scrutin, puis une barre par groupe.
C'est le premier onglet. **Articles** — ce que la loi change au droit, **en
entier ici** : les trois compteurs, les articles groupés par code, les
retouches de forme et ce que la loi ajoute. **Débats** — ce que les groupes en
ont dit en séance, chargé à la demande. **Parcours** — le parcours complet,
étape par étape, datée, **les votes intercalés à leur date** — voir la section
suivante. **Amendements** — chargés à la demande.

**Le vote sur l'ensemble ouvre la fiche quand il existe**, et il n'existe que
pour 71 textes sur 1 990 : les autres commencent par leurs articles ou leur
parcours, sans onglet vide. Il fallait deux gestes pour savoir qui avait voté
quoi — déplier, puis demander le détail ; c'est maintenant la première chose
qu'on voit. Les votes sur des amendements ou des articles, eux, restent dans
le parcours : un vote de détail ne se lit que dans son moment.

Des onglets plutôt que des dépliants empilés : ces rubriques ne se lisent pas
ensemble, et les 150 amendements d'un texte obligeaient à défiler à l'aveugle
pour savoir ce qu'il y avait plus bas. **Une rubrique sans contenu n'a pas
d'onglet** : un texte qui n'est pas encore une loi n'a pas d'onglet
« Articles », un texte dont personne n'a parlé en séance n'a pas le sien.
Chaque onglet garde le titre exact de sa rubrique, avec ses comptes —
« Parcours — 12 étapes, 3 votes ».

**La liste des articles est demandée à l'ouverture de son onglet**, pas à
celle de la fiche, et elle **ne porte aucun texte d'article** : c'est la raison
pour laquelle le socle la publie à part du texte de chaque article. Seul
l'onglet ouvert d'emblée demande ses données avec la fiche ; les paroles et les
amendements, eux, attendent leur bouton.

#### On passe d'un onglet à l'autre en glissant

**Les contenus sont posés côte à côte, comme les colonnes du fil** : on glisse
vers la gauche ou la droite, le contenu suit le doigt, et la page s'accroche
sur l'onglet d'arrivée. La barre suit le geste — l'onglet allumé change en
cours de route — et **le tour est sans fin** : après le dernier vient le
premier, par le même procédé que le fil (une copie du panneau d'en face posée
à chaque bout, et un saut invisible dès que le glissement s'immobilise
dessus). Toucher un onglet mène directement à son contenu.

**La barre tient sur une seule ligne et se fait glisser** quand les libellés
débordent — mesuré : cinq d'entre eux demandent 346 px quand un écran de
390 px en offre 358. L'onglet allumé est toujours ramené à l'écran, si bien
qu'on n'a jamais à le chercher.

**La bande prend la hauteur de l'onglet affiché**, et la recalcule dès que son
contenu bouge — une liste qui arrive, un dépliant qu'on ouvre. Sans cela elle
prendrait la hauteur du plus grand : « Vote » tient sur un écran et
« Amendements » sur cinquante, si bien que les autres onglets traîneraient un
vide derrière eux.

Toucher un onglet depuis le bas d'une longue liste remonte à la barre
d'onglets, sans déroulé — le même choix que pour les colonnes du fil.

#### La source reste sous les yeux

Sur une fiche — et sur les écrans qui la prolongent : la liste des articles
d'une loi, un article, le calendrier — **le bas de page se colle en bas de
l'écran**, à la place qu'occupe la frise sur le fil. D'où viennent ces données
et de quand elles datent se lisent donc sans descendre. **Sur le fil, rien ne
change** : le bas de page y reste en fin de page, avec ses trois paragraphes.

Le troisième — « Rien n'est écarté… » — ne s'affiche pas sur une fiche : il
décrit l'organisation du fil, ses onglets et ses colonnes, et n'a rien à dire
là. Les deux autres se resserrent : collé, ce bloc mangeait **152 px de haut
en 390 px de large et 191 px en 320 px**, soit près d'un quart de l'écran ;
resserré, il en fait 102 et 117. Les phrases, elles, ne changent pas. La
hauteur est **mesurée** à chaque ouverture, et réservée sous la fiche : rien
ne passe derrière le bloc.

### Les versions du texte, et ce que chaque étape en a fait

Un texte de loi n'est pas figé : il est déposé, la commission le réécrit, la
séance le réécrit encore. **Sous chaque étape qui produit une version, le
parcours porte une ligne** — « Texte de la commission · 3 articles modifiés » —
qui ouvre le texte de cette version.

Cet écran montre **le texte entier, article par article, superposé à la version
précédente** : ce qui a été retiré en rouge barré, ce qui a été ajouté en vert.
C'est le même calcul et le même dessin que pour les articles de loi — une
comparaison mot à mot avec la bibliothèque standard de Python, la ponctuation
descendue au caractère. La version déposée, elle, n'a rien à quoi se comparer :
elle s'affiche telle quelle, et le dit.

**À côté de chaque article, les amendements adoptés sur cet article** : leur
numéro, leur auteur, son groupe en couleur, et le lien vers l'amendement chez
l'Assemblée. Sur un téléphone il n'y a pas de place pour une colonne à côté du
texte — l'écran fait 30 rem au plus — donc ils se posent **au-dessus** de
l'article, et suivent son défilement.

**Ce que la page ne dit pas, et ne dira pas : quel mot vient de quel
amendement.** Il faudrait interpréter l'instruction de l'amendement (« à
l'alinéa 7, substituer aux mots… ») pour le deviner, c'est-à-dire fabriquer du
texte de loi. Le rapprochement se fait par le **numéro d'article**, et rien
d'autre. Mesuré le 2026-09-18 : **420 amendements adoptés sur 470 tombent sur
un article qui a réellement changé, 2 sur un article resté identique**. Il est
donc presque toujours juste — et souvent incomplet : 31 % des changements n'ont
aucun amendement adopté sur leur article, et **l'écran le dit** plutôt que de
laisser une place vide.

**Trois libellés sont de nous** : « Texte déposé », « Texte de la commission »,
« Texte adopté par l'Assemblée ». La source nomme le document « Proposition de
loi » à chaque étape, ce qui ne distinguerait pas les versions. Le reste — le
texte, les numéros d'article, les mentions « (nouveau) » et « (Supprimé) », les
amendements — est recopié.

**Ce que ça couvre**, et pourquoi une fiche peut n'avoir aucune ligne :
1 749 textes sur 2 219 ont au moins une version publiée par l'Assemblée, et
**249 en ont au moins deux**, donc une comparaison. Les autres sont nés au
Sénat, qui publie ses textes ailleurs. Et pendant les trois premiers jours qui
suivent une mise en service, la lecture n'est pas terminée : un texte dont la
version n'a pas encore été lue n'a simplement pas sa ligne. Détail des mesures
dans [`../docs/sources/textes-assemblee-html.md`](../docs/sources/textes-assemblee-html.md).

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

### Ce que la loi change au droit

Sur la carte d'une loi promulguée, deux choses que rien ne disait avant :

**Quand elle s'applique.** Une loi promulguée ne s'applique pas forcément tout
de suite, ni en une seule fois. La carte l'écrit — « Ne s'applique pas encore
en entier : 4 articles sur 7 entrent en vigueur le 1er septembre 2026 » — et
passe en rouge tant que quelque chose reste à venir. Les dates sont celles que
porte le texte officiel ; aucune n'est déduite.

**Combien d'articles elle touche**, avec un bouton vers le détail. Et quand
elle n'en touche aucun, la carte le dit aussi, plutôt que de rester muette :
« Ne modifie aucun article de loi existante — ce texte autorise la ratification
d'un traité. » La raison n'est donnée **que lorsque la donnée la porte** : elle
vient du type du dossier, pas d'une interprétation.

#### La liste des articles

Trois compteurs — modifiés, créés, abrogés — puis **un repli par code**. Chaque
article est une ligne avec **une barre qui montre la part du texte qui a
bougé**. C'est ce qui rend une loi de 574 articles parcourable : on va droit
aux gros changements au lieu de tout lire.

Elle s'affiche à deux endroits, **écrite une seule fois** : dans l'onglet
« Articles » de la fiche, et sur son propre écran (`#/change/<identifiant>`),
où mène le bouton de la carte du fil. Deux copies auraient divergé au premier
changement.

#### La fiche d'un article

Le texte **entier**, jamais tronqué, avec trois façons de le lire : *Ce qui
change* (les retraits barrés en rouge, les ajouts en vert), *Texte en vigueur*,
*Texte précédent*. Puis les conditions d'entrée en vigueur si le texte officiel
en porte, et le lien vers Légifrance.

**Une retouche de typographie se montre une seule fois.** Une part des
différences signalées n'est que de la forme : une virgule déplacée, une espace
restituée, un tiret. Mesuré : **13,6 % des morceaux signalés**.

Les effacer donnerait un texte de loi faux. Les afficher comme le reste —
l'ancien barré, puis le nouveau — oblige à lire le mot deux fois pour trouver
l'espace. On descend donc **au caractère**, et le mot s'écrit une fois :

| Le texte devient | Ce qui s'affiche |
|---|---|
| « I-Sont » → « I- Sont » | `I-`[espace en **bleu**]`Sont` |
| « 222-33 » → « 22233 » | `222`[tiret barré en **gris**]`33` |
| « Etat-membre » → « Etat membre » | `Etat`[tiret **gris**][espace **bleue**]`membre` |

| | |
|---|---|
| rouge barré | retiré par la loi |
| vert | ajouté par la loi |
| **bleu** | **ponctuation ou espace ajoutée** |
| **gris barré** | **ponctuation ou espace retirée** |

Les vrais changements restent mot à mot : « trois » devenu « cinq » se lit
comme un mot remplacé, pas comme quatre lettres. La légende n'affiche que les
couleurs réellement présentes dans l'article.

**Et un article dont *tout* le changement est de cette nature ne compte pas
comme modifié.** Il serait faux d'annoncer qu'une loi a changé quelque chose là
où elle n'a rien changé. Ces articles — 5 sur 4 431 — sont rangés en bas de
l'écran, dans un bloc replié : consultables, mais hors du compte.

**Rien n'est rédigé par une IA.** Les textes sont ceux du Journal officiel, et
la comparaison est un calcul mot à mot — la même bibliothèque standard que
partout ailleurs dans ce projet.

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

### Ce que les groupes en ont dit

Dans l'onglet « Débats », **les prises de parole en séance, recopiées mot
pour mot** du compte rendu de l'Assemblée : nom de l'orateur, son groupe du
jour du débat, la date, la section. 3 384 prises de parole sur 172 textes de
loi. L'onglet vient juste après les articles ; le vote sur l'ensemble a le
sien, le premier de la barre.

**Rien n'est résumé et rien n'est relié au vote.** La page ne dit pas « ce
groupe a voté ainsi parce que » : elle montre ce qui a été dit, et le vote est
dans l'onglet d'à côté. C'est un choix, pas une limite technique — le 25 février 2026,
l'UDR a voté *pour* les soins palliatifs pendant que son orateur disait
« l'ensemble du groupe UDR votera contre », parce qu'il parlait de l'autre
texte de la même séance.

**Une pastille par groupe, en haut**, dans l'ordre de l'hémicycle, avec le
nombre de paroles. La toucher ne montre que ce groupe ; la retoucher les
remontre tous.

**Les paroles sont repliées, pas coupées.** Une prise de parole fait 4 260
caractères en médiane : elle s'affiche sur quatre lignes, et « Lire la suite »
déroule le reste. Le texte entier est dans la page dès le premier affichage —
rien n'est allé chercher un complément, rien n'a été tronqué à la publication.

**Le fichier est chargé à la demande** — 54 Ko en médiane, 300 Ko pour le
PLFSS. La fiche s'ouvre sans l'attendre.

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
