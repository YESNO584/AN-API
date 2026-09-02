#!/usr/bin/env python3
"""Écrit les données de la base en fichiers tout prêts, à publier tels quels.

Pourquoi des fichiers plutôt qu'un serveur : les données ne changent qu'une
fois par jour et personne ne les modifie. Il n'y a donc rien à calculer en
direct. Des fichiers publiés quelque part suffisent — pas de machine à louer,
à surveiller ni à mettre à jour, et l'application démarre plus vite parce
qu'elle lit un fichier au lieu d'interroger un serveur.

Ce que ça produit (environ 2,5 Mo au total, 120 Ko pour la liste une fois
compressée) :

    public/etat.json              d'où viennent les données et de quand
    public/etapes.json            les six étapes du parcours, et leurs comptes
    public/textes.json            les textes en cours — le fichier principal
    public/promulgues.json        les lois déjà promulguées
    public/textes/<uid>.json      un fichier par texte, avec tout son parcours

Usage :
    ./publier.py                  # écrit dans public/
    ./publier.py --vers dossier
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import shutil
import sqlite3
import sys

import extraction
import legi

RACINE = pathlib.Path(__file__).resolve().parent
BASE = RACINE / "parlement.db"
BASE_LEGI = RACINE / "legi.db"
SORTIE = RACINE / "public"
MAQUETTE = RACINE.parent / "maquette" / "feed.html"

# Ce qu'une loi fait à un article, dit en clair. La clé est le mot de LEGI ;
# rien n'est reformulé, seulement traduit une fois pour toutes.
ACTIONS = {"MODIFIE": "modifié", "CREE": "créé", "ABROGE": "abrogé",
           "TRANSFERE": "transféré", "DEPLACE": "déplacé"}
# Du plus parlant au moins parlant, quand une loi en fait plusieurs au même
# article : ce que le lecteur retient, c'est que le contenu a changé.
PRIORITE = ("MODIFIE", "CREE", "ABROGE", "TRANSFERE", "DEPLACE")

# Les types de dossier qui ne peuvent aboutir à aucune loi, et ce qu'ils sont
# en clair. Ils ne sont plus écartés : ils ont leur propre onglet, où ces
# libellés servent de colonnes. L'ordre est celui de l'affichage.
TRAVAUX = (
    ("Commission d'enquête", "Une enquête aux pouvoirs renforcés, sur un sujet précis"),
    ("Mission d'information", "Un groupe de députés étudie un sujet"),
    ("Rapport d'information sans mission", "Une commission publie ses conclusions"),
    ("Résolution Article 34-1", "Une prise de position, prévue par la Constitution"),
    ("Résolution", "L'Assemblée prend position, ou modifie son règlement intérieur"),
    ("Engagement de la responsabilité gouvernementale",
     "Motion de censure, question de confiance"),
    ("Responsabilité pénale du président de la république", "Procédure de destitution"),
    ("Pétitions", "Une demande adressée à l'Assemblée par des citoyens"),
    ("Allocution du Président de l'Assemblée nationale", "Un discours"),
)

# Ce que la liste embarque pour chaque texte. Volontairement court : elle est
# chargée en entier par l'application, qui filtre et cherche ensuite toute
# seule, hors connexion. Le reste est dans le fichier de détail.
CHAMPS_LISTE = ("uid", "titre", "type", "chambre", "chambre_initiale", "etape",
                "statut", "etat_senat", "date_dernier_mouvement", "lecture",
                "dernier_acte", "conclusion", "prochaine_date", "prochaine_quoi",
                "url_an", "url_senat")

# Les textes qui se sont arrêtés en chemin. Regroupés dans un fichier à part :
# ils ne sont ni en cours, ni devenus des lois, et les laisser parmi les
# vivants faisait afficher comme « en cours » 29 textes que le Sénat donne
# pour finis.
ARRETES = (extraction.REJETE, extraction.NON_ADOPTE,
           extraction.CADUC, extraction.RETIRE)

# Au plus tant d'amendements détaillés par texte. Le record de la législature
# est de 19 510 sur un seul dossier : tout publier ferait un fichier de
# plusieurs dizaines de méga-octets pour un écran de téléphone. Les autres
# restent comptés, et le compte est affiché.
AMENDEMENTS_MAX = 150

# L'exposé sommaire — l'argumentaire de l'auteur — pèse à lui seul les trois
# quarts d'un fichier d'amendements. On en publie le début : de quoi
# comprendre l'intention, sans faire porter 200 Ko à un téléphone pour un
# seul texte. Le dispositif, lui, est toujours complet : c'est la partie qui
# dit ce que l'amendement fait.
EXPOSE_MAX = 400

CHAMPS_VOTE = ("uid", "date", "type", "portee", "objet", "sort", "annonce",
               "demandeur", "votants", "requis", "pour", "contre", "abstentions",
               "non_votants")


def resume_votes(cx: sqlite3.Connection) -> dict[str, dict]:
    """Par texte, de quoi afficher une carte sans ouvrir son fichier de détail.

    On ne retient que le vote **sur l'ensemble du texte** le plus récent :
    c'est celui qui décide si le texte poursuit son chemin. Les 7 218 votes
    sur des amendements comptent, mais ne se résument pas — ils sont dans le
    fichier de détail.
    """
    resume: dict[str, dict] = {}
    for l in cx.execute(
            "SELECT dossier_uid, COUNT(*) n,"
            " SUM(portee = 'ensemble') ensembles,"
            " MAX(date) derniere"
            " FROM vote WHERE dossier_uid IS NOT NULL GROUP BY dossier_uid"):
        resume[l["dossier_uid"]] = {"votes": l["n"], "votesEnsemble": l["ensembles"],
                                    "dernierVote": l["derniere"], "voteEnsemble": None}
    for l in cx.execute(
            "SELECT dossier_uid, date, sort, pour, contre, abstentions, objet"
            " FROM vote WHERE dossier_uid IS NOT NULL AND portee = 'ensemble'"
            " ORDER BY date"):
        resume[l["dossier_uid"]]["voteEnsemble"] = {
            "date": l["date"], "sort": l["sort"], "pour": l["pour"],
            "contre": l["contre"], "abstentions": l["abstentions"],
            "objet": l["objet"],
        }
    return resume


def votes_du_texte(cx: sqlite3.Connection, uid: str) -> list[dict]:
    votes = []
    for v in cx.execute(
            f"SELECT {', '.join(CHAMPS_VOTE)} FROM vote WHERE dossier_uid = ?"
            " ORDER BY date DESC, numero DESC", (uid,)):
        # Rangés comme dans l'hémicycle, de la gauche à la droite. Un groupe
        # que la source ne nomme plus — un groupe dissous — passe en fin de
        # liste plutôt que de disparaître.
        groupes = [dict(g) for g in cx.execute(
            "SELECT vg.sigle, vg.nom, vg.membres, vg.position, vg.pour, vg.contre,"
            " vg.abstentions, vg.non_votants, g.rang, g.couleur"
            " FROM vote_groupe vg LEFT JOIN groupe g ON g.ref = vg.organe_ref"
            " WHERE vg.vote_uid = ?"
            " ORDER BY g.rang IS NULL, g.rang, vg.membres DESC", (v["uid"],))]
        votes.append({**dict(v), "groupes": groupes})
    return votes


def signataires(cx: sqlite3.Connection, refs: list[str]) -> list[dict]:
    """Les députés désignés, avec leur photo et la couleur de leur groupe."""
    gens = []
    for ref in refs:
        l = cx.execute(
            "SELECT a.ref, a.civilite, a.prenom, a.nom, a.photo, g.sigle, g.nom nom_groupe,"
            " g.couleur FROM acteur a LEFT JOIN groupe g ON g.ref = a.groupe_ref"
            " WHERE a.ref = ?", (ref,)).fetchone()
        if l:
            gens.append(dict(l))
    return gens


def amendements_du_texte(cx: sqlite3.Connection, uid: str) -> dict:
    """Les amendements d'un texte, plafonnés, avec leur compte réel."""
    total = cx.execute(
        "SELECT COUNT(*) n FROM amendement WHERE dossier_uid = ?", (uid,)).fetchone()["n"]
    if not total:
        return {"total": 0, "publies": 0, "sorts": {}, "amendements": []}

    sorts = {l["sort"] or "(sans suite)": l["n"] for l in cx.execute(
        "SELECT sort, COUNT(*) n FROM amendement WHERE dossier_uid = ?"
        " GROUP BY sort ORDER BY n DESC", (uid,))}

    # Les adoptés d'abord : ce sont eux qui ont changé le texte.
    lignes = cx.execute(
        "SELECT a.uid, a.numero, a.article, a.sort, a.date_depot, a.dispositif,"
        " a.expose, a.morceaux, a.type_auteur,"
        " ac.civilite, ac.prenom, ac.nom, ac.photo, g.sigle, g.couleur"
        " FROM amendement a"
        " LEFT JOIN acteur ac ON ac.ref = a.auteur_ref"
        " LEFT JOIN groupe g ON g.ref = a.groupe_ref"
        " WHERE a.dossier_uid = ? AND a.dispositif != ''"
        " ORDER BY (a.sort = 'Adopté') DESC, a.article, a.ordre"
        " LIMIT ?", (uid, AMENDEMENTS_MAX)).fetchall()

    amendements = []
    for l in lignes:
        a = dict(l)
        a["morceaux"] = json.loads(a["morceaux"] or "[]")
        expose = a.get("expose") or ""
        a["exposeTronque"] = len(expose) > EXPOSE_MAX
        if a["exposeTronque"]:
            a["expose"] = expose[:EXPOSE_MAX].rsplit(" ", 1)[0] + "…"
        amendements.append(a)
    return {"total": total, "publies": len(amendements), "sorts": sorts,
            "amendements": amendements}


def ouvrir_legi() -> sqlite3.Connection | None:
    """La base du droit consolidé, si elle a été construite.

    Elle est facultative : sans elle, tout le reste se publie normalement et
    l'application n'affiche simplement pas ce que les lois changent. Une passe
    de quinze minutes ne doit pas pouvoir empêcher la publication du matin.
    """
    if not BASE_LEGI.exists():
        return None
    cx = sqlite3.connect(f"file:{BASE_LEGI}?mode=ro", uri=True, timeout=30)
    cx.row_factory = sqlite3.Row
    return cx


def changements_par_loi(legi_cx: sqlite3.Connection | None) -> dict[str, dict]:
    """Pour chaque loi, de quoi remplir sa carte : combien d'articles, et quand.

    « Quand » est la question qui manquait : une loi promulguée peut ne
    s'appliquer que plus tard, et parfois en plusieurs fois. On publie donc les
    dates d'entrée en vigueur telles quelles, sans les interpréter.
    """
    if legi_cx is None:
        return {}
    resume: dict[str, dict] = {}
    # Le total compte les **articles**, pas les liens : une même loi peut à la
    # fois modifier et déplacer un article, ce qui ferait deux liens et un seul
    # article. « Voir les 7 articles » doit dire vrai.
    for ligne in legi_cx.execute(
            "SELECT loi, COUNT(DISTINCT redaction_id) n FROM changement GROUP BY loi"):
        resume[ligne["loi"]] = {"total": ligne["n"], "actions": {}, "dates": []}
    for ligne in legi_cx.execute(
            "SELECT loi, quoi, COUNT(DISTINCT redaction_id) n"
            " FROM changement GROUP BY loi, quoi"):
        resume[ligne["loi"]]["actions"][ligne["quoi"]] = ligne["n"]
    dates: dict[str, dict[str, int]] = {}
    for ligne in legi_cx.execute(
            "SELECT c.loi, r.debut, COUNT(DISTINCT c.redaction_id) n"
            " FROM changement c JOIN redaction r ON r.id = c.redaction_id"
            " WHERE r.debut IS NOT NULL AND r.debut != ''"
            " GROUP BY c.loi, r.debut"):
        dates.setdefault(ligne["loi"], {})[ligne["debut"]] = ligne["n"]
    for numero, par_date in dates.items():
        resume[numero]["dates"] = [{"date": d, "articles": n}
                                   for d, n in sorted(par_date.items())]
    return resume


def articles_de_la_loi(legi_cx: sqlite3.Connection, numero: str) -> list[dict]:
    """Les articles qu'une loi a changés, groupés par code, avec la part modifiée.

    La liste ne porte aucun texte : elle sert à choisir. Le texte entier et sa
    comparaison sont dans un fichier par article, chargé au clic. Sans cette
    séparation, la loi de finances pour 2025 — 574 articles — ferait un fichier
    de plusieurs méga-octets pour un écran de téléphone.
    """
    groupes: dict[str, list] = {}
    for ligne in legi_cx.execute(
            "SELECT r.id, r.numero, r.ou, r.debut, r.texte, r.precedent,"
            " GROUP_CONCAT(DISTINCT c.quoi) actions,"
            " (SELECT texte FROM redaction WHERE id = r.precedent) avant"
            " FROM changement c JOIN redaction r ON r.id = c.redaction_id"
            " WHERE c.loi = ? GROUP BY r.id ORDER BY r.ou, r.numero", (numero,)):
        avant, apres = ligne["avant"], ligne["texte"] or ""
        # Une loi peut faire deux choses au même article — le modifier et le
        # déplacer. Un seul mot tient sur la pastille : on garde le plus
        # parlant, et l'ordre de PRIORITE dit lequel.
        actions = (ligne["actions"] or "").split(",")
        quoi = min(actions, key=lambda a: PRIORITE.index(a) if a in PRIORITE
                                          else len(PRIORITE))
        groupes.setdefault(ligne["ou"] or "Textes non codifiés", []).append({
            "id": ligne["id"], "numero": ligne["numero"], "quoi": quoi,
            "action": ACTIONS.get(quoi, quoi),
            "actions": [ACTIONS.get(a, a) for a in actions] if len(actions) > 1 else None,
            "debut": ligne["debut"],
            "mots": len(apres.split()),
            "commun": legi.part_commune(avant, apres) if avant else None,
            "avant": legi.etat_du_precedent(ligne["precedent"], ligne["avant"]),
        })
    return [{"ou": ou, "articles": articles} for ou, articles in groupes.items()]


def article_compare(legi_cx: sqlite3.Connection, identifiant: str) -> dict:
    """Un article : son texte entier, découpé en morceaux égaux, retirés, ajoutés."""
    ligne = legi_cx.execute(
        "SELECT r.*, (SELECT texte FROM redaction WHERE id = r.precedent) avant"
        " FROM redaction r WHERE r.id = ?", (identifiant,)).fetchone()
    avant, apres = ligne["avant"], ligne["texte"] or ""
    return {
        "id": ligne["id"], "numero": ligne["numero"], "ou": ligne["ou"],
        "debut": ligne["debut"], "fin": ligne["fin"], "etat": ligne["etat"],
        "nota": ligne["nota"] or None,
        "commun": legi.part_commune(avant, apres) if avant else None,
        "morceaux": legi.morceaux(avant, apres) if avant
                    else [{"role": "ajoute" if not ligne["precedent"] else "egal",
                           "texte": apres}],
        "avant": legi.etat_du_precedent(ligne["precedent"], ligne["avant"]),
        "source": legi.url_legifrance(ligne["id"]),
    }


def ecrire(chemin: pathlib.Path, contenu, brut: bytes | None = None) -> int:
    """Écrit du JSON, ou des octets tels quels si `brut` est fourni."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    if brut is None:
        brut = json.dumps(contenu, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    chemin.write_bytes(brut)
    return len(brut)


def publier(cx: sqlite3.Connection, sortie: pathlib.Path) -> dict[str, int]:
    # On repart d'un dossier vide : un texte promulgué hier ne doit pas rester
    # dans la liste des textes en cours d'avant-hier.
    if sortie.exists():
        shutil.rmtree(sortie)
    sortie.mkdir(parents=True)

    tailles: dict[str, int] = {}
    genere_le = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    votes = resume_votes(cx)
    legi_cx = ouvrir_legi()
    change = changements_par_loi(legi_cx)
    compte_amendements = {l["dossier_uid"]: l["n"] for l in cx.execute(
        "SELECT dossier_uid, COUNT(*) n FROM amendement GROUP BY dossier_uid")}

    comptes = {l["statut"]: l["n"] for l in cx.execute(
        "SELECT statut, COUNT(*) n FROM dossier WHERE est_loi = 1 GROUP BY statut")}
    par_etape = {l["etape"]: l["n"] for l in cx.execute(
        "SELECT etape, COUNT(*) n FROM dossier"
        " WHERE statut='en_cours' AND est_loi=1 AND etape IS NOT NULL GROUP BY etape")}

    # « partiel » : le rangement a réussi, mais une source facultative a
    # manqué. C'est un chargement valable, et la page doit pouvoir le dire.
    chargement = cx.execute(
        "SELECT * FROM journal WHERE statut IN ('succes', 'partiel')"
        " ORDER BY id DESC LIMIT 1").fetchone()

    tailles["etat.json"] = ecrire(sortie / "etat.json", {
        "genereLe": genere_le,
        "source": extraction.URL_ARCHIVE,
        "licence": "Licence Ouverte (Etalab)",
        "legislature": extraction.LEGISLATURE,
        "dernierChargement": dict(chargement) if chargement else None,
        "dossiers": cx.execute("SELECT COUNT(*) n FROM dossier").fetchone()["n"],
        "etapesEnregistrees": cx.execute("SELECT COUNT(*) n FROM etape").fetchone()["n"],
        # Ce que la page doit savoir taire plutôt que d'afficher un zéro faux :
        # une rubrique dont la source n'est pas arrivée ce matin.
        "amendementsIndisponibles":
            cx.execute("SELECT COUNT(*) n FROM amendement").fetchone()["n"] == 0,
        "textesEnCours": comptes.get(extraction.EN_COURS, 0),
        "promulgues": comptes.get(extraction.PROMULGUE, 0),
        "scrutins": cx.execute("SELECT COUNT(*) n FROM vote").fetchone()["n"],
        "textesAvecVote": cx.execute(
            "SELECT COUNT(DISTINCT d.uid) n FROM dossier d JOIN vote v ON v.dossier_uid = d.uid"
            " WHERE d.est_loi = 1").fetchone()["n"],
        "arretes": sum(comptes.get(x, 0) for x in ARRETES),
        "travaux": cx.execute(
            "SELECT COUNT(*) n FROM dossier WHERE est_loi = 0").fetchone()["n"],
        # Le droit consolidé est facultatif : sans lui, tout le reste se publie
        # et l'application n'affiche simplement pas ce que les lois changent.
        "droitConsolideIndisponible": legi_cx is None,
        "loisAvecChangements": len(change),
        "articlesChanges": sum(c["total"] for c in change.values()),
        "amendements": cx.execute("SELECT COUNT(*) n FROM amendement").fetchone()["n"],
        "textesAvecAmendements": cx.execute(
            "SELECT COUNT(DISTINCT dossier_uid) n FROM amendement").fetchone()["n"],
        "amendementsMaxParTexte": AMENDEMENTS_MAX,
        "issues": {cle: {"nom": nom, "quoi": quoi, "textes": comptes.get(cle, 0)}
                   for cle, (nom, quoi) in extraction.FINS.items()},
        "fichiers": ["etapes.json", "groupes.json", "textes.json", "promulgues.json",
                     "arretes.json", "travaux.json", "textes/<uid>.json",
                     "amendements/<uid>.json", "changements/<uid>.json",
                     "changements/<uid>/<LEGIARTI>.json"],
    })

    # Les groupes, rangés de la gauche à la droite de l'hémicycle. L'ordre est
    # mesuré sur les numéros de siège publiés ; la couleur est une convention
    # d'affichage, que la page reprend telle quelle plutôt que d'en inventer.
    tailles["groupes.json"] = ecrire(sortie / "groupes.json", {
        "genereLe": genere_le,
        "ordre": "de la gauche à la droite de l'hémicycle, d'après les numéros"
                 " de siège publiés par l'Assemblée",
        "couleurs": "convention d'affichage — l'open data n'en publie aucune",
        "groupes": [dict(g) for g in cx.execute(
            "SELECT ref, sigle, nom, rang, siege_median, couleur"
            " FROM groupe ORDER BY rang")],
    })

    tailles["etapes.json"] = ecrire(sortie / "etapes.json", {
        "genereLe": genere_le,
        "etapes": [{"n": n, "nom": nom, "quoi": quoi, "textesEnCours": par_etape.get(n, 0)}
                   for n, nom, quoi in extraction.ETAPES],
        # Les lois promulguées ne sont pas une septième étape : c'est l'après.
        # Mais un lecteur qui compte les textes doit les retrouver quelque part.
        "promulguees": comptes.get(extraction.PROMULGUE, 0),
    })

    for nom_fichier, statuts in (("textes.json", (extraction.EN_COURS,)),
                                 ("promulgues.json", (extraction.PROMULGUE,)),
                                 ("arretes.json", ARRETES)):
        # Les plus avancés d'abord : un texte près d'être promulgué intéresse
        # plus qu'une proposition déposée et jamais examinée — et celles-ci
        # sont l'immense majorité.
        trous = ",".join("?" * len(statuts))
        lignes = cx.execute(
            # Le groupe de l'auteur voyage avec le texte : la carte du fil le
            # montre en couleur, et l'ouvrir pour le savoir serait absurde.
            f"SELECT {', '.join('d.' + c for c in CHAMPS_LISTE)},"
            " d.loi_numero, d.loi_date, d.loi_url_jo,"
            " g.sigle auteur_sigle, g.nom auteur_groupe, g.couleur auteur_couleur"
            " FROM dossier d"
            " LEFT JOIN acteur a ON a.ref = d.auteur_ref"
            " LEFT JOIN groupe g ON g.ref = a.groupe_ref"
            f" WHERE d.statut IN ({trous}) AND d.est_loi = 1"
            " ORDER BY d.etape DESC, d.date_dernier_mouvement DESC, d.uid",
            statuts).fetchall()
        textes = []
        for l in lignes:
            texte = {c: l[c] for c in CHAMPS_LISTE}
            for c in ("auteur_sigle", "auteur_groupe", "auteur_couleur"):
                if l[c]:
                    texte[c] = l[c]
            texte.update(votes.get(l["uid"], {"votes": 0, "votesEnsemble": 0,
                                              "dernierVote": None, "voteEnsemble": None}))
            texte["amendements"] = compte_amendements.get(l["uid"], 0)
            if l["statut"] == extraction.PROMULGUE:
                texte.update(loiNumero=l["loi_numero"], loiDate=l["loi_date"],
                             loiUrlJO=l["loi_url_jo"])
                # Ce que la loi change au droit, et quand elle s'applique : la
                # carte le dit sans qu'on ait à l'ouvrir. Une loi absente de
                # `change` ne modifie aucun article — ce n'est pas une donnée
                # manquante, c'est un fait, et la carte le dira.
                if legi_cx is not None:
                    texte["change"] = change.get(l["loi_numero"])
            textes.append(texte)
        tailles[nom_fichier] = ecrire(sortie / nom_fichier,
                                      {"genereLe": genere_le, "total": len(textes),
                                       "textes": textes})

    # Le détail, un fichier par texte. Seulement pour ceux que les listes
    # citent : publier les 708 dossiers qui ne font pas de loi n'aurait
    # aucun lecteur.
    details, amendements = 0, 0
    for l in cx.execute(
            "SELECT * FROM dossier WHERE est_loi = 1 AND statut != ?",
            (extraction.SANS_ACTE,)):
        parcours = [{**dict(e), "details": json.loads(e["details"] or "{}")}
                    for e in cx.execute(
            "SELECT code, lecture, libelle, chambre, date, numero, conclusion,"
            " future, precision, details"
            " FROM etape WHERE dossier_uid = ? ORDER BY date, rang", (l["uid"],))]
        cosign = json.loads(l["cosignataires"] or "[]")
        details += ecrire(sortie / "textes" / f'{l["uid"]}.json', {
            **dict(l),
            "cosignataires": signataires(cx, cosign[:40]),
            "cosignatairesTotal": len(cosign),
            "auteur": (signataires(cx, [l["auteur_ref"]]) or [None])[0],
            "parcours": parcours,
            "votes": votes_du_texte(cx, l["uid"]),
        })

        # Les amendements dans un fichier séparé : la fiche s'ouvre sans les
        # attendre, et ils ne sont chargés que si on les demande.
        amdts = amendements_du_texte(cx, l["uid"])
        if amdts["total"]:
            amendements += ecrire(sortie / "amendements" / f'{l["uid"]}.json',
                                  {"genereLe": genere_le, **amdts})
    tailles["textes/*.json"] = details
    if amendements:
        tailles["amendements/*.json"] = amendements

    # Les travaux de l'Assemblée : les 708 dossiers qui n'aboutissent à aucune
    # loi. Ils étaient écartés ; ils ont maintenant leur onglet, avec une
    # colonne par catégorie. Rien n'est écarté.
    rangs = {nom: rang for rang, (nom, _) in enumerate(TRAVAUX)}
    travaux = []
    for l in cx.execute(
            "SELECT uid, titre, type, chambre, date_dernier_mouvement, lecture,"
            " dernier_acte, conclusion, statut, url_an, url_senat"
            " FROM dossier WHERE est_loi = 0"
            " ORDER BY date_dernier_mouvement DESC, uid"):
        travaux.append(dict(l))
    tailles["travaux.json"] = ecrire(sortie / "travaux.json", {
        "genereLe": genere_le, "total": len(travaux),
        # Les catégories servent de colonnes. On ne publie que celles qui ont
        # au moins un dossier : une colonne vide n'apprend rien.
        "categories": [{"n": rangs[nom], "nom": nom, "quoi": quoi,
                        "dossiers": sum(1 for t in travaux if t["type"] == nom)}
                       for nom, quoi in TRAVAUX
                       if any(t["type"] == nom for t in travaux)],
        "travaux": travaux,
    })

    # Ce que chaque loi change au droit. Deux niveaux : la liste des articles,
    # qui ne porte aucun texte et sert à choisir ; puis un fichier par article,
    # chargé au clic. Sans cette séparation, la loi de finances pour 2025 — 574
    # articles — ferait plusieurs méga-octets pour un seul écran.
    if legi_cx is not None:
        listes, fiches, lois_couvertes = 0, 0, 0
        for l in cx.execute(
                "SELECT uid, loi_numero FROM dossier"
                " WHERE statut = ? AND loi_numero IS NOT NULL AND loi_numero != ''",
                (extraction.PROMULGUE,)):
            groupes = articles_de_la_loi(legi_cx, l["loi_numero"])
            if not groupes:
                continue
            lois_couvertes += 1
            listes += ecrire(sortie / "changements" / f'{l["uid"]}.json', {
                "genereLe": genere_le, "loi": l["loi_numero"],
                **change.get(l["loi_numero"], {}),
                "groupes": groupes,
            })
            for groupe in groupes:
                for article in groupe["articles"]:
                    fiches += ecrire(
                        sortie / "changements" / l["uid"] / f'{article["id"]}.json',
                        article_compare(legi_cx, article["id"]))
        if listes:
            tailles["changements/*.json"] = listes
            tailles["changements/<loi>/*.json"] = fiches
        if lois_couvertes != len(change):
            print(f"{len(change) - lois_couvertes} lois du droit consolidé sans "
                  "dossier correspondant : la base du Parlement est-elle à jour ?",
                  file=sys.stderr)

    # La maquette devient la page d'accueil. Publiée à côté des données, elle
    # les lit par une adresse relative — et l'adresse racine sert enfin à
    # quelque chose au lieu de renvoyer une erreur.
    if MAQUETTE.exists():
        tailles["index.html"] = ecrire(sortie / "index.html", None,
                                       MAQUETTE.read_bytes())
    else:
        print(f"Maquette introuvable ({MAQUETTE}) : pas de page d'accueil.",
              file=sys.stderr)

    # Refermer la base du droit consolidé : une connexion laissée ouverte
    # garde un verrou, et la récupération en cours se cassait dessus.
    if legi_cx is not None:
        legi_cx.close()

    # GitHub Pages ne sert pas les dossiers dont le nom commence par un
    # tiret bas, et ajoute sa propre mise en page aux fichiers Markdown.
    # `.nojekyll` désactive tout ça : on veut nos fichiers, tels quels.
    (sortie / ".nojekyll").write_text("", encoding="utf-8")
    return tailles


def main() -> int:
    analyseur = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analyseur.add_argument("--base", type=pathlib.Path, default=BASE)
    analyseur.add_argument("--vers", type=pathlib.Path, default=SORTIE)
    options = analyseur.parse_args()

    if not options.base.exists():
        print(f"Base introuvable : {options.base}\nLancer d'abord ./recuperer.py",
              file=sys.stderr)
        return 1

    cx = sqlite3.connect(f"file:{options.base}?mode=ro", uri=True)
    cx.row_factory = sqlite3.Row
    tailles = publier(cx, options.vers)
    cx.close()

    fichiers = sum(1 for _ in options.vers.rglob("*") if _.is_file())
    print(f"Écrit dans {options.vers} — {fichiers} fichiers", file=sys.stderr)
    for nom, octets in tailles.items():
        print(f"   {octets:>10,} o   {nom}", file=sys.stderr)
    print(f"   {sum(tailles.values()):>10,} o   au total", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
