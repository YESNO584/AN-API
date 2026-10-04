# Faut-il séparer la base du Sénat de celle de l'Assemblée ?

**Mesuré le 2026-10-04**, après l'échec de la publication n° 114. Les
commandes qui produisent ces chiffres sont dans `tmp/q1.py` à `tmp/q4.py`.

Deux questions, posées dans cet ordre parce que la première est la cause de
l'incident et la seconde prépare la suite.

## La réponse en deux lignes

1. **Le cache de `parlement.db` surveille un fichier qui fait deux métiers à la
   fois.** Deux commits sur 127 ont fait retélécharger 412 Mo sans qu'une
   seule ligne stockée change. L'un des deux est celui qui a cassé la
   publication d'hier.
2. **Une base Sénat séparée pèserait 30 Mo** et se rattacherait aux textes de
   l'Assemblée par une clé que la source publie elle-même. C'est le motif que
   le projet emploie déjà deux fois — mais elle ne sert à rien tant qu'on
   n'affiche pas de données du Sénat.

## 1. Pourquoi une modification d'affichage a fait retélécharger 412 Mo

`parlement.db` est gardée d'un jour sur l'autre, et **la clé de ce cache porte
l'empreinte de trois fichiers** : `schema.sql`, `extraction.py` et
`recuperer.py` (`.github/workflows/donnees.yml`). Changer l'un d'eux jette la
base et refait tout.

C'est voulu, et la raison est bonne : si une règle de lecture change, la base
de la veille ne contient que ce que l'ancienne règle retenait, et la nouvelle
ne s'appliquerait qu'aux archives du jour.

**Mais `extraction.py` fait deux métiers.** Sur ses 88 noms publics :

| | Noms |
|---|---:|
| Utilisés par `recuperer.py` — ce qui **remplit** la base | 29 |
| Utilisés par `publier.py` — ce qui la **lit** | 17 |
| Utilisés par les deux | 4 |
| **Utilisés par la seule publication** | **13** |

Les treize derniers ne décident de rien de ce qui est stocké. En font partie
`ETAPES_SENAT` et `moment_au_senat`, ajoutés hier : ils rangent les colonnes
de l'onglet « Sénat » au moment de publier, et ne touchent à aucune table.

### Combien de fois le cache a-t-il été jeté pour rien

Sur **127 commits** de l'historique, **19 ont jeté le cache** (15 %). La
plupart le méritaient : ils changeaient `schema.sql` et `recuperer.py`
ensemble, donc bien ce qui est stocké.

Quatre n'ont touché que `extraction.py`. En regardant ce que leur diff change
réellement :

| Commit | Verdict |
|---|---|
| 2026-10-04 — l'onglet « Sénat » | **n'a touché que de la lecture** |
| 2026-09-02 — le calendrier des séances | **n'a touché que de la lecture** |
| 2026-08-31 — reprendre un transfert coupé | touche `telecharger`, `lire_reunions` : justifié |
| 2026-08-31 — réessayer un transfert coupé | idem |

**Deux invalidations sur 127 commits étaient inutiles** — 1,6 %. C'est rare,
et c'est exactement ce qui a cassé la publication d'hier : sans elle, la base
de la veille aurait été reprise et les 412 Mo n'auraient jamais été demandés
au serveur lent de l'Assemblée.

### Ce qu'on peut en faire, et ce qu'on ne peut pas

`hashFiles` empreinte des **fichiers entiers** : on ne peut pas lui demander de
ne surveiller que les 29 noms qui comptent. Trois voies :

| | Ce que ça donne | Ce que ça coûte |
|---|---|---|
| **Couper `extraction.py` en deux** — ce qui remplit d'un côté, ce qui lit de l'autre | Le cache ne se jette plus que quand c'est mérité | Un fichier de plus, et une coupure à tenir dans le temps |
| Retirer `extraction.py` de la clé | Le cache ne se jette presque plus | **Dangereux** : une vraie règle de lecture changerait sans refaire la base, et personne ne le verrait |
| Ne rien faire | Rien à écrire | Une publication cassée tous les deux mois environ, et 412 Mo pour rien |

**Je recommande la première.** C'est la même coupure que le projet a déjà
faite pour `legi.py` et `textes.py` : chacun a sa clé de cache, qui ne
surveille que ses propres règles.

**Mais elle ne répare pas l'incident d'hier à elle seule.** Un serveur lent
peut couper un téléchargement n'importe quel matin, cache ou pas. La reprise
sur les sources obligatoires reste nécessaire — c'est l'autre correction, à
part.

## 2. Ce que coûterait une base Sénat séparée

**Aujourd'hui l'onglet « Sénat » ne lit aucune donnée du Sénat.** Les étapes
qu'il affiche viennent de l'open data de l'Assemblée, qui décrit le parcours
dans les deux chambres. Le seul fichier du Sénat que le socle télécharge fait
3,5 Mo et sert à une chose : savoir qu'un texte est fini sans avoir été
promulgué.

La question se pose donc **pour la suite** — les scrutins, les amendements,
les sénateurs — et la réponse est oui.

### Ce qu'elle contiendrait, et ce qu'elle pèserait

Construite pour de vrai, en ne gardant que ce qui est publié :

| | |
|---|---:|
| **Une base Sénat utile** | **30,2 Mo** |
| …dont 6 744 amendements adoptés sur nos textes, avec leur texte entier | |
| À comparer : `parlement.db` | 337,6 Mo |
| À comparer : `textes.db` | 4,2 Mo |

Ses sources : `dosleg.zip` (15,3 Mo), `ameli.zip` (146,9 Mo) et une page web de
29 Ko par jour pour les scrutins.

### La table de jointure, et pourquoi elle n'a rien à inventer

**La clé existe et les deux côtés la publient.** Le Sénat appelle `signet`
l'adresse courte d'un dossier (`pjl25-689`) ; l'Assemblée publie cette même
adresse pour chacun de ses textes. Le rapprochement est donc une lecture, pas
une devinette — **730 de nos 731 textes passés au Sénat y sont retrouvés**.

Une seule table suffit :

```
texte_senat ( dossier_uid , signet )
             ↑ notre texte   ↑ le dossier au Sénat
```

Tout le reste s'y accroche : les scrutins par leur signet, les amendements par
le leur, les sénateurs par leur matricule.

### Ce que ça change au temps de publication

Aujourd'hui, une publication réussie prend **127 secondes** pour tout
récupérer et **104 secondes** pour écrire les fichiers.

Une base Sénat séparée s'ajouterait à ce temps la première fois, puis serait
**gardée d'un jour sur l'autre avec sa propre clé** — comme `legi.db` et
`textes.db`. Une modification des règles de l'Assemblée ne la jetterait plus,
et une modification des règles du Sénat ne jetterait plus `parlement.db`.

**C'est le vrai gain, et il est double** : chaque base ne se refait que quand
ses propres règles changent, et une panne chez l'une n'emporte pas l'autre.

## Ce que je ferais, dans l'ordre

| | Quand | Pourquoi |
|---|---|---|
| **1. La reprise sur toutes les sources** | maintenant | C'est ce qui a cassé la publication, et ça ne dépend d'aucun découpage |
| **2. Couper `extraction.py` en deux** | avant la prochaine règle d'affichage | Évite de rejeter 412 Mo pour une colonne |
| **3. La base Sénat séparée** | **avec le premier affichage de données du Sénat** | Aujourd'hui elle serait vide : rien n'en est publié |

Le troisième point ne se décide pas tout seul : il arrive avec les votes du
Sénat, les amendements ou les thèmes — voir
[`CE-QUE-LE-SENAT-APPORTERAIT.md`](CE-QUE-LE-SENAT-APPORTERAIT.md).
