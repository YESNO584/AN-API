# AN-API — Project Memory

## Each prompt triggers these rules
- Never edit anything outside of this folder, or nested folders.
- Limit all read operations to the scope of this project, except if explicitly
  required by the prompt. Reading is allowed for any file or internet source
  shared directly in a message.
- Reformulate every prompt to make it optimal for Claude Code, and ask for
  confirmation. Only start responding after the reformulation is confirmed.

## Architecture

Le projet suit `docs/PLAN.md`. Il en est à l'**étape 1 : la maquette**. Il n'y
a pas encore d'application, de base de données ni de dépendances.

| Dossier | Ce qu'il contient |
|---|---|
| `docs/` | Le plan, les fiches de sources, la note d'accès réseau. Documents, pas du code |
| `docs/sources/` | Ce que valent les sources de données, **mesuré** (étape 0, faite le 2026-08-31) |
| `socle/` | **Le cœur du code.** Récupère, range, publie. `extraction.py` (les règles, testées), `recuperer.py` (le programme quotidien), `publier.py` (écrit les fichiers mis en ligne), `serveur.py` (développement local seulement), `schema.sql`. Voir `socle/README.md` |
| `.github/workflows/` | La publication quotidienne des données, exécutée par GitHub |
| `maquette/` | La maquette de l'étape 1 : `feed.html`, un seul fichier, qui **lit les données publiées par le socle**. Voir `maquette/README.md` |
| `.claude/` | La configuration Claude Code |

- **La source de vérité des données est l'open data de l'Assemblée
  nationale.** Elle contient le parcours d'un texte dans *les deux* chambres,
  y compris les étapes passées au Sénat. Ne pas écrire de code de rapprochement
  entre les deux chambres : l'Assemblée publie déjà le lien.
- **Les règles de lecture des dossiers vivent dans `socle/extraction.py`, à
  un seul endroit.** Ne pas les recopier ailleurs : la maquette les importe.
  Toute modification doit passer par `socle/test_extraction.py`.
- **Aucune donnée du Parlement n'est versionnée.** La base `socle/parlement.db`,
  le dossier `socle/public/` et les archives téléchargées sont ignorés par
  git — ils se reconstruisent avec `socle/recuperer.py` puis `socle/publier.py`.
  La maquette ne les embarque plus : elle lit les fichiers publiés.
- **Une page web ne peut pas aller chercher ces données elle-même** — les
  portails n'envoient pas l'en-tête `Access-Control-Allow-Origin`. Toute
  maquette autonome passe donc par une préparation hors ligne.
- **Il n'y a pas de serveur en production, et c'est voulu** (question 8 du §10
  du plan, décidée le 2026-08-31). Les données sont publiées en fichiers par
  GitHub, chaque matin, sur **<https://yesno584.github.io/AN-API/>**.
  `socle/serveur.py` ne sert qu'au développement local ; il resservira à
  l'étape 4, quand les favoris exigeront de stocker quelque chose par
  utilisateur.
- **Le dépôt doit rester public.** C'est ce qui rend la publication gratuite
  et lisible sans mot de passe. Le repasser en privé casserait les deux :
  GitHub Pages exigerait un abonnement, et l'application ne pourrait plus
  rien lire.
- **L'application sera en Flutter (Dart), le mobile d'abord**, le web
  ensuite et dans le même code (décidé le 2026-08-31 — question 7 du §10 du
  plan). **Aucun code Flutter n'existe encore :** le seul code du dépôt reste
  le Python de préparation et le HTML/CSS/JS de la maquette.
- **Deux conséquences de ce choix, à ne pas redécouvrir plus tard :** une
  application Flutter *web* butera sur le même refus que la maquette HTML
  (pas d'en-tête `Access-Control-Allow-Origin` côté portails) et exigera donc
  un serveur intermédiaire — l'application *mobile*, elle, n'a pas cette
  limite ; et l'archive de 10 Mo des dossiers législatifs ne peut pas être
  téléchargée et décortiquée sur un téléphone à chaque ouverture.
- **`.claude/code_rules.json` ne s'applique à rien ici** : il vise `**/*.cs`,
  et le dépôt ne contiendra pas de C# — le code applicatif sera du Dart. Le
  faire re-miner (agent `code-convention-miner`) n'aura de sens qu'une fois
  le premier code Flutter écrit. Jusque-là, un rapport « 0 finding » signifie
  que rien n'a été vérifié, pas que le code est propre.

## Read these first
- `.claude/LEARNINGS.md` — cross-session lessons. Read at the start of every
  session; append to it at the end of one.
- `.claude/code_rules.json` — the code-quality contract the checker enforces.
  Worth reading before writing code, because it is currently a **generic C#
  template**, not this project's rules: its `scope.include_globs` is `**/*.cs`
  and every `evidence` field is empty. If this project turns out not to be C#,
  that file is wrong and must be re-mined before its report means anything.
- `.claude/reference/store-apis.md` — how to list a publisher's live apps and
  versions from the App Store Connect and Google Play APIs. Only relevant if
  this API ends up talking to the mobile stores; ignore otherwise.

## Checks
| Checker | How to run | Report |
|---|---|---|
| Code rules | `cd .claude/scripts && ./code_rule_report.py` | `.claude/reports/code_rule_audit.html` |
| Code rules, one unit | `cd .claude/scripts && ./code_rule_checker.py <unit_id>` | console |
| Unit discovery | `cd .claude/scripts && ./discover_units.py` | console |

**When it MUST be run:** before any commit that adds or changes source files,
and again before opening a pull request. It is not wired into a git hook —
nothing runs it for you.

**Caveat that outranks the table:** the checker matches `**/*.cs` only, so
until `.claude/code_rules.json` is mined against real code it will report
"0 findings" on a non-C# codebase. A clean run from an unmined rules file is
not evidence of clean code — it is evidence that nothing was checked.

## External / vendored code
- None yet — the repository has no third-party code in-tree.
- When vendored code is added, list its folders here and register them in
  `.claude/code_rules.json` under `scope.vendor_detection.path_contains_any`,
  so the checker stops linting code we do not own.
- The standing rule for that code: **wrap, don't patch.** If a bug looks like
  it is in vendor code, check our wrapper first.

# Project Rules

## Scope enforcement (mechanically enforced — see .claude/settings.json)
- Edits/writes are restricted to this folder and its subfolders. This is
  enforced by `permissions.deny` plus the `enforce-scope.sh` PreToolUse hook —
  it is not optional and does not depend on remembering this instruction.
- Reads are limited to this project's scope. Reads outside the project prompt
  for explicit confirmation (`permissions.ask`) rather than happening
  silently. Files or internet sources shared directly in a prompt are always
  fine to read.

## Before starting any task
Never begin acting on a prompt directly. First, restate the request in a
clear, optimized form for Claude Code:
- explicit scope (which files/subsystems this touches)
- expected output/deliverable
- constraints or things to avoid

Then ask: "Is this correct?" and stop. Do not read (beyond what's needed to
reformulate), edit, or run anything until the user explicitly confirms the
reformulation. This is reinforced on every message via a UserPromptSubmit
hook (`inject-rules.sh`), but the actual "wait for confirmation" behavior
depends on Claude following it — no hook can force a pause mid-turn.

## Branche de travail

**`main` est la branche du projet.** Tout se développe et se pousse dessus.

- Ne créez **pas** de branche `claude/...` ou de branche de fonctionnalité de
  votre propre initiative. Une autre branche ne se crée que si l'utilisateur
  le demande explicitement dans le prompt.
- Si la configuration de la session vous **assigne** une branche (les sessions
  distantes le font systématiquement, avec un nom de la forme
  `claude/<sujet>-<suffixe>`), cette consigne-ci l'emporte : basculer sur
  `main` (`git checkout main`) avant de commiter, et pousser sur `main`.
- La consigne ne peut pas être imposée mécaniquement : aucun hook ne peut
  changer la branche assignée au démarrage. Elle repose sur le fait de la
  lire — d'où sa place ici.

Deux limites constatées le 2026-08-31, à connaître avant de promettre quoi
que ce soit sur les branches :

- **Une session ne peut pas supprimer une branche distante.** `git push
  origin --delete` renvoie `403`, de façon reproductible. Ce n'est pas le
  réseau (le proxy ne signale rien, la lecture fonctionne) : les droits de la
  session ne le permettent pas. La suppression se fait à la main sur GitHub.
- **`main` n'est pas la branche par défaut du dépôt côté GitHub**, sauf si
  quelqu'un l'a réglé depuis. Ce réglage-là n'est pas accessible d'ici non
  plus.

## Self-configuration (standing authorization)
Claude may create, edit and override its own harness configuration in this
project without asking each time: `.claude/agents/**`, `.claude/skills/**`,
`.claude/hooks/**`, `.claude/scripts/**`, `.claude/settings*.json`, this file,
any nested `CLAUDE.md`, `.claude/LEARNINGS.md`, and the auto-memory directory.
The intent is that each session's learnings are written back into config so
the next session starts better informed.

Editing product source is NOT covered by this — source changes are asked for
first, as usual. Adding a `CLAUDE.md` inside a subsystem folder is.

Product source, for this rule, means **every file in the repository that is
not `.claude/**` and not this `CLAUDE.md`.** That deliberately broad wording
is the only safe one while the repository is empty: with no source layout to
name, a narrower glob would silently exempt whatever gets created first.
Replace it with the real glob (e.g. `src/**/*.ts`) in the same session that
creates the source folder.

## Check before you answer

Understand the whole thing before saying anything. Assume nothing. Almost
every answer is already somewhere in the project — read the code, run the
checkers, read the scripts themselves, check git history. Look it up instead
of guessing.

**Say "I'm not sure" only when the information genuinely isn't anywhere.**
Doubt is a last resort, not a shortcut past the checking. And when it is
genuine, say plainly what is unknown and what was already tried.

**A tool's output is a lead, not a fact.** Confirm it against the source
before repeating it or acting on it. Three real failures of this kind, worth
keeping as the shape to watch for:

- A checker script was run from the command line to capture a baseline. It
  had no command-line entry point, so it printed nothing and reported
  success — 18 empty files were written and the mistake only surfaced when a
  later comparison crashed. *Check that a command actually produced output.*
- A count of "7 skipped checks" was repeated from an audit report. Reading
  the file showed 8, and that the damage was wider than the audit could see.
  *Read the file before quoting a number.*
- A test was flagged as broken by a checker. Counting by hand showed the test
  was right and the checker was wrong; the checker got fixed instead of the
  test. *When a tool and the code disagree, find out which one is wrong.*

This does not override the reformulation rule above. The boundary:

- **Before the user confirms** — look only as far as needed to describe the
  job accurately.
- **After the user confirms** — verify everything, and don't guess.

## How to answer

Write for someone who knows nothing about the subject. These rules are about
answers in the chat, not about code comments or the documents under
`.claude/`, which stay precise.

- **Simple words.** Skip a technical term whenever a plain one works. If a
  technical term is unavoidable, say in a few words what it means.
- **Big picture first.** A short overview of what happened and what it means
  beats a long, detailed description. Add detail only where it changes what
  the user would decide or do.
- **One name per thing.** Pick a name and keep it for the whole conversation.
  Never switch between two words for the same thing (e.g. don't alternate
  between "the checker", "the audit" and "the script" — choose one).
- **Problems: the first sentence is the whole problem.** If something is
  wrong, the opening sentence alone must be enough to understand it. Put the
  cause, the consequence and the fix after that, shortest first.
- **Say what it means, not just what was done.** "This test can never pass"
  beats "the declared count differs from the reachable count".

## Token usage visibility
Exact token/cost usage is shown in the status line (see
`.claude/hooks/statusline.sh`) and via the built-in `/cost` command — not
something for Claude to compute or report in its answers, since it has no
reliable access to the exact running total.
