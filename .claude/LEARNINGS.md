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
