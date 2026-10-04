#!/usr/bin/env python3
"""Les règles de lecture des sources du Sénat.

Elles vivent ici et nulle part ailleurs, comme celles de l'Assemblée vivent
dans `extraction.py`. `socle/test_senat.py` les tient.

**Trois sources, trois formats, et deux pièges mesurés le 2026-10-04 :**

- `dosleg.zip` — un dump PostgreSQL, en **UTF-8**, qui porte les dossiers, les
  scrutins, les 1,66 million de votes nominatifs et les séances à venir ;
- les fichiers des sénateurs — des CSV en **latin-1** (le même éditeur ne
  déclare pas le même encodage d'un fichier à l'autre) ;
- les **pages de scrutins publics du site**, seul endroit où le Sénat relie un
  scrutin à un dossier. Aucun fichier d'open data ne le fait.
"""
from __future__ import annotations

import csv
import io
import pathlib
import re
import zipfile

# ---------------------------------------------------------------- les adresses

DONNEES = "https://data.senat.fr/data/"
URL_DOSLEG = DONNEES + "dosleg/dosleg.zip"
URL_SENATEURS = DONNEES + "senateurs/ODSEN_GENERAL.csv"
URL_HISTOGROUPES = DONNEES + "senateurs/ODSEN_HISTOGROUPES.csv"
# Une page par session parlementaire. Seule celle de la session en cours change.
URL_SCRUTINS = "https://www.senat.fr/scrutin-public/scr{annee}.html"

# ------------------------------------------------- lire un dump PostgreSQL

def lignes_du_dump(texte: io.TextIOBase, table: str):
    """Les lignes d'une table d'un dump, en dictionnaires.

    Le format est celui de `COPY … FROM stdin` : une ligne d'en-tête qui nomme
    les colonnes, puis des lignes séparées par des tabulations, closes par
    « \\. ». `\\N` est l'absence de valeur.
    """
    entete, dedans = None, False
    for ligne in texte:
        if not dedans and ligne.startswith(f"COPY {table} ("):
            entete = [c.strip().strip('"') for c in
                      ligne.split("(", 1)[1].rsplit(")", 1)[0].split(",")]
            dedans = True
            continue
        if dedans:
            if ligne.startswith("\\."):
                return
            champs = [None if c == "\\N" else c
                      for c in ligne.rstrip("\n").split("\t")]
            yield dict(zip(entete, champs))


def lire_dump(archive: pathlib.Path, table: str):
    """La même chose, depuis l'archive, sans la déplier sur le disque.

    Le dump pèse 126 Mo déplié pour 15 Mo compressés : on le lit en flux, une
    table à la fois.
    """
    with zipfile.ZipFile(archive) as z:
        nom = next(n for n in z.namelist() if n.endswith(".sql"))
        with z.open(nom) as brut:
            yield from lignes_du_dump(
                io.TextIOWrapper(brut, encoding="utf-8", errors="replace"), table)


def net(valeur: str | None) -> str | None:
    """Le dump remplit ses colonnes de caractères à largeur fixe."""
    return valeur.strip() if isinstance(valeur, str) else valeur


# ------------------------------------------- le pont avec nos propres textes

SIGNET = re.compile(r"/([a-z]{2,4}\d{2}-\d+|[a-z]+\d{4})\.html")


def signet_de(url: str | None) -> str | None:
    """« https://www.senat.fr/dossier-legislatif/pjl25-689.html » → « pjl25-689 ».

    C'est la clé de jointure entre les deux chambres, et elle est publiée des
    deux côtés. Deux formes existent : `pjl25-689` pour un texte ordinaire,
    `pjlf2026` pour un budget — la seconde n'a pas de tiret, et l'oublier perdait
    quatre textes de finances (mesuré le 2026-10-04).
    """
    m = SIGNET.search(url or "")
    return m.group(1) if m else None


# --------------------------------------------- les pages de scrutins publics

LIEN_SCRUTIN = re.compile(r"/?(\d{4})/scr\1-(\d+)\.html")
LIEN_DOSSIER = re.compile(r"/dossier-legislatif/([a-z0-9][\w-]*)\.html")


def scrutins_de_la_page(texte: str) -> dict[tuple[int, int], str | None]:
    """Quel dossier chaque scrutin de cette page concerne.

    **La lecture ne s'appuie sur aucune mise en page** : ni balise, ni classe,
    ni formulation — seulement sur les deux formes d'adresse du Sénat, qui sont
    son propre système d'adressage. Vérifié le 2026-10-04 : elle donne
    exactement le même résultat que la lecture qui suivait la mise en page,
    340 scrutins sur 340.

    La règle est simple : **chaque scrutin prend le dossier cité avant le
    scrutin suivant.** Un scrutin sans dossier — une déclaration du
    Gouvernement — rend `None`, et c'est juste.
    """
    jalons = sorted(
        [(m.start(), 0, (int(m.group(1)), int(m.group(2)))) for m in
         LIEN_SCRUTIN.finditer(texte)]
        + [(m.start(), 1, m.group(1)) for m in LIEN_DOSSIER.finditer(texte)])
    trouves: dict[tuple[int, int], str | None] = {}
    courant = None
    for _, quoi, valeur in jalons:
        if quoi == 0:
            courant = valeur
            trouves.setdefault(courant, None)
        elif courant is not None and trouves.get(courant) is None:
            trouves[courant] = valeur
    return trouves


# Ce qui doit alerter plutôt que de passer pour un résultat. Une archive qui
# manque se voit ; **une page qui a changé de forme, non** : elle arrive, elle
# pèse son poids, et la lecture en tire zéro. Sans ces seuils, le socle
# publierait « aucun vote au Sénat » sur tous les textes, ce qui serait faux.
#
# Mesurés sur 20 sessions, de 2006 à 2026 : 129 à 445 scrutins par page, et
# 97 à 100 % d'entre eux portent un lien de dossier.
PART_MINIMALE_AVEC_DOSSIER = 0.90

# Le groupe qu'on place à gauche pour orienter l'axe des votes. **C'est la
# seule chose de cet ordre qui ne soit pas mesurée**, et elle est assumée :
# la mesure range les groupes sur une ligne, elle ne dit pas lequel de ses
# deux bouts est la gauche. `CRC` est le code, périmé mais stable, du groupe
# Communiste Républicain Citoyen et Écologiste - Kanaky.
GROUPE_LE_PLUS_A_GAUCHE = "CRC"


def page_lisible(trouves: dict, attendus: int | None = None) -> str | None:
    """Ce qui cloche dans la lecture d'une page, ou rien si elle va bien.

    Rend la raison en clair, pour le journal : c'est elle qui dira, le jour où
    le Sénat refera sa page, qu'il s'agit d'une panne et non d'une session sans
    scrutin.
    """
    if not trouves:
        return "aucun scrutin lu sur la page"
    avec = sum(1 for v in trouves.values() if v)
    part = avec / len(trouves)
    if part < PART_MINIMALE_AVEC_DOSSIER:
        return (f"{avec} scrutins sur {len(trouves)} portent un dossier"
                f" ({part:.0%}, moins de {PART_MINIMALE_AVEC_DOSSIER:.0%})")
    if attendus is not None and len(trouves) < attendus:
        return f"{len(trouves)} scrutins lus, contre {attendus} la fois d'avant"
    return None


# ------------------------------------------------------- les sénateurs, en CSV

def lire_csv_senat(chemin: pathlib.Path) -> list[dict]:
    """Un fichier de sénateurs : **latin-1**, et des lignes de commentaire.

    Trois pièges, les trois mesurés le 2026-10-04 :

    - l'encodage est le **latin-1** ; lus en UTF-8, ces fichiers affichent
      `S?nateur` ;
    - ils commencent par des lignes `%` qui décrivent la requête SQL d'origine,
      et que le lecteur doit sauter, sans quoi l'en-tête est faux ;
    - **le séparateur n'est pas le même d'un fichier à l'autre du même
      éditeur** : les fichiers de sénateurs emploient la virgule, celui des
      dossiers législatifs le point-virgule. Le forcer à l'un ou à l'autre
      rendait une seule colonne portant toute la ligne — et aucune erreur.

    On prend donc celui qui découpe l'en-tête en le plus de colonnes : c'est
    une mesure, pas une devinette.
    """
    with chemin.open(encoding="latin-1", newline="") as f:
        lignes = [l for l in f if not l.startswith("%")]
    if not lignes:
        return []
    separateur = max((",", ";", "\t"),
                     key=lambda c: len(next(csv.reader([lignes[0]], delimiter=c))))
    return list(csv.DictReader(lignes, delimiter=separateur))


# ------------------------------- l'ordre des groupes, mesuré sur les votes

def rang_par_les_votes(positions: dict[str, dict[str, int]],
                       gauche: str | None = None) -> list[str]:
    """Les groupes rangés de la gauche à la droite, d'après leur façon de voter.

    **L'ordre ne peut pas se mesurer sur les sièges, et c'est mesuré.** À
    l'Assemblée, la médiane des numéros de siège range les groupes. Au Sénat,
    elle les range à l'envers du sens politique : la numérotation tourne rang
    par rang, le groupe change 152 fois quand on suit les sièges — contre 9
    pour un hémicycle rangé par blocs — et les Républicains occupent les sièges
    8 à 346. Aucun plan de salle n'est publié.

    On range donc les groupes sur ce qu'ils font : pour chaque scrutin, la part
    de « pour » de chaque groupe, puis la première composante de ces profils.
    Elle sépare nettement la gauche, le centre et la droite ; **elle ne
    départage pas les groupes d'un même bloc**, et l'écran doit le dire.

    **La mesure donne une ligne, pas un sens.** Mathématiquement, l'axe et son
    opposé décrivent aussi bien les données : rien dans les votes ne dit lequel
    des deux bouts est « la gauche ». Le sens est donc une **convention**, au
    même titre que les couleurs des groupes, et `gauche` la rend explicite :
    c'est le code d'un groupe qu'on place du côté gauche. Sans lui, l'ordre
    peut sortir inversé d'une publication à l'autre.

    `positions` : {sigle: {clé de scrutin: part de « pour », de 0 à 1}}.
    """
    sigles = sorted(positions)
    if len(sigles) < 2:
        return sigles
    scrutins = sorted(set().union(*(set(p) for p in positions.values())))
    # Centrer chaque scrutin : ce qui compte est l'écart entre groupes, pas le
    # fait qu'un texte soit consensuel.
    centre = {}
    for s in scrutins:
        valeurs = [positions[g][s] for g in sigles if s in positions[g]]
        centre[s] = sum(valeurs) / len(valeurs) if valeurs else 0.0
    profils = {g: [positions[g].get(s, centre[s]) - centre[s] for s in scrutins]
               for g in sigles}

    def norme(v):
        return sum(x * x for x in v) ** 0.5

    # Le départ est **le profil le plus marqué**, et non un vecteur alterné.
    # Un vecteur alterné peut être exactement orthogonal au signal — deux
    # groupes opposés pris avec des signes opposés s'annulent — et la méthode
    # rendait alors l'ordre alphabétique **sans rien dire**. Attrapé par un
    # test le 2026-10-04. Le profil d'un groupe, lui, est dans le signal par
    # construction.
    axe = max(profils.values(), key=norme)
    if not norme(axe):
        return sigles          # tous les groupes votent pareil : rien à ranger
    axe = [x / norme(axe) for x in axe]
    # La première composante, par la méthode des puissances : pas de
    # dépendance, et quelques dizaines d'itérations suffisent largement.
    poids = {g: 0.0 for g in sigles}
    for _ in range(200):
        poids = {g: sum(profils[g][i] * axe[i] for i in range(len(scrutins)))
                 for g in sigles}
        suivant = [sum(poids[g] * profils[g][i] for g in sigles)
                   for i in range(len(scrutins))]
        n = norme(suivant)
        if not n:
            return sigles
        axe = [x / n for x in suivant]
    ordre = sorted(sigles, key=lambda g: poids[g])
    # Le seul choix qui ne se mesure pas : de quel côté est la gauche.
    if gauche in poids and ordre.index(gauche) > (len(ordre) - 1) / 2:
        ordre.reverse()
    return ordre
