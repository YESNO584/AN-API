"""Lecture du droit consolidé (jeu de données LEGI) : ce qu'une loi change.

Ce module ne fait que lire et comparer. Il ne télécharge rien de sa propre
initiative et n'écrit dans aucune base : `recuperer_legi.py` s'en charge.

**Ce qu'on cherche.** Quand une loi modifie un article de code, LEGI publie la
nouvelle rédaction *et* garde l'ancienne. On peut donc superposer les deux et
montrer exactement ce qui change. Le raccordement avec nos dossiers est direct :
chaque rédaction porte le numéro de la loi qui l'a produite.

**Ce qu'on cherche aussi, depuis le 2026-09-03 : ce qu'une loi ajoute.** Ses
propres articles. Ils n'ont pas d'« avant » — il n'y a donc rien à superposer —
mais ils sont du droit nouveau, et les taire donnait une réponse absurde : une
loi de finances de fin de gestion, dont presque toute la matière est dans ses
propres articles, s'affichait comme ne changeant que deux articles. La source
les publie, avec leur texte ; c'est le rapprochement qui manquait. Voir
`AJOUTE`, `loi_qui_porte` et `est_un_ajout`.

**Ce qu'on ne cherche pas.** Les liens `CITATION` : la loi cite l'article sans y
toucher. Ils sont deux fois plus nombreux que les vraies modifications (5 520
contre 2 711, mesuré le 2026-09-01) — les compter ferait dire n'importe quoi à
l'application.

Source : https://echanges.dila.gouv.fr/OPENDATA/LEGI/ — Licence Ouverte (Etalab).

**Un paquet, une responsabilité par module.** Les règles vivent dans les
modules ci-dessous ; cet en-tête les réexporte pour que tout le projet
continue d'écrire `legi.morceaux`. `mutations_legi.py` défait les règles
module par module.
"""
from __future__ import annotations

from legi.etats import (  # noqa: F401
    CHANGEMENTS, AJOUTE, EN_COURS, SANS_FIN, SANS_DATE, TYPE_SANS_TEXTE,
)
from legi.depot import (  # noqa: F401
    DEPOT_LEGI, archives_du_depot, parcourir_archive, url_legifrance,
)
from legi.balises import (  # noqa: F401
    attributs, champ, nettoyer, normaliser,
)
from legi.ajouts import (  # noqa: F401
    sans_les_renvois, support, loi_qui_porte, est_un_ajout, INTITULE_MAX,
    intitule_de_secours, est_en_attente,
)
from legi.redactions import (  # noqa: F401
    versions, est_mort_ne, version_precedente, changements, ou_se_trouve,
    lire_article, date_d_effet, etat_du_precedent,
)
from legi.forme import (  # noqa: F401
    PONCTUATION, sans_forme, est_de_forme, remplacement_de_forme,
    changement_de_fond, au_caractere, morceaux, part_commune,
)
