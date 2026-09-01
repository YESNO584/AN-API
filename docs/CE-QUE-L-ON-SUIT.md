# Ce que l'on suit exactement

**Mesuré le 2026-09-01**, sur les 2 859 dossiers et 10 634 étapes de la base.
Tous les chiffres viennent de `socle/parlement.db`. Écrit pour quelqu'un qui
ne connaît pas le fonctionnement du Parlement.

## En une phrase

**On suit 2 151 « textes » — c'est-à-dire tout ce qui peut devenir une loi —
et on écarte 708 dossiers qui sont des travaux de l'Assemblée n'aboutissant à
aucun texte de loi.**

## Le vocabulaire, une fois pour toutes

Trois mots reviennent, et ils ne veulent pas dire la même chose.

| Mot | Ce que ça veut dire |
|---|---|
| **Dossier** | Le classeur qui suit une affaire du début à la fin. C'est l'unité de l'open data : 2 859 en tout |
| **Texte** | Un dossier qui peut aboutir à une loi. 2 151 des 2 859 |
| **Loi** | Un texte arrivé au bout : voté par les deux chambres et signé par le Président. 107 à ce jour |

Un texte n'est donc pas encore une loi ; une loi est un texte qui a réussi.

## Les 2 151 textes : de quoi sont-ils faits ?

### Qui l'écrit décide du nom

| Nom | Combien | Qui l'écrit |
|---|---:|---|
| **Proposition de loi ordinaire** | 1 908 | Un ou plusieurs parlementaires |
| **Projet de loi ordinaire** | 68 | Le Gouvernement |

C'est la seule différence entre « proposition » et « projet » : **proposition =
un parlementaire, projet = le Gouvernement.** Rien d'autre ne les distingue.

### Les textes qui touchent aux règles du jeu

| Nom | Combien | Ce que c'est |
|---|---:|---|
| **Projet ou proposition de loi constitutionnelle** | 79 | Modifie la Constitution. Exige un vote identique des deux chambres, puis un référendum ou un Congrès |
| **Projet ou proposition de loi organique** | 52 | Précise comment la Constitution s'applique (le statut des juges, l'organisation d'une élection). Passe obligatoirement devant le Conseil constitutionnel |

### Les textes d'argent

| Nom | Combien | Ce que c'est |
|---|---:|---|
| **Projet de loi de finances de l'année** | 3 | Le budget de l'État. Un par an, en automne |
| **Projet de loi de finances rectificative** | 3 | Le budget corrigé en cours d'année |
| **Projet de loi de financement de la sécurité sociale** | 2 | Le budget de la Sécurité sociale. Un par an |
| **Projet de loi … approbation des comptes** | 2 | Le constat de ce qui a été dépensé l'année passée |

Ils sont peu nombreux mais énormes : **la loi de finances pour 2025 touche à
elle seule 574 articles de code**, quand la loi médiane en touche 8.

### Les traités

| Nom | Combien | Ce que c'est |
|---|---:|---|
| **Projet de ratification des traités et conventions** | 33 | Le Parlement autorise la France à signer un accord avec un autre pays |

**Ils ne changent aucune règle française** — vérifié : sur les 23 déjà
promulgués, aucun ne modifie un article de code. Il n'y a donc rien à
superposer pour eux, et ce n'est pas un trou dans les données.

### Le cas isolé

| Nom | Combien | Ce que c'est |
|---|---:|---|
| **Proposition de loi de l'article 11** | 1 | Le référendum d'initiative partagée : un texte porté par des parlementaires et des électeurs |

## Les 708 dossiers écartés, et pourquoi

Ce sont de vrais travaux de l'Assemblée. Ils ne produisent simplement **aucun
texte de loi** — rien à suivre jusqu'à une promulgation.

| Nom | Combien | Ce que c'est |
|---|---:|---|
| **Résolution** | 243 | L'Assemblée prend position, ou modifie son propre règlement intérieur. Ne change pas la loi. Exemples réels : « Le coût de l'immigration », « Supprimer le vote par assis et levé » |
| **Rapport d'information sans mission** | 205 | Une commission enquête et publie ses conclusions |
| **Résolution Article 34-1** | 188 | Une prise de position adressée au pays, prévue par la Constitution. Exemples réels : « Faire du don de plasma la grande cause nationale 2027 », « Reconnaître les fanfares comme patrimoine vivant » |
| **Mission d'information** | 23 | Un groupe de députés étudie un sujet |
| **Commission d'enquête** | 22 | Une enquête aux pouvoirs renforcés, sur un sujet précis |
| **Engagement de la responsabilité gouvernementale** | 20 | Motion de censure, question de confiance |
| **Responsabilité pénale du Président** | 4 | Procédure de destitution |
| **Allocution du Président de l'Assemblée** | 2 | Un discours |
| **Pétitions** | 1 | Une demande adressée à l'Assemblée par des citoyens |

La règle qui les écarte est écrite à un seul endroit : `TYPES_DE_LOI` dans
`socle/extraction.py`. Les dossiers restent en base, marqués `est_loi = 0`,
pour que le compte reste vérifiable.

## Où en sont les 2 151 textes

| | Combien |
|---|---:|
| **En cours** | 1 982 |
| **Promulgués** (devenus lois) | 107 |
| **Retirés** par leur auteur | 53 |
| **Rejetés** | 8 |
| Sans aucun acte enregistré | 1 |

**Attention à la lecture de ce tableau.** On serait tenté d'en tirer un taux
de réussite — 107 sur 2 151, soit 5 %. Ce serait faux : les 1 982 « en cours »
ne le sont pas tous vraiment. Beaucoup sont déposés, jamais inscrits à l'ordre
du jour, et s'éteignent sans que rien ne le dise dans les données.

Ce qu'on peut dire honnêtement : **169 textes ont une fin enregistrée, et 107
d'entre eux sont devenus des lois.** Pour les 1 982 autres, la source ne
tranche pas, et nous ne tranchons pas non plus.

## D'où ils partent

| | Combien |
|---|---:|
| Déposés d'abord à l'**Assemblée** | 1 553 |
| Déposés d'abord au **Sénat** | 597 |

Un texte parcourt les deux chambres quel que soit son point de départ. **La
source de vérité reste l'open data de l'Assemblée**, qui publie le parcours
complet, étapes sénatoriales comprises.

## Ce qui arrive à un texte : 10 634 étapes, 104 formes

Les étapes se regroupent en une poignée de familles. Les plus fréquentes :

| Famille | Combien | En clair |
|---|---:|---|
| Dépôt | 2 932 | Le texte est déposé, ou une nouvelle version est déposée |
| Renvoi en commission | 2 646 | Le texte est confié à une commission spécialisée |
| Réunion de commission | 962 | La commission se réunit et amende le texte |
| Discussion en séance | 790 | Le texte est débattu par tous les députés |
| Dépôt de rapport | 588 | Le rapporteur publie son analyse |
| Décision | 485 | Le texte est adopté, rejeté, ou renvoyé |
| Nomination de rapporteur | 350 | Un député est chargé du texte |
| Procédure accélérée | 156 | Le Gouvernement raccourcit le parcours |
| **Promulgation** | **107** | Le Président signe : le texte devient loi |
| Retrait | 82 | L'auteur retire son texte |

## Ce que la base contient déjà, en plus du parcours

| | Combien |
|---|---:|
| Amendements, avec leur texte et leur sort | 109 854 |
| Scrutins (votes détaillés, nom par nom) | 8 434 |
| Textes ayant au moins un vote enregistré | 151 |
| Textes ayant au moins un amendement | 289 |

Un vote nom par nom n'existe que s'il y a eu **scrutin public**, ce qui est
rare : la plupart des votes se font à main levée et ne laissent qu'un
résultat global.

## Ce que la base ne contient pas

- **Le contenu des textes.** On sait qu'un texte a été adopté ; on n'a pas
  ses articles. Voir `sources/monalisa.md` et `sources/textes-pdf-assemblee.md`.
- **Les débats.** Ni compte rendu, ni vidéo.
- **La législature 17 seulement**, c'est-à-dire depuis juillet 2024.
