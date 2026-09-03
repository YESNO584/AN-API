# Session learnings

Append-only log of things learned while working on this project that aren't
derivable from the code, and that would otherwise be rediscovered at cost.
Loaded every session via the root `CLAUDE.md`.

## How to use this file

- **Newest entries at the top**, under a dated `##` heading.
- One bullet per lesson. State the fact, then *why it matters*. Name the file,
  class or flag so it can be verified later.
- If a lesson belongs to one subsystem, put it in that subsystem's own
  `CLAUDE.md` instead and only cross-reference here. This file is for
  cross-cutting or process lessons.
- If a lesson turns out to be wrong, **delete or correct it** — a stale
  learning is worse than none.
- Durable facts about *the user's* preferences go in the auto-memory, not
  here.

---

## 2026-09-03 — Mesuré sur le socle entier : ce que la passe complète a appris

- **417 articles propres pour 2 767 changés**, sur 56 lois (socle du
  2025-07-13 plus deux quotidiennes ; la production en couvre davantage parce
  qu'elle lit aussi les 419 quotidiennes). La loi de finances pour 2025 en
  compte 146. La loi de fin de gestion 2024 — celle qui a fait découvrir le
  manque — passe de 2 articles à **2 changés et 6 propres, soit 8 134 mots**
  de texte de loi qui n'apparaissaient nulle part.
- **La rédaction « d'avant » n'est pas figée, et le pourcentage de changement
  bouge avec elle.** Sur une seule quotidienne, **2 965 rédactions sur 4 498
  étaient closes avant la date du socle** — une rédaction de la loi n° 78-17
  datée de 1980, un décret de 1969. La source corrige donc en permanence des
  rédactions anciennes. Conséquence constatée : l'article 156 de la loi de
  finances 2024 donne **76 %** de texte commun avec l'instantané de juillet
  2025 seul (l'en-tête du tableau des plafonds manquait à la rédaction d'avant)
  et **100 %** avec les quotidiennes qui l'ont corrigée. *La leçon :* un
  pourcentage d'avant/après mesuré sur une base partielle ne se compare pas à
  celui du site, et ce n'est pas un bug — c'est pourquoi la publication lit le
  socle *et* toutes les quotidiennes.
- **Ne pas conclure à une régression de vitesse sans savoir ce que le chiffre
  contient.** La passe s'est affichée en **29,6 min** contre 15,7 min
  documentées, et j'ai commencé à chercher le coût dans mon code. Le chronomètre
  de `recuperer_legi.py` englobe le **téléchargement** : 15 min de réseau plus
  **14,6 min de lecture**, soit un peu moins qu'avant. Le test de sous-chaîne
  que j'allais ajouter pour « réparer » cela valait 40 s sur 15 min, mesuré —
  0,4 %. Il n'a pas été ajouté.
- **Six rédactions sur 5 091 n'ont aucun numéro**, et ce sont exactement les
  états et annexes des lois de finances et de financement de la sécurité
  sociale — dont l'état A de la loi de fin de gestion, le tableau des recettes.
  L'écran affichait « Article » suivi de rien. On montre à la place le début de
  leur propre texte, coupé à un mot entier, en disant que c'est un début de
  texte et non un intitulé. *Pourquoi ne pas deviner où le titre s'arrête :* la
  source l'écrit en capitales, mais « (En euros.) » et « Voies et moyens »
  cassent la règle dès le deuxième exemple.
- **Le défaut « 0 % du texte a changé » est toujours là, et se voit maintenant
  à côté du correctif.** Sur la fiche de la fin de gestion 2024, l'article 46
  de la loi 2005-1719 affiche « 0 % du texte a changé » pour 50,7 millions
  d'euros de TVA en moins. Il a été laissé hors de ce lot exprès, un changement
  à la fois — mais c'est le prochain.

---

## 2026-09-03 — Ce qu'une loi ajoute, écrit : trois règles, dont deux trouvées en vérifiant

Mise en œuvre du constat de l'entrée suivante. Ce qui compte ici n'est pas le
code — il fait une centaine de lignes — mais **l'ordre dans lequel les règles
se sont révélées fausses**. Les deux tiers de ce qui suit ont été trouvés en
vérifiant sur les vraies données une règle que je croyais bonne.

- **La règle publiée d'abord était fausse deux fois, et les deux erreurs
  n'étaient visibles que sur les données.** Version 1 : « le `TYPE` de la
  source dit lesquels montrer ». Elle laissait passer 8 articles sur 87 qui
  n'affichaient qu'une liste de références — un `PARTIELLEMENT_MODIF` peut
  n'être fait que de renvois. Version 2 : « le `TYPE`, plus un test sur le
  texte ». Elle **perdait du droit réel** : l'article 32 de la loi 2026-201 est
  annoncé `ENTIEREMENT_MODIF` et 92 % de son contenu est une servitude au
  profit des jeux Olympiques d'hiver. Version 3, celle qui tient : **le texte
  seul décide**, le `TYPE` n'est plus qu'un renseignement. *La leçon :* une
  étiquette que la source pose sur son propre contenu se trompe dans les deux
  sens, et rien ne le montre avant de l'avoir confrontée au contenu.
- **Un renvoi se reconnaît à la structure, pas aux mots.** Ma première
  détection était ancrée au début de la chaîne ; or la source écrit « I. A
  modifié les dispositions suivantes », « I. à V. - A modifié… ». La forme
  stable est ailleurs : **un `<p>` d'annonce suivi d'un `<blockquote>`** qui
  porte la liste des articles visés. `legi.sans_les_renvois` retire les
  `<blockquote>` du plus imbriqué vers l'extérieur, puis les paragraphes
  d'annonce. Contrôle de non-régression : les **321 articles de fond**
  rencontrés ressortent **intacts au caractère près**.
- **Le garde-fou qui évite d'attribuer un article au mauvais texte : « pas de
  rédaction d'avant ».** Toutes les rédactions d'un article nomment le même
  porteur. Sans ce test, l'article 156 de la loi de finances 2024 *tel que la
  loi de fin de gestion l'a modifié* passait pour un article que la loi de
  finances avait écrit. Un article de loi compte jusqu'à **six rédactions
  successives** (article 31 de la loi n° 78-17).
- **Et ce garde-fou a révélé un vrai bug, vieux, dans `version_precedente` :
  un article se donnait pour son propre « avant ».** Un article dont l'entrée
  en vigueur n'est pas fixée porte la sentinelle `2999-01-01` en début **et**
  en fin, et figure dans sa propre liste de versions : « celle qui finit quand
  la nôtre commence » le désignait lui-même. **61 des 130 articles** des lois
  d'août 2026. Bénin jusqu'ici — la rédaction était déjà en base — mais il
  rendait le nouveau test inutilisable. *La leçon :* une règle nouvelle
  s'appuie sur les anciennes, et c'est ce qui fait sortir leurs angles morts.
- **Une donnée dérivée ne se verse pas dans un chiffre déjà publié.** `total`,
  `actions` et `dates` disent depuis toujours « ce qu'elle change dans le droit
  d'avant ». Les ajouts ont leur propre compteur (`ajouts`) et leur propre
  liste (`articlesAjoutes`). Y verser des articles neufs aurait changé le sens
  d'un chiffre que l'écran affiche déjà, sans que rien ne le signale.
- **Le tri avant la lecture, sur 2,5 millions de fichiers.** `lire_article`
  déplie tout le texte ; l'appeler pour chaque fichier de l'archive coûterait
  des minutes. Le test d'appartenance (`loi_qui_porte`, une regex sur
  `CONTEXTE`) vient donc avant, et `lire_article` après. C'est la seule raison
  pour laquelle le test « est-ce un ajout » n'est pas au même endroit que
  l'autre : il a besoin de `precedent`.
- **Trois défauts d'accent trouvés en regardant l'écran, pas le code.**
  « les 1 article qu'elle change » (déjà là avant), « les 28 qu'elle ajoute »
  sans le nom, et trois tuiles à zéro pour une loi qui n'amende rien. Aucun
  n'apparaît dans un test ; tous les trois sautent aux yeux sur une capture.
  D'où `combienDArticles`, qui fait l'accord une fois pour toutes.
- **Une maquette se vérifie dans un navigateur, et ça tient en deux
  commandes.** `python3 -m http.server --directory socle/public`, puis
  Playwright sur le Chromium déjà installé
  (`/opt/pw-browsers/chromium-1194/chrome-linux/chrome`, le paquet Python
  s'installe avec `pip install playwright` — ne pas lancer
  `playwright install`). Cela a confirmé le libellé, les tuiles, la pastille,
  l'absence de bascule avant/après, le thème sombre, et l'absence d'erreur JS.
  **Un `404 /favicon.ico` apparaît en console : il est antérieur et sans
  rapport** — la page ne déclare aucune icône.
- **Fabriquer le décor manquant vaut mieux que d'attendre les données.** Le cas
  « la loi n'amende rien mais écrit ses propres articles » — celui de la loi de
  finances — n'était pas dans la base partielle. Une copie des fichiers publiés
  dans le bac à sable, deux champs mis à zéro, et le chemin d'affichage était
  vérifié sans attendre la passe de 16 minutes.

---

## 2026-09-03 — Les articles propres d'une loi sont dans LEGI, et on les rate

Correction d'une conclusion écrite plus tôt le même jour. L'utilisateur a
contesté « une loi de fin de gestion ne change presque rien » : ses articles
sont nouveaux, donc ils ajoutent du droit. **Il avait raison, et la source les
publie.** Mesuré sur deux archives quotidiennes de LEGI (12,7 et 6,3 Mo, donc
sans la passe de 16 minutes sur le socle).

- **Les articles propres d'une loi sont bien dans LEGI**, sous
  `code_et_TNC_en_vigueur/TNC_en_vigueur/JORF/TEXT/<JORFTEXT…>/article/…`, avec
  leur texte. `legi.parcourir_archive` les lit déjà : le filtre `/article/` les
  attrape. Ce ne sont pas des données manquantes.
- **Chaque article nomme sa propre loi, dans son propre XML** :
  `<TEXTE … nature="LOI" num="2026-796" nor="AGRS2603566L" cid="JORFTEXT…">`,
  dans `CONTEXTE`. C'est la clé qui manque à `legi.py`, et elle est directe —
  aucun rapprochement par titre.
- **Pourquoi on les rate.** `legi.changements()` ne garde qu'un lien
  `sens="cible"` dont le `typelien` est un **verbe** (`MODIFIE`, `CREE`, …)
  *et* qui porte un `numtexte`. Un article de loi n'en porte jamais : rien n'a
  agi sur lui. Ce qu'il porte, c'est la forme **nominale** — `MODIFICATION`,
  `CREATION`, `ABROGATION` — avec un `numtexte` **vide**, qui dit ce que *lui*
  fait aux autres. Les deux vocabulaires sont les deux bouts du même lien : le
  verbe est sur la cible, le nom est sur la source.
- **Chiffres.** 642 articles hors code dans les deux quotidiennes : **0** porte
  un lien de changement venant de sa propre loi. Et sur les 5 880 articles
  publiés pour les 72 lois suivies, **0** est un article de la loi elle-même.
  Ce n'est pas un cas limite, c'est systématique.
- **Ce n'est pas la source qui manque, et c'est vérifiable d'un coup d'œil.**
  La loi 2026-798 affiche 208 articles changés chez nous et a **138 de ses
  propres articles** dans ces deux archives ; la loi 2026-796, 95 affichés et
  **61** présents.
- **`TYPE` dit lesquels valent d'être montrés, et c'est mesuré.** Sur 667
  articles de loi :

  | `TYPE` | Part | Contenu |
  |---|---:|---|
  | `AUTONOME` | 48 % | du texte lisible (89 % d'entre eux) |
  | `ENTIEREMENT_MODIF` | 36 % | « A modifié les dispositions suivantes : – Code rural… » — rien à lire |
  | `PARTIELLEMENT_MODIF` | 16 % | du texte lisible (88 %) |

  *Pourquoi ça compte :* montrer les `ENTIEREMENT_MODIF` ferait doublon — leur
  substance est déjà à l'écran, sous forme des articles de code modifiés — et
  n'afficherait qu'une phrase de renvoi. Le filtre à écrire est `TYPE`, pas
  une heuristique sur le texte.
- **Deux pièges pour la suite.** Un article tout neuf peut porter
  « **en cours de traitement** » au lieu de son texte : 69 des 138 articles de
  la loi 2026-798, promulguée la veille. Et le même article a **deux
  rédactions**, l'une côté JORF (`DATE_DEBUT` = `2999-01-01`) et l'autre côté
  LEGI (la vraie date) — les deux `TITRE_TXT` du `CONTEXTE` le montrent. Les
  afficher toutes les deux ferait un doublon.
- **Les quotidiennes suffisent à trancher une question sur LEGI.** 419
  quotidiennes au dépôt, de 5,3 Ko à 12,7 Mo, couvrant environ un an et deux
  mois. Toute cette mesure a tenu en deux téléchargements. *La leçon :* avant
  de renoncer à vérifier une règle du droit consolidé parce que « le socle fait
  1,1 Go », regarder si une quotidienne répond.

---

## 2026-09-03 — Deux chiffres d'une même fiche ne comptent pas la même chose

Enquête sur la loi de finances de fin de gestion pour 2024 (loi 2024-1167,
dossier `DLR5L17N50838`) : « beaucoup d'amendements adoptés, mais 2 articles
changés, avec quasiment pas de diff ». Aucun bug dans le socle ; **un défaut
d'affichage dans la maquette**, et deux faits de droit à ne pas redécouvrir.

- **Un amendement adopté peut être annulé par le rejet du texte entier, et
  c'est fréquent en loi de finances.** Le 2024-11-19 l'Assemblée a rejeté la
  **première partie** du texte (53 pour, 146 contre), ce qui met fin à son
  examen : les 15 amendements adoptés ce jour-là tombent avec elle. La loi
  promulguée est le texte de la CMP. *Preuve chiffrée :* l'amendement adopté
  n° 12 portait la fraction de TVA de l'audiovisuel public de
  « 3 976 056 557 » à « 3 981 056 557 » ; la loi promulguée écrit
  « 3 976 056 557 », le montant du gouvernement. *Pourquoi ça compte :* la
  fiche affiche les amendements adoptés en tête de liste sans dire qu'ils
  n'ont rien changé — c'est la première cause de l'étonnement, et rien à
  l'écran ne la signale.
- **Une loi de fin de gestion ne change presque rien au droit existant, par
  construction.** Sa substance est dans ses propres articles — article
  liminaire, crédits, états A, B et C — qui ne modifient aucun article
  préexistant. Seules ses dispositions de plafonds de taxes affectées le font :
  ici l'article 156 de la loi 2023-1322 (AFITF 2 044 150 000 → 1 650 811 986,
  VNF 136 500 → 145 600) et l'article 46 de la loi 2005-1719 (audiovisuel
  4 026 728 396 → 3 976 056 557). Mesures de contrôle : fin de gestion 2025 →
  4 articles, lois spéciales (2024-1188, 2025-1316) → 0, loi de finances pour
  2025 → 1 053. **Le chiffre est juste** ; c'est l'attente qui est fausse.
- **Le socle ne voit pas les articles propres à une loi.** Un changement se lit
  dans un lien `sens="cible"` porté par l'article *visé* ; les articles qu'une
  loi crée pour elle-même n'en portent pas. Vérifié : sur les 231 `CREE` de la
  loi de finances pour 2025, **aucun** n'appartient à la loi 2025-127 elle-même.
  **Correction du 2026-09-03 :** j'avais ajouté « et ne peut pas », et c'était
  faux — voir l'entrée du 2026-09-03 ci-dessus. La source les publie, avec leur
  texte, et l'article nomme sa propre loi. C'est bien un trou à combler.
- **Le défaut, lui : « 0 % du texte a changé » sur un vrai changement.**
  `feed.html:2542` affiche `100 - a.commun`, et `legi.part_commune` arrondit.
  Huit mots changés sur 5 377 donnent 99,85 % → 100 % → « 0 % ». Sur un texte
  budgétaire, ces huit mots *sont* la loi. **441 articles sur 4 426 (10 %)**
  sont dans ce cas, dont 103 pour la seule loi de finances pour 2025. La
  barre de jauge dit la même chose : `Math.max(2, 0)`, soit 2 % de largeur.
  *La piste :* dire les mots changés plutôt qu'un pourcentage quand celui-ci
  arrondit à zéro — le compte est déjà publié.
- **`publier.py:177` écarte les amendements sans dispositif, et l'écran n'en
  dit rien.** 227 amendements, 76 publiés : les 151 autres n'ont pas de
  dispositif dans la source parce qu'ils n'ont jamais été publiés —
  58 « (sans suite) », 24 « Crédits », 14 « Charge », 5 doublons, 8 retirés
  avant publication. « Crédits » et « Charge » sont des **motifs
  d'irrecevabilité** (article 40), pas des catégories : 42 amendements
  irrecevables se lisent comme s'ils avaient un sort neutre. Le filtre est
  bon ; le message « 76 affichés sur 227 » laisse croire à un plafond alors
  que c'est la source qui est vide. Et il coûte **2 adoptés sur 15**.
- **La maquette ne montre jamais `sorts`**, que `publier.py` publie pourtant
  par texte. C'est le seul endroit où le compte réel des adoptés, rejetés et
  irrecevables serait lisible d'un coup d'œil.
- **Les fichiers déjà publiés remplacent une passe de 16 minutes.**
  `https://yesno584.github.io/AN-API/changements/<uid>.json` répond en une
  seconde et porte le résultat de `legi.db`. Toute l'enquête a tenu sans
  reconstruire le droit consolidé — vérifier `etat.json` (`genereLe`,
  `droitConsolideIndisponible`) avant de lancer un téléchargement de 1,1 Go.

---

## 2026-09-02 — Les argumentaires, écrits : recopiés, jamais reliés au vote

- **La décision qui a tout simplifié : ne pas relier la parole au vote.** La
  mesure de la veille cherchait à afficher « pourquoi ce groupe a voté ainsi »,
  et son risque principal était une contrevérité à l'écran. En affichant les
  prises de parole **sans prétendre qu'elles expliquent un vote**, ce risque
  disparaît entièrement — et la fenêtre d'attribution, qui était tout le
  problème, redevient un simple choix de sections. *La leçon :* quand une
  fonctionnalité ne tient qu'à une inférence risquée, retirer l'inférence peut
  la rendre à la fois plus juste et plus simple.
- **Le compte rendu cite le numéro de dépôt du texte, pas son dossier.** Il est
  dans l'attribut `valeur` du titre de section : `" (n[[o]] 2406)"`, ou
  `" (n[[os]] 2406, 2401)"` quand deux textes sont discutés ensemble. La clé
  (date, votants, pour, contre) mesurée la veille n'a pas servi : le numéro est
  plus direct et rattache à un **texte**, ce qu'on voulait, plutôt qu'à un vote.
- **Un numéro de dépôt ne suffit pas seul : il faut la date de séance.**
  « n° 698 » désigne quatre documents de l'archive — une proposition de
  l'Assemblée, son rapport, et deux propositions du Sénat. Filtrer sur les
  documents de l'Assemblée (`uid` contenant `ANR5L17`) laisse encore 97 numéros
  sur 693 pointant vers deux à quatre dossiers ; **départager par la date de
  séance en lève la totalité** — un dossier discuté ce jour-là a forcément une
  étape datée de ce jour-là. Résultat : 614 numéros sur 693 rattachés,
  **0 ambigu**, 79 appartenant à la 16e législature.
- **Chercher un renseignement au mauvais endroit donne un chiffre bas qui a
  l'air d'un fait.** Le sigle du groupe est imprimé après le nom de l'orateur
  (« M. Éric Martineau (Dem) »), mais seulement quand la présidence vient de
  lui donner la parole. Le chercher dans les seules sections publiées donnait
  85,7 % d'attribution ; le chercher dans **toute** la séance donne 95,6 %.
  M. Stéphane Lenormand parle 49 fois sans sigle, et ses 8 mentions « (LIOT) »
  sont toutes ailleurs. *La leçon :* avant de conclure « la source ne le dit
  pas », vérifier qu'on a lu toute la source.
- **La même parenthèse ne veut pas toujours dire la même chose.** Elle porte le
  sigle du groupe, mais aussi le département quand deux députés sont homonymes.
  Sans confronter le contenu à la liste des groupes, trois orateurs se
  retrouvaient dans un groupe « Alpes-Maritimes ».
- **Le XML des comptes rendus est plat, pas imbriqué.** Les `<point>` se
  suivent tous au même niveau sous `<contenu>` ; c'est l'attribut `nivpoint`
  qui donne la hiérarchie. Un parcours récursif ne trouve donc rien, et un
  découpage par section se fait à l'état, pas à la structure.
- **Une mesure sur des paragraphes ne se transpose pas à des prises de
  parole.** Le taux d'attribution du groupe passait de 94,6 % (par paragraphe)
  à 85,7 % (par prise de parole recollée) sans qu'aucune règle ait changé :
  les orateurs sans groupe — ministres, rapporteurs — parlent en interventions
  courtes, et pèsent donc plus une fois les paragraphes regroupés. *La
  leçon :* quand un chiffre bouge après un changement de découpage, le
  dénominateur a changé avant le code.
- **Un test peut échouer parce que son décor est trop pauvre.** Le test du
  rattrapage de sigle échouait : mon `<orateur>` de fabrication n'avait pas de
  `<id>`, alors que tous ceux de l'archive en ont un. C'est le décor qui était
  faux, pas la règle. *Même famille que les trois échecs déjà notés dans
  `CLAUDE.md` :* quand l'outil et le code se contredisent, chercher lequel des
  deux a tort.

---

## 2026-09-02 — Les arguments des groupes sont dans les débats, et rattachables

- **Les comptes rendus de séance se rattachent à nos votes à 97 %**, sans
  numéro de scrutin — le compte rendu n'en cite aucun (vérifié : 0 mention de
  « scrutin public n° X » dans les 601 fichiers). La clé qui marche est
  **(date de séance, votants, pour, contre)** : 8 206 des 8 434 scrutins de la
  base retrouvés, 13 blocs de résultat sans correspondance, et 154 clés sur
  8 252 partagées par plusieurs votes (le numéro d'amendement, porté par
  l'attribut `adt` du `point`, les départage). *Pourquoi ça compte :* c'est ce
  qui rend possible d'afficher, sous un vote, ce que chaque groupe a dit.
- **L'archive des débats est `vp/syceronbrut/syseron.xml.zip`** (55,8 Mo,
  601 séances), et non `vp/syseron/…` : les trois chemins devinés renvoient
  404, l'adresse se lit sur la page `travaux-parlementaires/debats`.
- **Chaque prise de parole porte `id_acteur` (`PA…`)**, ce qui donne le groupe
  par jointure sur notre table `acteur`. Attention : `acteur.groupe_ref` est le
  groupe **d'aujourd'hui**, pas celui du jour du débat, et seuls 577 acteurs
  sur 1 066 en ont un.
- **Le séparateur des chiffres d'un résultat de scrutin est l'espace
  insécable `\xa0`**, pas l'espace. Un découpage sur `\s{2,}` renvoie donc
  zéro résultat sans rien signaler — c'est ce qui a fait échouer la première
  mesure. *La leçon :* un compteur à zéro se vérifie sur un exemple imprimé.
- **La fenêtre d'attribution est tout le problème, et elle se mesure.** Les
  paroles retenues autour d'un vote décident de la justesse de ce qu'on
  affiche. Mesuré sur les annonces explicites d'intention (« nous voterons
  pour »), comparées au vote réellement émis :

  | Fenêtre | Groupes par vote sur l'ensemble | Annonce conforme au vote |
  |---|---:|---:|
  | Tout depuis le scrutin précédent | 8 | 77 % |
  | Le seul point de l'ordre du jour | 0 (64 % vides) | 81 % |
  | Toute la section du texte | 11 | 59 % |
  | **« Explications de vote » + « Discussion générale »** | **10** | **94,5 %** |

  *Pourquoi ça compte :* la bonne fenêtre n'est pas la plus large ni la plus
  étroite, c'est la **section nommée** du compte rendu — l'Assemblée y donne
  la parole à un orateur par groupe, sur le vote final et rien d'autre.
- **Une erreur type, lue à la main :** le 2026-02-25, l'UDR a voté *pour* les
  soins palliatifs (17-0) alors que son orateur disait « l'ensemble du groupe
  UDR votera contre » — il parlait de l'aide à mourir, l'autre texte de la même
  séance. *La leçon :* une phrase d'intention prise dans la mauvaise section
  produit une contrevérité à l'écran, et c'est le risque principal de cette
  fonctionnalité.
- **Les exposés sommaires ne suffisent pas** pour cette fonctionnalité :
  90 337 amendements en portent un, mais il n'explique que la position de leur
  **auteur**. Sur les 101 208 couples (vote, groupe) de la base, seuls **2 061
  (2 %)** recevraient un argument par cette voie.
- **Les scripts de mesure sont dans le scratchpad de la session**
  (`mesure.py` … `mesure8.py`), pas versionnés. L'agent
  `feature-data-coverage-prober` a été écrit pour refaire ce genre de mesure
  sans redécouvrir la méthode.

## 2026-08-31 — La maquette en colonnes

### La maquette se vérifie dans un vrai navigateur, sans réseau

- **Chromium et Playwright sont installés dans la session** : `playwright` est
  un module global (`NODE_PATH=/opt/node22/lib/node_modules`), les navigateurs
  sont dans `/opt/pw-browsers`. *Pourquoi ça compte :* une modification
  d'affichage de `maquette/feed.html` peut être **mesurée** (largeurs,
  positions, défilement, erreurs JS) au lieu d'être supposée d'après le diff.
- **Le socle se remplace par un faux socle local.** La page lit ses données à
  côté d'elle par une adresse relative : il suffit d'écrire des `textes.json`,
  `promulgues.json`, `arretes.json`, `etat.json`, `groupes.json` inventés dans
  un dossier, d'y copier `feed.html`, et de servir le tout avec
  `python3 -m http.server`. Les portails bloqués ne gênent donc en rien le
  travail sur l'affichage.
- **Deux pièges de cette mise en place**, tous deux rencontrés : les variables
  de proxy doivent être vidées pour que `127.0.0.1` soit joignable ; et
  `page.setContent()` ne marche pas ici — sans adresse de base, les `fetch`
  relatifs de la page ne mènent nulle part. Il faut vraiment servir la page
  (`page.goto`).
- L'agent `static-page-layout-verifier` a été écrit pour refaire tout ça sans
  le redécouvrir.

### `hidden` ne résiste pas à `display: flex`

- Passer `main#fil` en `display: flex` casse, en silence, le masquage du fil
  quand une fiche s'ouvre (`$("fil").hidden = true`) : la règle du navigateur
  pour `[hidden]` est `display: none`, mais une règle d'auteur l'emporte. D'où
  `main#fil[hidden] { display: none; }` dans la feuille de style. *Pourquoi ça
  compte :* le symptôme est le fil qui reste visible sous la fiche, et rien
  dans la console ne le signale.

### Un défaut d'affichage constaté n'est pas forcément le sien

- Le panneau des filtres s'affiche de travers : les titres de rubrique à
  gauche, les puces poussées à droite. Ce n'est **pas** dû au passage en
  colonnes — la même capture prise sur `git show HEAD:maquette/feed.html` est
  identique. La cause est une **collision de classe CSS dans `feed.html` :
  `.groupe` désigne à la fois une rubrique du panneau des filtres et une ligne
  de groupe politique dans le détail d'un vote**, et la seconde règle
  (`display: flex; align-items: center`) écrase la première. Pas corrigé :
  hors du sujet demandé. *La leçon de méthode :* rendre l'ancienne version et
  comparer, avant d'attribuer un défaut à sa propre modification.

## 2026-08-31 — Initialisation du dépôt, plan v1 et v2

### Le blocage réseau vient de la session, pas de l'utilisateur

- **Les portails parlementaires et gouvernementaux sont refusés par le proxy
  de la session**, pas par le réseau de l'utilisateur : `CONNECT tunnel
  failed, response 403` sur `data.assemblee-nationale.fr`, `data.senat.fr`,
  `senat.fr`, `legifrance.gouv.fr`, `data.gouv.fr`,
  `assemblee-nationale.fr`, `lafabriquedelaloi.fr`, `regardscitoyens.org`.
  Retesté le 2026-08-31, inchangé. *Pourquoi ça compte :* ne pas faire
  chercher une panne de connexion à l'utilisateur, et ne pas retenter à
  chaque session sans le dire.
- **Comment le vérifier en une commande :** `curl -sS
  "$HTTPS_PROXY/__agentproxy/status"` — le champ `recentRelayFailures`
  nomme chaque hôte refusé. Plus fiable que d'interpréter un code d'erreur
  `curl`.
- **Ça se corrige**, et ce n'est pas une fatalité : le niveau d'accès réseau
  de l'environnement se règle sur `Custom` avec une liste de domaines. La
  marche à suivre complète est dans `docs/ACCES-RESEAU.md`. À faire une
  fois, pas à rediagnostiquer à chaque session.
- **Ce qui marche quand même :** `WebSearch`. Ne marchent pas : `curl`,
  `WebFetch` (qui répond `EGRESS_BLOCKED`). L'accès GitHub est limité au
  seul dépôt de la session ; l'API GitHub répond 403 sur tout autre dépôt.
  *Conséquence :* on peut enquêter sur une source, jamais ouvrir ses
  fichiers. Toute affirmation sur un format ou une taille de fichier reste
  non vérifiée tant que quelqu'un n'a pas regardé depuis un poste normal.

### Un `git status` vide ne veut pas dire « rien n'a été fait »

- Après une reprise de session (contexte résumé), `git status --short` n'a
  rien renvoyé. Interprétation naturelle : les fichiers n'ont pas été
  créés. Interprétation correcte : **tout était déjà commité et poussé** par
  la partie résumée de la session. `git log --oneline` l'a montré en une
  seconde. *La règle du `CLAUDE.md` s'applique exactement ici :* la sortie
  d'un outil est une piste, pas un fait. Avant de conclure qu'un travail
  n'a pas eu lieu, regarder `git log` et `git ls-files`, pas seulement
  l'état de la copie de travail.

### Tester un hook : vérifier la charge d'entrée, pas seulement le code de sortie

- `statusline.sh` a affiché `.` comme nom de projet pendant un test. Réflexe
  possible : corriger le script. En réalité **le script lit le champ `.cwd`
  et le test lui envoyait `.workspace.current_dir`** — le script était bon,
  le test était faux. *Pourquoi ça compte :* c'est exactement le troisième
  échec-type listé dans `CLAUDE.md` (« quand un outil et le code ne sont pas
  d'accord, chercher lequel des deux a tort »), rencontré en vrai.
- Les trois hooks ont été vérifiés un par un et fonctionnent : rappel de
  reformulation, ligne d'état, et blocage d'écriture hors du dossier
  (sortie 2). `jq` est bien présent, c'est leur seule dépendance.

### Les tarifs de l'API Claude se vérifient, ils ne se recopient pas

- Le plan cite les prix par million de jetons. Ils ont été **vérifiés via la
  compétence `claude-api`** avant réécriture, et étaient exacts (Opus 5 :
  5 $ / 25 $ ; Sonnet 5 : 2 $ / 10 $ ; Haiku 4.5 : 1 $ / 5 $ ; remise de
  50 % en traitement par lots). *Pourquoi ça compte :* ces prix changent, et
  les recopier de mémoire d'une version du document à la suivante est le
  moyen le plus simple d'y laisser un chiffre faux pendant des mois.

### Ce qui reste faux dans la configuration du dépôt

- **`.claude/code_rules.json` est toujours le modèle générique C#**, avec
  `include_globs` à `**/*.cs` et tous les champs `evidence` vides. Le
  vérificateur tourne sans erreur et annonce « 0 problème » — sur un dépôt
  qui ne contient aucun fichier `.cs`. **Un rapport propre ne prouve donc
  rien aujourd'hui.** À régénérer avec l'agent `code-convention-miner` dans
  la session qui écrira le premier code.
- La section « Architecture » du `CLAUDE.md` et la définition trop large de
  « produit source » sont à remplacer dans cette même session.

### Connaissances produit

Elles ne sont pas ici : elles sont dans `docs/PLAN.md`, qui est le document
vivant du projet. Point le plus utile à connaître avant d'y entrer : **La
Fabrique de la Loi (Regards Citoyens) suit déjà un texte à travers les deux
chambres et publie ses données** — vérifier s'il est à jour est la première
chose à faire, avant toute décision technique.

---

## Permission rules cannot contain a literal `*`

Carried over from a previous project; true of Claude Code itself, not of any
one codebase.

- **In a `Bash(...)` allow rule, `*` always means "anything from here on" —
  there is no escape.** So a rule recording a command that genuinely contains
  an asterisk (`--include="*.cs"`, or a regex piece like `\s*` or `.*`) does
  not approve that one command: it approves everything matching up to the
  asterisk, including extra options slipped in at that spot, with no prompt.
- **A rule like this can only be deleted, never fixed.** The safe form is a
  wildcard at the very end (`Bash(/usr/bin/grep *)`), which usually already
  covers the command that was being approved, so nothing is lost by deleting
  the over-broad one.
- **`Read(...)` rules are different.** `Read(/tmp/**)` and friends are
  ordinary path globs and are fine; don't sweep them up in the same pass.
- Cheapest way to find these: for each `Bash(...)` rule, check whether the
  first `*` in the body is the last character. If not, the rule is broader
  than it looks.

Worth re-running that check on `.claude/settings.local.json` every few weeks —
these accumulate one one-off search at a time.

---

## `main` est la branche de travail, et rien ne l'impose

Consigne donnée par l'utilisateur le 2026-08-31, inscrite dans `CLAUDE.md`
(section « Branche de travail »). Répétée ici parce que c'est la première
chose qu'une session distante fera de travers : sa configuration lui assigne
d'office une branche `claude/<sujet>-<suffixe>`, et elle y poussera sans
réfléchir.

- **Tout se développe et se pousse sur `main`.** Une autre branche ne se crée
  que si le prompt le demande explicitement.
- **Basculer avant de commiter**, pas après : `git checkout main`.
- Aucun hook ne peut corriger cela — la branche est choisie au démarrage du
  conteneur, hors de portée de la configuration du projet.

Deux limites de droits, mesurées et reproductibles, qui encadrent toute
promesse sur les branches :

- **Supprimer une branche distante est impossible depuis une session.**
  `git push origin --delete` renvoie `403` à chaque tentative. Le diagnostic
  compte autant que le fait : le proxy ne signale **aucun** échec vers
  GitHub et `git ls-remote` fonctionne, donc ce n'est pas le réseau mais les
  droits de la session. Ne pas annoncer une suppression comme faite — la
  renvoyer à l'utilisateur, qui la fait en deux clics dans l'onglet
  *Branches* du dépôt.
- **Désigner la branche par défaut du dépôt** n'est pas non plus accessible
  d'ici. Tant que ce n'est pas fait côté GitHub, `main` est une branche
  ordinaire parmi d'autres.

Corollaire général, valable au-delà des branches : quand une opération Git
échoue, lire `curl -sS "$HTTPS_PROXY/__agentproxy/status"` **avant** de
conclure. Le champ `recentRelayFailures` vide écarte le réseau et laisse une
seule explication : les droits.

---

## Session du 2026-09-01 — le droit consolidé, et trois façons de se tromper

### Une règle « évidente » qui produit un résultat faux et crédible

Pour comparer un article de loi avant et après, il faut trouver « la rédaction
d'avant ». La règle évidente — **prendre la précédente dans la liste des
versions** — est fausse, et son résultat ne ressemble pas à une erreur.

La liste `<VERSIONS>` d'un article LEGI n'est **pas chronologique**, et elle
contient des rédactions **mort-nées** (`MODIFIE_MORT_NE`) : votées, jamais
entrées en vigueur. Sur l'article 6 de la loi n° 2004-575, la précédente dans
la liste est datée du **22 février 2222**. La comparaison tombait à **13 % de
texte commun** — un avant/après spectaculaire, entièrement faux, et que rien
ne signalait.

La bonne règle : **celle qui se termine au moment où la nôtre commence, les
mort-nées écartées.** 97 %, et rien ne change pour les six autres articles de
la même loi.

**La leçon, au-delà du cas :** quand une règle simple donne un résultat
*spectaculaire*, c'est le moment de la vérifier, pas de s'en réjouir. Ici, un
seul article sur sept sortait du lot — il aurait été facile de le prendre pour
une loi qui réécrit tout.

### Un trou dans les données déguisé en fait

Un article dont la rédaction précédente n'a pas été retrouvée s'affichait
**exactement comme** un article que la loi vient de créer : « texte nouveau ».
Les deux cas sont pourtant opposés — l'un est un fait sur la loi, l'autre un
manque de notre côté.

**À faire systématiquement :** quand une donnée est absente, distinguer
« absente parce qu'il n'y en a pas » de « absente parce qu'on ne l'a pas
trouvée », et l'afficher. Les deux se codent pareil (`None`) et se lisent
très différemment.

### Un verrou SQLite qui coûte quarante minutes

`database is locked`, à la fin d'une passe de quarante minutes, tout perdu.
La cause était moi : j'avais ouvert la base **en lecture seule** pour voir où
en était le remplissage. En mode journal classique, un lecteur bloque
l'écrivain.

**Pour toute base qu'un programme long remplit :** `PRAGMA journal_mode = WAL`
dès l'ouverture, `busy_timeout` en second filet, enregistrer par lots plutôt
qu'une fois à la fin, et ne pas effacer le fichier de travail en cas d'échec —
un téléchargement de dix minutes ne doit pas être refait pour rien.

### Ce qu'on peut lire sans place disque

Le socle LEGI pèse **1,1 Go compressé, 9,5 Go déplié, en 2,5 millions de
fichiers minuscules** — et le nombre de fichiers est plus pénible que le
volume. Il se lit **en flux** (`tarfile.open(fileobj=…, mode="r|gz")`) sans
rien écrire : **15,7 minutes chronométrées** pour une passe complète.

Généralisable : avant de conclure qu'une source est trop grosse, vérifier si
elle peut se lire en flux. La réponse a été oui ici, et elle change la
faisabilité du tout au tout.

### Deux réflexes de vérification qui ont servi

- **Compter les `def test_` et comparer à « Ran N tests ».** Deux classes de
  même nom se remplacent silencieusement, et des tests disparaissent sans que
  rien n'échoue.
- **Un test qui échoue n'a pas forcément raison.** `morceaux("Le maire
  décide.", "…décide seul.")` donnait un remplacement là où j'attendais un
  ajout : c'est mon cas d'essai qui était mal choisi — « décide. » et
  « décide » sont deux mots différents. Le code avait raison.

### CSS : `[hidden]` ne cache pas ce qui a un `display`

`.barre { display: flex }` l'emporte sur le `display: none` que le navigateur
donne à `[hidden]`. Cacher l'élément depuis JavaScript ne le cachait pas. Il
faut une règle `.barre[hidden] { display: none; }` explicite. À vérifier pour
tout élément qu'on masque et qui porte un `display` dans la feuille de style.

### Ce que Légifrance apporte, et ce qu'il n'apporte pas

Le site est **inaccessible aux programmes** (403 Cloudflare sur tout, y
compris `robots.txt`), son API demande un compte, et ses dossiers législatifs
redirigent vers `vie-publique.fr`, qui exige JS et cookies.

Ce n'est pas une perte : **le fonds qu'il affiche est publié en libre accès
sous le nom LEGI**, avec les mêmes identifiants `LEGIARTI…`. Légifrance est
une façon de *regarder* ces données, pas une source de plus.

**Corollaire :** avant de chercher à contourner un site, chercher d'où il tire
ses données. C'est souvent publié à côté, sans barrière.
