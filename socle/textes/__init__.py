"""Le texte d'un projet ou d'une proposition de loi, version par version.

**Ce que ce module lit.** L'Assemblée publie le texte intégral de chaque
version d'un texte — celui qui est déposé, celui qui sort de la commission,
celui qui est adopté en séance — à une adresse qui se déduit de l'identifiant
du document :

    https://www.assemblee-nationale.fr/dyn/docs/PIONANR5L17B1794.raw

C'est le document Word de l'Assemblée converti en HTML. **Ce n'est pas du
JSON, et il n'en existe pas** : le JSON que publie l'Assemblée pour un document
est une fiche signalétique, dont le champ `divisions` est vide (mesuré le
2026-09-18 sur six documents de natures différentes). Mais ce HTML-ci est
*structuré*, ce qui est la seule chose qui compte : la classe du paragraphe dit
où commence un article, et les tableaux restent des tableaux.

**Les identifiants viennent de l'archive déjà téléchargée chaque matin.** Chaque
étape du parcours nomme le document qu'elle produit ou qu'elle examine
(`texteAssocie`, `texteAdopte`) : aucune devinette sur l'étape à laquelle
rattacher une version, et aucun appel réseau pour le savoir.

**Ce que ça couvre**, mesuré le 2026-09-18 sur les 2 219 textes de loi de la
législature : 1 749 ont au moins une version publiée par l'Assemblée — donc un
texte à lire — et **249 en ont au moins deux**, donc une comparaison possible.
Les 470 autres sont nés au Sénat, qui publie ses textes ailleurs.

**Les règles viennent toutes d'un défaut constaté**, jamais d'une
supposition. Voir `../docs/sources/textes-assemblee-html.md` pour les mesures.

**Deux modules, séparés exprès** (2026-10-10) : `lecture` découpe un document
en articles — ses règles sont celles dont `textes.db` garde le résultat, et que
`empreinte_de_lecture` couvre ; `comparaison` calcule tout le reste à la
publication, et le changer ne relit rien. Le reste du projet écrit
`textes.articles` ou `textes.comparer` comme avant.
"""

from __future__ import annotations
from textes.lecture import (
    ALINEA, BALISE, BALISE_BUDGETAIRE, CLASSE, CLASSE_ARTICLE, DEBUT_ARTICLE,
    DEBUT_DU_DISPOSITIF, DISPOSITIF, ENTETES, FIN_DU_DISPOSITIF, FIN_DU_TEXTE,
    HORS_TEXTE, PASTILLE, URL_DOCUMENT, articles, articles_budgetaires, blocs,
    empreinte_de_lecture)
from textes.comparaison import (
    INTITULE, MENTION, MENTION_TITRE, NON_REPRODUIT, amendements_de_l_article,
    amendements_du_document, amendements_du_parcours, avec_les_alineas, comparer,
    etat, numero, premiere_version, racine, resume, sans_mention, titre_propre,
    version_a_jour)
