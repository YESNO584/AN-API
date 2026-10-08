"""Où sont les sources : les adresses de l'open data de l'Assemblée, celle du Sénat, la législature suivie.
"""
from __future__ import annotations



DEPOT = "https://data.assemblee-nationale.fr/static/openData/repository/17/"


URL_ARCHIVE = DEPOT + "loi/dossiers_legislatifs/Dossiers_Legislatifs.json.zip"


URL_SCRUTINS = DEPOT + "loi/scrutins/Scrutins.json.zip"


# Cette archive contient à la fois les groupes (organe/) et les députés
# (acteur/) : une seule source pour les deux.
URL_ORGANES = DEPOT + "amo/deputes_actifs_mandats_actifs_organes/AMO10_deputes_actifs_mandats_actifs_organes.json.zip"


URL_AMENDEMENTS = DEPOT + "loi/amendements_div_legis/Amendements.json.zip"


# L'agenda des réunions. Il ne sert qu'à une chose, mais elle est nécessaire :
# départager deux actes du même jour. Une commission qui se réunit à 9 h puis
# à 15 h, une séance publique qui est la « Deuxième » du jour — sans cette
# archive, les deux s'affichent à l'identique et passent pour un doublon.
URL_AGENDA = DEPOT + "vp/reunions/Agenda.json.zip"


# Les députés, sénateurs et ministres de la législature. `URL_ORGANES` ne
# connaît que les 577 députés en exercice : 716 textes de loi sur 2 151 ont
# donc un auteur que personne ne sait nommer — un ministre qui dépose un
# projet de loi, un sénateur qui dépose une proposition — et 3 109
# cosignataires restent anonymes (mesuré le 2026-09-01). Cette archive-ci les
# nomme : 715 des 716 auteurs, et la totalité des cosignataires.
URL_ACTEURS_LARGE = (DEPOT + "amo/deputes_senateurs_ministres_legislature/"
                     "AMO20_dep_sen_min_tous_mandats_et_organes.json.zip")


# Les photos des députés. Elles ne sont pas dans l'open data : ce sont des
# fichiers du site de l'Assemblée, dont l'adresse se déduit de l'identifiant.
# Testées le 2026-08-31 sur douze députés tirés au hasard — dix réponses, deux
# coupures réseau, aucune absente.
PHOTO_DEPUTE = "https://www2.assemblee-nationale.fr/static/tribun/17/photos/{}.jpg"


# Le Sénat, pour une seule raison : il dit ce que l'Assemblée ne dit pas —
# qu'un texte est « non adopté », « caduc » ou « retiré ». Sans lui, 29 textes
# finis restent affichés comme en cours (mesuré le 2026-08-31).
URL_SENAT = "https://data.senat.fr/data/dosleg/dossiers-legislatifs.csv"


LEGISLATURE = "17"


PREFIXE_DOSSIER_AN = "https://www.assemblee-nationale.fr/dyn/17/dossiers/"


# Le compte rendu de séance, mot pour mot. C'est la seule source du projet où
# un député explique un texte avec ses propres phrases — le reste (dossiers,
# scrutins, amendements) ne dit que des faits et des décomptes.
#
# **Rien n'est résumé, rien n'est reformulé.** Ce module recopie les prises de
# parole telles que l'Assemblée les publie, avec le nom de l'orateur et son
# groupe. Il ne cherche pas à savoir si un orateur annonce un vote, ni si son
# groupe l'a suivi : une phrase d'intention lue dans la mauvaise section
# produit une contrevérité à l'écran (constaté le 2026-09-02 sur l'UDR, qui a
# voté « pour » les soins palliatifs pendant que son orateur disait « contre »
# — il parlait de l'autre texte de la même séance).
URL_DEBATS = DEPOT + "vp/syceronbrut/syseron.xml.zip"


# Le XML des comptes rendus porte un espace de noms, et `ElementTree` en
# préfixe chaque balise.
NS_DEBATS = "{http://schemas.assemblee-nationale.fr/referentiel}"
