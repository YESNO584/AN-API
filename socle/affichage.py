#!/usr/bin/env python3
"""Les règles qui ne décident **que de l'affichage**, et jamais du stockage.

**Pourquoi ce fichier existe, et pourquoi il n'est pas dans `extraction.py`.**

La base `parlement.db` est gardée d'un jour sur l'autre, et la clé de ce cache
porte l'empreinte de `schema.sql`, `extraction.py` et `recuperer.py`
(`.github/workflows/donnees.yml`). C'est voulu : si une règle de **lecture des
archives** change, la base de la veille ne contient que ce que l'ancienne règle
retenait, et il faut tout refaire.

Mais `extraction.py` faisait deux métiers. Mesuré le 2026-10-04 : sur ses 88
noms publics, 13 ne servaient qu'à la publication — ils ne touchaient à aucune
table. Les y laisser avait un prix : sur 127 commits, **19 ont jeté le cache et
2 l'ont fait pour rien**, dont celui qui a cassé la publication n° 114. Changer
le nom d'une colonne à l'écran faisait retélécharger 412 Mo, qui sont tombés sur
un serveur lent.

`hashFiles` empreinte des fichiers entiers : on ne peut pas lui demander de ne
surveiller qu'une partie d'un fichier. La seule réponse est donc de couper —
comme le projet l'a déjà fait pour `legi.py` et `textes.py`, qui ont chacun
leur cache et leur clé.

**La règle pour savoir où écrire une règle nouvelle :**

- elle décide de ce qui **entre dans la base** → `extraction.py` ;
- elle décide de ce qui **sort à l'écran** → ici.

Ce fichier peut importer `extraction` ; l'inverse est interdit, sans quoi la
coupure ne vaudrait plus rien.
"""
from __future__ import annotations

import re

from extraction import (CADUC, EN_COURS, NON_ADOPTE, PROMULGUE, REJETE, RETIRE)

# Les étapes **propres au Sénat**, telles que la source les nomme.
#
# **On ne les aligne pas sur les six étapes de l'Assemblée**, et c'est voulu :
# les deux chambres ne découpent pas le parcours pareil, et les faire
# correspondre reviendrait à inventer un découpage que personne ne publie.
#
# Le code d'une étape au Sénat porte sa lecture en préfixe — `SN1`, `SN2`,
# `SNNLEC` — puis son moment : `SN1-COM-FOND-RAPPORT`. La lecture s'affiche à
# part, sur la carte ; ce sont les moments qui font les colonnes, sans quoi on
# aurait quinze colonnes presque toutes vides.
#
# Mesuré le 2026-10-04 sur les 731 textes passés au Sénat : 494 en sont au
# renvoi en commission, 191 à la décision, 20 au rapport, 1 au dépôt.
ETAPES_SENAT = (
    ("depot", "Déposé au Sénat",
     "Le texte est arrivé au Sénat. Rien n'y a encore été examiné."),
    ("commission", "Renvoyé en commission",
     "Une commission du Sénat en est saisie. C'est de loin le cas le plus "
     "fréquent : la plupart des textes attendent là."),
    ("rapport", "Rapport déposé",
     "La commission a rendu son rapport. Le texte peut aller en séance."),
    ("seance", "En séance publique",
     "Le Sénat en débat en séance."),
    ("decision", "Décidé",
     "Le Sénat s'est prononcé. Ce qui arrive ensuite — navette, commission "
     "mixte paritaire, promulgation — ne lui appartient plus."),
)
# Les préfixes de lecture au Sénat. Ils sont la seule chose qui distingue une
# étape du Sénat d'une étape de l'Assemblée : les deux chambres emploient les
# mêmes suffixes (`-DEPOT`, `-DEBATS-DEC`…).
LECTURES_SENAT = re.compile(r"^SN(\d+|NLEC|LECDEF)$")
# Du code de la source au moment qu'il désigne. La clé est ce qui suit la
# lecture ; la lecture elle-même (`SN1`, `SN2`, `SNNLEC`) ne décide de rien.
MOMENTS_SENAT = {
    "DEPOT": "depot",
    "COM-FOND-SAISIE": "commission",
    "COM-FOND-RAPPORT": "rapport",
    "DEBATS-SEANCE": "seance",
    "DEBATS-DEC": "decision",
}
def moment_au_senat(code: str | None) -> str | None:
    """Le moment du parcours sénatorial que ce code désigne, ou rien.

    « SN1-COM-FOND-RAPPORT » → « rapport ». Un code que la table ne connaît
    pas — une procédure accélérée, une saisine pour avis — ne rend rien : il
    n'a pas de colonne, et en inventer une serait pire que de l'ignorer.

    **Le préfixe doit être celui d'une lecture au Sénat**, et c'est vérifié :
    les deux chambres emploient les mêmes suffixes, si bien que « AN1-DEPOT »
    rendait « depot » et aurait rangé dans le fil du Sénat un texte qui n'y
    est jamais allé. Préfixes relevés le 2026-10-04 : `SN1` (2 088 étapes),
    `SN2` (33) et `SNNLEC` (22).
    """
    lecture, _, reste = (code or "").partition("-")
    if not reste or not LECTURES_SENAT.match(lecture):
        return None
    return MOMENTS_SENAT.get(reste)
# Comment le dire à l'écran. **Aucune de ces phrases ne prétend qu'un texte
# est fini pour de bon** : la source ne le dit pas, nous non plus. Un texte
# rejeté ou non adopté peut être redéposé, et rien dans les données ne permet
# de l'exclure.
FINS = {
    PROMULGUE: ("Promulguée",
                "Le parcours est terminé : le texte est devenu une loi, signée et "
                "publiée au Journal officiel. C'est à partir de là qu'elle s'applique."),
    REJETE: ("Rejeté",
             "La dernière décision connue sur ce texte est un rejet. Cela ne veut pas "
             "dire qu'il ne reviendra jamais : un texte rejeté peut être redéposé, et "
             "la source ne se prononce pas là-dessus."),
    NON_ADOPTE: ("Non adopté",
                 "Le Sénat indique que ce texte n'a pas été adopté. C'est son propre "
                 "mot. Un texte non adopté peut être redéposé ; rien dans les données "
                 "ne dit s'il le sera."),
    CADUC: ("Caduc",
            "Le Sénat indique que ce texte est caduc : il n'a pas abouti avant la fin "
            "de la période où il pouvait être examiné. Pour repartir, il devrait être "
            "déposé à nouveau."),
    RETIRE: ("Retiré",
             "Le texte a été retiré par celui qui l'avait déposé. Ce n'est ni un rejet "
             "ni un échec de vote : son auteur a choisi de l'enlever."),
    EN_COURS: ("En cours d'examen",
               "Le texte est quelque part entre son dépôt et sa promulgation. Rien ne "
               "dit qu'il ira au bout : la plupart s'arrêtent en route."),
}
# Ce qui fait un événement de calendrier, et ce qui n'en fait pas. Un dépôt, un
# renvoi en commission, une nomination de rapporteur sont des actes
# administratifs : ils n'ont ni heure, ni public, ni rien à suivre en direct.
# Restent les moments où le Parlement se réunit et décide.
GENRES = (
    ("DEBATS-DEC", "decision"),      # « le texte est adopté », « rejeté »
    ("DEBATS-SEANCE", "seance"),     # la discussion en séance publique
    ("-REUNION", "commission"),      # la commission se réunit et amende
    ("PROM-PUB", "promulgation"),    # le Président signe : c'est une loi
)
# Les portées de vote qui méritent une ligne au calendrier. Sur 2 748 votes
# rattachés à un texte, **2 260 portent sur un amendement** (mesuré le
# 2026-09-02) : les afficher noierait le calendrier sous des scrutins de
# détail, alors que la séance du jour est déjà là pour les porter.
VOTES_AU_CALENDRIER = frozenset({"ensemble", "motion"})
def genre_d_evenement(code: str) -> str | None:
    """Ce qu'une étape est, pour un calendrier — ou `None` si elle n'y a pas sa place.

    Le code d'une étape porte la chambre et la lecture en préfixe
    (`AN1-DEBATS-SEANCE`, `SN2-DEBATS-DEC`) : on reconnaît donc la fin du code,
    pas le code entier.
    """
    for motif, genre in GENRES:
        if code and motif in code:
            return genre
    return None
