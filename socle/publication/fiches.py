"""Le détail d'un texte : sa fiche, les fiches de ses amendements adoptés, ses versions, ses paroles — un fichier chacun, demandés seulement quand on les ouvre.
"""
from __future__ import annotations
from publication.amendements import amendements_adoptes_en_entier
from publication.amendements import amendements_du_texte
from publication.amendements import debats_par_amendement
from publication.amendements import votes_par_amendement
from publication.commun import ecrire
from publication.debats import paroles_du_texte
from publication.listes import procedure_acceleree
from publication.listes import signataires
from publication.listes import votes_du_texte
from publication.versions import comparaison_des_versions
from publication.versions import ouvrir_textes
from publication.versions import versions_du_texte
import extraction
import json
from publication.contexte import Publication


def ecrire_fiches(p: Publication) -> None:
    """Un fichier par texte, et à côté ses amendements, ses versions, ses paroles."""
    cx = p.cx
    sortie = p.sortie
    genere_le = p.genere_le
    tailles = p.tailles
    descriptions = p.descriptions
    resumes_debats = p.resumes_debats
    votes_senat = p.votes_senat
    mesurables = p.mesurables
    # Le détail, un fichier par texte. Seulement pour ceux que les listes
    # citent : publier les 708 dossiers qui ne font pas de loi n'aurait
    # aucun lecteur.
    details, amendements, paroles, versions_ecrites = 0, 0, 0, 0
    fiches_amdt = 0
    # Par texte, les amendements adoptés dont on connaît **et** le scrutin
    # **et** l'ampleur du débat. Ce sont les seuls que la maquette peut
    # signaler ; les autres ne disent rien, ni dans un sens ni dans l'autre —
    # 97 % des amendements adoptés le sont à main levée.
    textes_cx = ouvrir_textes()
    for l in cx.execute(
            "SELECT * FROM dossier WHERE est_loi = 1 AND statut != ?",
            (extraction.SANS_ACTE,)):
        parcours = [{**dict(e), "details": json.loads(e["details"] or "{}")}
                    for e in cx.execute(
            "SELECT code, lecture, libelle, chambre, date, numero, conclusion,"
            " future, precision, details"
            " FROM etape WHERE dossier_uid = ? ORDER BY date, rang", (l["uid"],))]
        cosign = json.loads(l["cosignataires"] or "[]")
        # Les versions successives du texte, et ce qui a changé de l'une à
        # l'autre. Le détail va dans un fichier par version — un texte adopté
        # pèse jusqu'à 1,4 Mo — et la fiche ne porte que de quoi afficher la
        # ligne dans le parcours.
        suite = versions_du_texte(cx, textes_cx, parcours)
        # Cherchés une fois par texte : ils servent à la comparaison des
        # versions **et** à la fiche de chaque amendement adopté.
        votes_amdt = votes_par_amendement(cx, l["uid"])
        debats_amdt = debats_par_amendement(cx, l["uid"])
        comparaisons, depuis_le_depot = (
            comparaison_des_versions(cx, suite, l["uid"], votes_amdt, debats_amdt)
            if suite else ([], None))
        # La fiche d'un amendement : son texte entier, son scrutin, son débat.
        # **Un fichier par amendement**, demandé seulement quand on ouvre sa
        # fiche — deux kilo-octets, quel que soit le texte dont il vient.
        debat_du_scrutin = {}
        for a in amendements_adoptes_en_entier(
                cx, l["uid"], suite, votes_amdt, debats_amdt):
            fiches_amdt += ecrire(
                sortie / "amendements" / l["uid"] / f'{a["uid"]}.json',
                {"genereLe": genere_le, **a})
            # Le parcours affiche une pastille sur les lignes de vote qui
            # portent sur un amendement disputé : il lui faut le compte des
            # orateurs, rattaché ici une fois pour toutes.
            if a.get("vote") and a.get("debat"):
                debat_du_scrutin[a["vote"]["uid"]] = a["debat"]
                # Et la carte du fil en a besoin avant même qu'on ouvre le
                # texte. **On publie les deux chiffres, pas le verdict** :
                # les seuils qui décident de la pastille sont un choix
                # d'affichage, ils vivent dans la maquette, à un seul endroit.
                mesurables.setdefault(l["uid"], []).append({
                    "uid": a["uid"], "numero": a["numero"],
                    "article": a["article"], "ou": a["ou"],
                    # De quoi écrire la ligne comme partout ailleurs : un
                    # amendement s'y nomme par son auteur, pas par son numéro
                    # seul. Un amendement du Gouvernement n'a pas de député
                    # pour auteur, d'où `typeAuteur`.
                    "nom": " ".join(x for x in (a["prenom"], a["nom"]) if x) or None,
                    "sigle": a["sigle"], "couleur": a["couleur"],
                    "typeAuteur": a["type_auteur"],
                    "vote": {"ecart": a["vote"]["ecart"],
                             "pour": a["vote"]["pour"],
                             "contre": a["vote"]["contre"]},
                    "debat": {"orateurs": a["debat"]["orateurs"]}})
        for comparaison in comparaisons:
            versions_ecrites += ecrire(
                sortie / "versions" / l["uid"] / f'{comparaison["ref"]}.json',
                {"genereLe": genere_le, **comparaison})
        # Le parcours entier, dans son propre fichier : c'est ce que l'onglet
        # « Texte » montre sous « Modifications » et sous « Version à jour »,
        # et il n'a pas de version à lui. Il porte le texte à jour de chaque
        # article, y compris de ceux que le dernier document ne réimprime pas.
        if depuis_le_depot:
            versions_ecrites += ecrire(
                sortie / "versions" / l["uid"] / "depuis-le-depot.json",
                {"genereLe": genere_le, **depuis_le_depot})
        # La colonne `description` de la base est la formule de la source : on
        # la republie sous son nom, et on libère la clé `description` pour la
        # rubrique écrite. Les laisser toutes deux sous le même nom revenait à
        # publier tantôt une phrase de la source, tantôt un objet écrit ici.
        ligne = {k: v for k, v in dict(l).items() if k != "description"}
        details += ecrire(sortie / "textes" / f'{l["uid"]}.json', {
            **ligne,
            # Les scrutins du Sénat, à côté de ceux de l'Assemblée et jamais
            # mêlés à eux : le parcours les affiche à leur date, chambre
            # marquée. Absents quand il n'y en a pas.
            **({"votesSenat": votes_senat[l["uid"]]}
               if l["uid"] in votes_senat else {}),
            "cosignataires": signataires(cx, cosign[:40]),
            "cosignatairesTotal": len(cosign),
            "auteur": (signataires(cx, [l["auteur_ref"]]) or [None])[0],
            "parcours": parcours,
            "versions": [{k: c[k] for k in ("ref", "nom", "date", "etape", "resume")}
                         for c in comparaisons],
            "votes": votes_du_texte(cx, l["uid"], debat_du_scrutin),
            # **Deux choses différentes, deux clés différentes.** `formule` est
            # la phrase que la source imprime sur le document de dépôt
            # (« visant à la création d'un statut des accompagnants… ») : elle
            # existe pour tous les textes et n'est écrite par personne ici.
            # `description` est la rubrique écrite hors ligne, qui n'existe que
            # pour quelques textes. Elles occupaient la même clé, et la seconde
            # écrasait la première : une phrase de la source disparaissait sans
            # que rien ne le signale.
            **({"formule": l["description"]} if l["description"] else {}),
            **({"procedureAcceleree": acceleree}
               if (acceleree := procedure_acceleree(cx, l["uid"])) else {}),
            # La description ne va que dans le fichier de détail : la liste est
            # chargée en entier au démarrage, et 2 151 descriptions la
            # feraient grossir pour un texte lu à la fois.
            **({"description": descriptions[l["uid"]]}
               if l["uid"] in descriptions else {}),
            **({"resumeDebats": resumes_debats[l["uid"]]}
               if l["uid"] in resumes_debats else {}),
        })

        # Les amendements dans un fichier séparé : la fiche s'ouvre sans les
        # attendre, et ils ne sont chargés que si on les demande.
        amdts = amendements_du_texte(cx, l["uid"])
        if amdts["total"]:
            amendements += ecrire(sortie / "amendements" / f'{l["uid"]}.json',
                                  {"genereLe": genere_le, **amdts})

        # Les argumentaires, dans un fichier à part pour la même raison :
        # 54 Ko en médiane, 286 Ko pour le PLFSS. La fiche s'ouvre sans eux.
        dits = paroles_du_texte(cx, l["uid"])
        if dits["total"]:
            paroles += ecrire(sortie / "paroles" / f'{l["uid"]}.json',
                              {"genereLe": genere_le, **dits})
    tailles["textes/*.json"] = details
    if versions_ecrites:
        tailles["versions/<texte>/*.json"] = versions_ecrites
    if amendements:
        tailles["amendements/*.json"] = amendements
    if fiches_amdt:
        tailles["amendements/<texte>/<amendement>.json"] = fiches_amdt
    if paroles:
        tailles["paroles/*.json"] = paroles

