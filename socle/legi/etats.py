"""Le vocabulaire que LEGI emploie pour l'état d'une rédaction et ce qu'une loi lui fait, et nos sentinelles de date. Une feuille : tout le paquet s'y réfère, elle ne dépend de rien.
"""
from __future__ import annotations



# Ce qu'une loi peut faire à un article. `CITATION` n'y est pas, exprès.
CHANGEMENTS = ("MODIFIE", "CREE", "ABROGE", "TRANSFERE", "DEPLACE")


# Ce qu'une loi **ajoute** : ses propres articles. `AJOUTE` est notre mot, pas
# celui de LEGI — et c'est précisément pourquoi on ratait ces articles.
#
# Un lien de changement est porté par l'article **visé**, à la forme verbale
# (`MODIFIE`, `CREE`) et avec le numéro de la loi qui a agi. Un article de loi
# n'en porte jamais : rien n'a agi sur lui, c'est lui qui agit. Ce qu'il porte,
# c'est la forme *nominale* (`MODIFICATION`, `CREATION`) sans numéro de texte.
# La source ne relie donc pas un article à sa propre loi par un lien : elle le
# **range dedans**, et cela se lit dans `CONTEXTE` (voir `loi_qui_porte`).
#
# Mesuré le 2026-09-03 sur deux archives quotidiennes : 642 articles hors code,
# **aucun** portant un lien de changement venant de sa propre loi.
AJOUTE = "AJOUTE"


# Ce que la source annonce d'un article de loi (balise `TYPE`) : `AUTONOME`,
# `PARTIELLEMENT_MODIF`, `ENTIEREMENT_MODIF`. Mesuré le 2026-09-03 sur 667
# articles de loi : 48 %, 16 % et 36 %.
#
# **Ce `TYPE` ne décide de rien, et s'y fier était une erreur — deux fois.**
# Un `PARTIELLEMENT_MODIF` peut n'être fait que de renvois (8 des 87 premiers
# articles retenus n'affichaient qu'une liste de références : article 82 de la
# loi 2025-127, article 44 de la loi 2026-725). Et un `ENTIEREMENT_MODIF` peut
# porter du droit bien réel : l'article 32 de la loi 2026-201 est annoncé comme
# n'amendant que d'autres textes, et 92 % de son contenu est une servitude au
# profit des jeux Olympiques d'hiver. Le seul juge est donc le **texte**, une
# fois les renvois retirés — voir `sans_les_renvois`.
#
# Il reste une chose que le `TYPE` sait et que le texte ne dit pas : qu'un
# article *fera* des renvois et rien d'autre. Utile pour les seuls articles
# dont la source n'a pas encore saisi le texte — les annoncer aujourd'hui pour
# les voir disparaître demain ne rendrait service à personne.
TYPE_SANS_TEXTE = "ENTIEREMENT_MODIF"


# La phrase par laquelle la source remplace un texte qu'elle n'a pas encore
# saisi. Voir `est_en_attente`.
EN_COURS = "en cours de traitement"


# LEGI marque la fin des rédactions en vigueur par une date sentinelle.
SANS_FIN = "2999-01-01"


# Et par une autre — le 22 février 2222 — les dates **non encore fixées** :
# la loi prévoit qu'un article entrera en vigueur ou sera abrogé, mais renvoie
# à un décret qui n'est pas paru. 73 changements sur 2 261 sont dans ce cas
# (mesuré le 2026-09-02), presque tous à l'état VIGUEUR_DIFF ou ABROGE_DIFF.
# C'est une information à dire, pas une date à afficher.
SANS_DATE = "2222-02-22"
