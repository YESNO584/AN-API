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
