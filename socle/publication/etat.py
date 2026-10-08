"""Les fichiers d'ensemble : l'état de la publication, la composition de l'Assemblée, les étapes et leurs comptes.
"""
from __future__ import annotations
from publication.amendements import AMENDEMENTS_MAX
from publication.commun import ecrire
from publication.commun import sans_accent
from publication.debats import vu_le
from publication.listes import ARRETES
import affichage
import extraction
from publication.contexte import Publication


def provenance_et_fraicheur(p: Publication, chargement) -> dict:
    """D'où viennent les données, de quand, et ce qui manque aujourd'hui."""
    cx, genere_le, senat_cx, comptes = p.cx, p.genere_le, p.senat_cx, p.comptes
    return {
    "genereLe": genere_le,
    "source": extraction.URL_ARCHIVE,
    "licence": "Licence Ouverte (Etalab)",
    "legislature": extraction.LEGISLATURE,
    "dernierChargement": dict(chargement) if chargement else None,
    "dossiers": cx.execute("SELECT COUNT(*) n FROM dossier").fetchone()["n"],
    "etapesEnregistrees": cx.execute("SELECT COUNT(*) n FROM etape").fetchone()["n"],
    # Ce que la page doit savoir taire plutôt que d'afficher un zéro faux :
    # une rubrique dont la source n'est jamais arrivée.
    "amendementsIndisponibles":
        cx.execute("SELECT COUNT(*) n FROM amendement").fetchone()["n"] == 0,
    # **Et quand elle date.** Une archive qui n'arrive pas ce matin ne vide
    # plus la base : les amendements de la veille restent affichés. Encore
    # faut-il le dire, sans quoi la page se donnerait pour plus fraîche
    # qu'elle n'est. C'est l'horodatage du dernier téléchargement réussi.
    "amendementsVusLe": vu_le(cx, extraction.URL_AMENDEMENTS),
    # Et de quand datent les données du Sénat. Même raison : une
    # reconstruction qui échoue n'efface plus la base de la veille — mais
    # la page ne doit pas se donner pour plus fraîche qu'elle n'est.
    "senatVuLe": vu_le(senat_cx, "senat.db") if senat_cx else None,
    "textesEnCours": comptes.get(extraction.EN_COURS, 0),
    "promulgues": comptes.get(extraction.PROMULGUE, 0),
    "scrutins": cx.execute("SELECT COUNT(*) n FROM vote").fetchone()["n"],
    "textesAvecVote": cx.execute(
        "SELECT COUNT(DISTINCT d.uid) n FROM dossier d JOIN vote v ON v.dossier_uid = d.uid"
        " WHERE d.est_loi = 1").fetchone()["n"],
    "arretes": sum(comptes.get(x, 0) for x in ARRETES),
    "travaux": cx.execute(
        "SELECT COUNT(*) n FROM dossier WHERE est_loi = 0").fetchone()["n"],
    }


def comptes_publies(p: Publication) -> dict:
    """Combien de tout, pour que la page puisse le dire sans tout charger."""
    cx, legi_cx, change, senat_cx, votes_senat = (
        p.cx, p.legi_cx, p.change, p.senat_cx, p.votes_senat)
    descriptions, resumes_debats, comptes = p.descriptions, p.resumes_debats, p.comptes
    return {
    # Le droit consolidé est facultatif : sans lui, tout le reste se publie
    # et l'application n'affiche simplement pas ce que les lois changent.
    "droitConsolideIndisponible": legi_cx is None,
    "loisAvecChangements": len(change),
    "articlesChanges": sum(c["total"] for c in change.values()),
    # Compté à part de `articlesChanges` : ce sont les articles que les
    # lois ont écrits pour elles-mêmes, pas ce qu'elles ont modifié.
    "articlesAjoutes": sum(c["ajouts"] for c in change.values()),
    "amendements": cx.execute("SELECT COUNT(*) n FROM amendement").fetchone()["n"],
    "textesAvecAmendements": cx.execute(
        "SELECT COUNT(DISTINCT dossier_uid) n FROM amendement").fetchone()["n"],
    "amendementsMaxParTexte": AMENDEMENTS_MAX,
    # Les débats sont facultatifs eux aussi : leur archive pèse 55,8 Mo.
    # Sans eux, la fiche s'affiche sans les argumentaires plutôt que de
    # laisser croire que personne n'a parlé du texte.
    "debatsIndisponibles":
        cx.execute("SELECT COUNT(*) n FROM parole").fetchone()["n"] == 0,
    "debatsVusLe": vu_le(cx, extraction.URL_DEBATS),
    # Le Sénat est une source facultative, comme le droit consolidé : sans
    # elle, tout le reste se publie et l'application n'affiche ni ses
    # votes, ni sa composition, ni son calendrier.
    "senatIndisponible": senat_cx is None,
    "senatTextesAvecVote": len(votes_senat),
    "senatScrutins": sum(len(v) for v in votes_senat.values()),
    "paroles": cx.execute("SELECT COUNT(*) n FROM parole").fetchone()["n"],
    "descriptions": len(descriptions),
    "resumesDebats": len(resumes_debats),
    "textesAvecParoles": cx.execute(
        "SELECT COUNT(DISTINCT dossier_uid) n FROM parole").fetchone()["n"],
    }


def ecrire_etat(p: Publication) -> None:
    """`etat.json` : d'où viennent les données, de quand, et ce qu'il y a dedans."""
    cx, sortie, tailles, comptes = p.cx, p.sortie, p.tailles, p.comptes
    # « partiel » : le rangement a réussi, mais une source facultative a
    # manqué. C'est un chargement valable, et la page doit pouvoir le dire.
    chargement = cx.execute(
        "SELECT * FROM journal WHERE statut IN ('succes', 'partiel')"
        " ORDER BY id DESC LIMIT 1").fetchone()
    tailles["etat.json"] = ecrire(sortie / "etat.json", {
        **provenance_et_fraicheur(p, chargement),
        **comptes_publies(p),
        "issues": {cle: {"nom": nom, "quoi": quoi, "textes": comptes.get(cle, 0)}
                   for cle, (nom, quoi) in affichage.FINS.items()},
        "fichiers": ["etapes.json", "groupes.json", "textes.json", "promulgues.json",
                     "arretes.json", "travaux.json", "textes/<uid>.json",
                     "amendements/<uid>.json", "paroles/<uid>.json",
                     "changements/<uid>.json",
                     "changements/<uid>/<LEGIARTI>.json",
                     "groupes/<ref>.json"],
    })


def ecrire_groupes(p: Publication) -> None:
    """`groupes.json` et un fichier par groupe : la composition de l'Assemblée."""
    cx, sortie, genere_le, tailles = p.cx, p.sortie, p.genere_le, p.tailles
    # Les groupes, rangés de la gauche à la droite de l'hémicycle. L'ordre est
    # mesuré sur les numéros de siège publiés ; la couleur est une convention
    # d'affichage, que la page reprend telle quelle plutôt que d'en inventer.
    # L'effectif est un compte des députés en exercice, pas une donnée publiée
    # comme telle : c'est ce qui permet de dessiner la composition. Les groupes
    # à zéro député sont écartés — la base en garde deux, hérités de scrutins
    # qui citent un identifiant sans groupe correspondant.
    groupes_publies = [dict(g) for g in cx.execute(
        "SELECT g.ref, g.sigle, g.nom, g.rang, g.siege_median, g.couleur,"
        " COUNT(a.ref) effectif"
        " FROM groupe g LEFT JOIN acteur a ON a.groupe_ref = g.ref"
        " GROUP BY g.ref HAVING effectif > 0 ORDER BY g.rang")]
    tailles["groupes.json"] = ecrire(sortie / "groupes.json", {
        "genereLe": genere_le,
        "ordre": "de la gauche à la droite de l'hémicycle, d'après les numéros"
                 " de siège publiés par l'Assemblée",
        "couleurs": "convention d'affichage — l'open data n'en publie aucune",
        "deputes": sum(g["effectif"] for g in groupes_publies),
        "groupes": groupes_publies,
    })

    # Les députés d'un groupe, un fichier par groupe. Tout est recopié de la
    # source : la civilité, le prénom, le nom, le département, le numéro de
    # circonscription et celui du siège dans l'hémicycle. Le classement, lui,
    # est à nous : par nom, puis par prénom, ce que la source ne fait pas.
    #
    # La page lit ces douze fichiers à l'ouverture de l'hémicycle — 113 Ko en
    # tout — pour compter les femmes et les hommes de chaque groupe sur les
    # civilités. Ce compte n'est donc pas publié ici : il se refait à
    # l'affichage, et reste juste sans nouvelle publication.
    deputes = 0
    for g in groupes_publies:
        membres = [dict(l) for l in cx.execute(
            "SELECT ref, civilite, prenom, nom, departement, circo, siege, photo"
            " FROM acteur WHERE groupe_ref = ?", (g["ref"],))]
        # Le classement se fait ici et non en SQL : SQLite range « Bénard »
        # après « Brugerolles », parce qu'il compare des octets et que « é »
        # vient après « r ». Dans une liste de noms, cela se voit.
        membres.sort(key=lambda m: (sans_accent(m["nom"]), sans_accent(m["prenom"])))
        deputes += ecrire(sortie / "groupes" / f'{g["ref"]}.json', {
            "genereLe": genere_le,
            "ref": g["ref"],
            "sigle": g["sigle"],
            "nom": g["nom"],
            "couleur": g["couleur"],
            "effectif": len(membres),
            "ordre": "par nom, puis par prénom",
            "deputes": membres,
        })
    tailles["groupes/<ref>.json"] = deputes



def ecrire_etapes(p: Publication) -> None:
    """`etapes.json` : les étapes des deux chambres et les sujets, avec leurs comptes."""
    sortie = p.sortie
    genere_le = p.genere_le
    tailles = p.tailles
    themes = p.themes
    etape_senat = p.etape_senat
    en_cours_au_senat = p.en_cours_au_senat
    comptes = p.comptes
    par_etape = p.par_etape
    # Les textes rangés par moment du parcours **sénatorial**, pour que
    # l'onglet « Sénat » sache dessiner ses colonnes sans rien recalculer.
    par_moment: dict[str, int] = {}
    for uid, e in etape_senat.items():
        if uid in en_cours_au_senat:
            par_moment[e["moment"]] = par_moment.get(e["moment"], 0) + 1
    # La composition du Sénat et son calendrier : deux écrans, deux fichiers,
    # demandés seulement quand on les ouvre.
    compte_themes: dict[str, int] = {}
    for liste in themes.values():
        for t in liste:
            compte_themes[t] = compte_themes.get(t, 0) + 1

    tailles["etapes.json"] = ecrire(sortie / "etapes.json", {
        "genereLe": genere_le,
        "etapes": [{"n": n, "nom": nom, "quoi": quoi, "textesEnCours": par_etape.get(n, 0)}
                   for n, nom, quoi in extraction.ETAPES],
        # **Les étapes du Sénat ne sont pas celles de l'Assemblée**, et on ne
        # les aligne pas : les deux chambres ne découpent pas le parcours
        # pareil. Voir `affichage.ETAPES_SENAT`.
        "etapesSenat": [{"cle": cle, "nom": nom, "quoi": quoi,
                         "textesEnCours": par_moment.get(cle, 0)}
                        for cle, nom, quoi in affichage.ETAPES_SENAT],
        "textesAuSenat": len(etape_senat),
        # Les sujets, et combien de textes chacun porte. Le plus fourni
        # d'abord : c'est l'ordre dans lequel le filtre les propose.
        "themes": [{"nom": t, "textes": n} for t, n in
                   sorted(compte_themes.items(), key=lambda x: (-x[1], x[0]))],
        "textesAvecTheme": len(themes),
        # Les lois promulguées ne sont pas une septième étape : c'est l'après.
        # Mais un lecteur qui compte les textes doit les retrouver quelque part.
        "promulguees": comptes.get(extraction.PROMULGUE, 0),
    })
