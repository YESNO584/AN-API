# Étape 0 — ce que valent les sources, vérifié

**Mesuré le 2026-08-31**, depuis une session Claude Code, sur les fichiers
réellement téléchargés. Chaque fiche de ce dossier donne le détail d'une
source ; ce fichier-ci donne la conclusion.

## La conclusion en une phrase

**L'open data de l'Assemblée nationale contient à lui seul le parcours
complet d'un texte à travers les deux chambres, et il est mis à jour tous
les jours** — ce qui rend inutile le recollement que le plan redoutait, et
permet de construire la maquette sur données réelles tout de suite.

## Ce qui change par rapport au plan

| Ce que `PLAN.md` supposait | Ce qui est vrai |
|---|---|
| La Fabrique de la Loi est la piste n° 1 (stratégie A) | **Elle est abandonnée.** Ses données s'arrêtent à la 15e législature (janvier 2022) ; plus rien n'a été ajouté depuis. Inutilisable pour un suivi de l'actualité |
| Il faut peut-être recoller les deux chambres nous-mêmes (stratégie C), « coûteux, fragile, jamais fiable à 100 % » | **Pas nécessaire.** L'Assemblée publie elle-même l'adresse du dossier Sénat correspondant. Le rapprochement marche sur **100 %** des dossiers testés |
| Le recollement est « le premier travail de l'étape 0 », non vérifié | **Vérifié : 910 dossiers portent un lien vers le Sénat, 910 retrouvés** dans le fichier du Sénat après normalisation de l'adresse |
| Une journée de séance = « quelques centaines de milliers de jetons » | **Mesuré.** Assemblée : 198 000 caractères par séance (médiane sur 601 séances). Sénat : 462 000 caractères par journée (médiane sur 199 journées) |
| Environ 150 jours de séance par an et par chambre | **314 séances à l'Assemblée et 126 journées au Sénat en 2025.** L'Assemblée publie par séance, le Sénat par journée — les deux ne se comparent pas directement |
| Le traitement d'une année de débats des deux chambres se compte « en centaines d'euros » | **Mesuré : 34,8 millions de jetons pour l'année 2025 complète, soit 35 $ en Sonnet 5 avec traitement par lots.** Des dizaines d'euros, pas des centaines |

## Le chiffre qui conditionnait les coûts

Volume de débats réellement publié, balises retirées :

| Année | Assemblée | Sénat | Total | ≈ jetons |
|---|---:|---:|---:|---:|
| 2024 (depuis juillet) | 12,9 M car. | — | 12,9 M | 3,4 M |
| **2025 (année pleine)** | **63,1 M car.** | **67,4 M car.** | **130,5 M** | **34,8 M** |
| 2026 (jusqu'à fin août) | 43,2 M car. | 34,6 M car. | 77,9 M | 20,8 M |

Coût de lecture d'une année entière de débats des deux chambres, au tarif
d'entrée, avec le traitement par lots (-50 %) :

| Modèle | Une année de débats |
|---|---:|
| Claude Haiku 4.5 | **17 $** |
| Claude Sonnet 5 | **35 $** |
| Claude Opus 5 | **87 $** |

Le plan disait « des centaines d'euros, pas des milliers ». La mesure dit
**des dizaines d'euros**. Sa conclusion tient et se renforce : **le coût des
résumés n'est pas le facteur limitant du projet.**

## L'état de chaque source

| Source | État | Fraîcheur | Fiche |
|---|---|---|---|
| Assemblée nationale | **À retenir — source principale** | Mise à jour quotidienne (dernière : le jour même du test) | [`assemblee-nationale.md`](assemblee-nationale.md) |
| Sénat | **À retenir — source de complément** | Mise à jour quotidienne | [`senat.md`](senat.md) |
| Monalisa (texte des lois, Sénat) | **Piste ouverte** — texte structuré, mais côté Sénat seulement (203 de nos 2 859 dossiers) | Mise à jour quotidienne | [`monalisa.md`](monalisa.md) |
| Textes de l'Assemblée en PDF | **Piste ouverte** — lisible à 86 %, porterait la comparaison à 319 textes | Publiés au fil des séances | [`textes-pdf-assemblee.md`](textes-pdf-assemblee.md) |
| Journal officiel (DILA) | **Piste ouverte** — texte des lois promulguées et censures constitutionnelles | Deux archives par jour | [`journal-officiel.md`](journal-officiel.md) |
| Droit consolidé (LEGI, DILA) | **Piste ouverte** — l'article de code avant et après la loi qui le modifie, 2 446 articles mesurés | Une archive par jour | [`droit-consolide.md`](droit-consolide.md) |
| La Fabrique de la Loi | **À écarter** — figée depuis 2022 | Dernière donnée : janvier 2022 | [`fabrique-de-la-loi.md`](fabrique-de-la-loi.md) |
| Légifrance via PISTE | **Non vérifié** — demande un compte | inconnue | [`legifrance-piste.md`](legifrance-piste.md) |
| NosDéputés.fr / NosSénateurs.fr | **Hors service au moment du test** | — | voir `../ACCES-RESEAU.md` |

## Ce que cela permet de faire maintenant

1. **La maquette sur données réelles**, sans attendre : les dossiers
   législatifs de l'Assemblée suffisent à afficher un fil de textes classés
   par étape du parcours.
2. **Le modèle de données du §3.1 du plan est confirmé par les faits** : un
   dossier, des étapes datées, chacune rattachée à une chambre. C'est
   exactement la forme dans laquelle l'Assemblée publie.
3. **Ce qui reste à décider** : faut-il un compte PISTE pour Légifrance ?
   Seulement si l'on veut le texte consolidé de la loi promulguée. Pour
   suivre le parcours, non.
