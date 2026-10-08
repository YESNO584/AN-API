"""Lecture de l'open data de l'Assemblée : dossiers législatifs et leurs étapes.

Ce paquet ne fait que lire et classer. Il ne télécharge rien de sa propre
initiative, n'écrit dans aucune base et n'affiche rien : `recuperer.py` s'en
charge, et `../maquette/preparer_donnees.py` l'utilise aussi.

Le modèle est celui du §3.1 de `../docs/PLAN.md` : **un dossier, des étapes
datées, chacune rattachée à une chambre.** L'Assemblée publie le parcours dans
les deux chambres, y compris les étapes passées au Sénat — il n'y a donc aucun
rapprochement à faire entre les deux sources.

Source : https://data.assemblee-nationale.fr — Licence Ouverte (Etalab).

**Un paquet, une responsabilité par module, un seul nom par règle.** Les
règles vivent dans les modules ci-dessous ; cet en-tête les réexporte pour
que tout le projet continue d'écrire `extraction.analyser`. La clé du cache
de `parlement.db` empreinte le dossier entier — déplacer une règle d'un
module à l'autre change donc la clé, comme avant la modifier changeait le
fichier.
"""
from __future__ import annotations

from extraction.sources import (  # noqa: F401
    DEPOT, URL_ARCHIVE, URL_SCRUTINS, URL_ORGANES, URL_AMENDEMENTS,
    URL_AGENDA, URL_ACTEURS_LARGE, PHOTO_DEPUTE, URL_SENAT, LEGISLATURE,
    PREFIXE_DOSSIER_AN, URL_DEBATS, NS_DEBATS,
)
from extraction.archives import ESSAIS_SANS_PROGRES, MORCEAU, telecharger  # noqa: F401
from extraction.agenda import (  # noqa: F401
    GENRES_HORS_TEXTE, PREFIXE_SEANCE_AN, points_hors_texte, lire_points_hors_texte,
)
from extraction.actes import (  # noqa: F401
    CHAMBRES, QUANTIEMES, chambre_du_code, libelle, aplatir, precision_acte,
    details_acte, numero_etape, fusionner_actes,
)
from extraction.dossiers import (  # noqa: F401
    TYPES_DE_LOI, ETAPES, EN_COURS, PROMULGUE, RETIRE, SANS_ACTE, REJETE,
    NON_ADOPTE, CADUC, FINS_SENAT, statut_final, analyser, est_rejete,
    lire_senat, cle_senat, lire_archive, lire_reunions, lire_documents,
)
from extraction.scrutins import (  # noqa: F401
    ENSEMBLE, ARTICLE, AMENDEMENT, MOTION, AUTRE, PORTEES, classer_portee,
    analyser_scrutin, position_dominante, refs_de_vote, lire_scrutins,
)
from extraction.acteurs import (  # noqa: F401
    COULEURS_GROUPES, DEGRADE, couleur_de_groupe, mediane_depuis_histogramme,
    places_du_scrutin, ordonner_groupes, lire_acteurs, lire_groupes,
    lire_organes,
)
from extraction.amendements import (  # noqa: F401
    AJOUT, RETRAIT, NEUTRE, VERBES_RETRAIT, VERBES_REMPLACEMENT,
    colorer_dispositif, analyser_amendement, lire_amendements,
)
from extraction.debats import (  # noqa: F401
    SECTIONS_ARGUMENTAIRE, PAROLE, INTERRUPTION, PRESIDENCE,
    est_la_presidence, sigle_d_orateur, numeros_de_texte, prises_de_parole,
    lire_debats, sigles_nommes, completer_les_sigles, SOUTENIR_AMENDEMENT,
    SORT_AMENDEMENT, debats_par_amendement, lire_debats_par_amendement,
    PREFIXE_DOCUMENT_AN, documents_par_numero, dossier_des_numeros,
)
