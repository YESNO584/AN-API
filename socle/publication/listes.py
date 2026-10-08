"""Les listes du fil — textes en cours, promulgués, arrêtés, travaux — et ce que chaque carte doit savoir sans ouvrir le texte.
"""
from __future__ import annotations

import sqlite3
import extraction
from publication.amendements import groupes_du_scrutin
from publication.commun import ecrire
from publication.contexte import Publication


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


def votes_du_texte(cx: sqlite3.Connection, uid: str,
                   debats: dict[str, dict] | None = None) -> list[dict]:
    """Les scrutins publics d'un texte, groupe par groupe.

    `debats` donne, par identifiant de scrutin, combien de monde a parlé de
    l'amendement voté. Il vient du rattachement **déjà résolu** par la fiche
    des amendements — pas d'un second rapprochement par numéro, qui
    confondrait deux lectures.
    """
    debats = debats or {}
    votes = []
    for v in cx.execute(
            f"SELECT {', '.join(CHAMPS_VOTE)} FROM vote WHERE dossier_uid = ?"
            " ORDER BY date DESC, numero DESC", (uid,)):
        vote = {**dict(v), "groupes": groupes_du_scrutin(cx, v["uid"])}
        if v["uid"] in debats:
            vote["debat"] = debats[v["uid"]]
        votes.append(vote)
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


def procedure_acceleree(cx: sqlite3.Connection, uid: str) -> dict | None:
    """Le jour où le gouvernement a engagé la procédure accélérée, s'il l'a fait.

    C'est un acte du parcours comme un autre — code `AN1-PROCACC` ou
    `SN1-PROCACC` — mais il ne se lit pas comme les autres : il **change la
    procédure entière**, en limitant le texte à une lecture par chambre avant
    la commission mixte paritaire. Le site de l'Assemblée en fait une bannière
    en tête de dossier ; nous le laissions au milieu de trente-sept étapes.
    Mesuré le 2026-09-19 : 158 textes de loi sur 2 218 la portent, jamais deux
    fois pour le même texte.
    """
    ligne = cx.execute(
        "SELECT date, chambre FROM etape WHERE dossier_uid = ? AND code LIKE '%PROCACC%'"
        " ORDER BY date LIMIT 1", (uid,)).fetchone()
    return {"date": ligne["date"], "chambre": ligne["chambre"]} if ligne else None


def ecrire_listes(p: Publication) -> None:
    """Les trois listes du fil, écrites après les fiches parce qu'elles en dépendent."""
    cx = p.cx
    sortie = p.sortie
    genere_le = p.genere_le
    tailles = p.tailles
    votes = p.votes
    legi_cx = p.legi_cx
    change = p.change
    themes = p.themes
    etape_senat = p.etape_senat
    compte_amendements = p.compte_amendements
    compte_paroles = p.compte_paroles
    mesurables = p.mesurables
    # Les trois listes s'écrivent **après** le détail, et non avant : elles
    # portent, pour chaque texte, les amendements dont on connaît à la fois le
    # scrutin et le débat — et ce rapprochement-là n'est résolu que par la
    # boucle ci-dessus, qui sait quelle lecture a voté quel numéro.
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
            texte["paroles"] = compte_paroles.get(l["uid"], 0)
            if l["uid"] in themes:
                texte["themes"] = themes[l["uid"]]
            # Absent plutôt que vide : deux textes sur trois ne sont jamais
            # allés au Sénat, et ce n'est pas un trou.
            if l["uid"] in etape_senat:
                texte["senat"] = etape_senat[l["uid"]]
            # Absent plutôt que vide : la grande majorité des textes n'a aucun
            # amendement mesurable, et une liste vide par texte pèserait pour
            # rien dans un fichier chargé d'un coup.
            if l["uid"] in mesurables:
                texte["amendementsMesurables"] = mesurables[l["uid"]]
            if l["statut"] == extraction.PROMULGUE:
                texte.update(loiNumero=l["loi_numero"], loiDate=l["loi_date"],
                             loiUrlJO=l["loi_url_jo"])
                # Ce que la loi change au droit, ce qu'elle y ajoute, et quand
                # elle s'applique : la carte le dit sans qu'on ait à l'ouvrir.
                # Une loi absente de `change` ne touche à rien et n'écrit aucun
                # article — ce n'est pas une donnée manquante, c'est un fait, et
                # la carte le dira.
                if legi_cx is not None:
                    texte["change"] = change.get(l["loi_numero"])
            textes.append(texte)
        tailles[nom_fichier] = ecrire(sortie / nom_fichier,
                                      {"genereLe": genere_le, "total": len(textes),
                                       "textes": textes})



def ecrire_travaux(p: Publication) -> None:
    """`travaux.json` : les dossiers qui n'aboutissent à aucune loi, par catégorie."""
    cx, sortie, genere_le, tailles = p.cx, p.sortie, p.genere_le, p.tailles
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

