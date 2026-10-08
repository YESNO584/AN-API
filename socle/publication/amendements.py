"""Les amendements d'un texte : la liste plafonnée de l'onglet, la fiche de chaque adopté, et le rapprochement avec son scrutin et son débat.
"""
from __future__ import annotations

import json
import re
import sqlite3
import textes as textes_mod


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


def sans_les_doublons(lignes: list) -> list:
    """Un même amendement publié deux fois par la source ne compte qu'une.

    Mesuré le 2026-09-23 : sur les 12 738 amendements adoptés qui portent un
    dispositif, **37 couples (document, numéro) sont portés par deux lignes**.
    Il faut les départager, car ils ne disent pas tous la même chose :

    - **29 portent deux fois le même dispositif.** C'est le même amendement,
      publié sous deux identifiants qui ne diffèrent que par leur segment de
      document — `…B2755P0D1N000059` et `…BTC2755P0D1N000059` pointent le même
      `texte_ref`, le même article, la même date et le même texte. Le compter
      deux fois faisait dire à l'écran « 2 amendements adoptés de justesse »
      là où il n'y en avait qu'un.
    - **8 portent des dispositifs différents.** Ce sont deux amendements bien
      réels, de deux délibérations successives — `D1` et `D2` dans
      l'identifiant — qui numérotent chacune à partir de 1. Les fondre serait
      en perdre un.

    D'où la clé : le document, le numéro **et le dispositif**. Elle sépare les
    deux cas sans rien interpréter, parce qu'elle ne compare que ce que la
    source écrit.
    """
    vus, gardees = set(), []
    for l in lignes:
        cle = (l["texte_ref"], l["numero"], l["dispositif"])
        if cle in vus:
            continue
        vus.add(cle)
        gardees.append(l)
    return gardees


def amendements_adoptes_en_entier(cx: sqlite3.Connection, dossier_uid: str,
                                  suite: list[dict], votes: dict[str, list[dict]],
                                  debats: dict[tuple, dict]) -> list[dict]:
    """Les amendements **adoptés** d'un texte, avec tout ce qu'on en sait.

    C'est ce qui remplit la fiche d'un amendement : son dispositif et son
    exposé **entiers**, son auteur, le scrutin s'il y en a eu un — groupe par
    groupe — et combien de monde en a parlé.

    **Un fichier par amendement, et c'est mesuré.** `amendements/<uid>.json`
    sert la liste de l'onglet, plafonnée à 150 par texte et l'exposé coupé à
    400 caractères : un dossier compte jusqu'à 19 510 amendements, et tout y
    mettre ferait porter des dizaines de méga-octets à un téléphone pour une
    liste qu'on parcourt. Un fichier par **texte** ne marchait pas non plus :
    mesuré le 2026-09-23, 238 fichiers, 25 Ko de médiane mais **4,5 Mo au
    pire** — le prix d'une fiche ne doit pas dépendre du texte dont elle vient.
    Un fichier par amendement pèse deux kilo-octets, et on n'en demande qu'un.

    Seuls les adoptés en ont un : ce sont eux que l'onglet « Texte » relie à un
    article, et un amendement rejeté n'a pas de fiche à ouvrir.
    """
    fenetres = {avant["ref"]: (avant["date"], suite[rang + 1]["date"])
                for rang, avant in enumerate(suite[:-1])}
    lignes = cx.execute(
        "SELECT a.uid, a.numero, a.article, a.ou, a.division, a.sort, a.date_depot,"
        " a.dispositif, a.expose, a.morceaux, a.type_auteur, a.texte_ref,"
        " ac.civilite, ac.prenom, ac.nom, ac.photo, g.sigle, g.nom nom_groupe,"
        " g.couleur"
        " FROM amendement a"
        " LEFT JOIN acteur ac ON ac.ref = a.auteur_ref"
        " LEFT JOIN groupe g ON g.ref = a.groupe_ref"
        " WHERE a.dossier_uid = ? AND a.sort = 'Adopté' AND a.dispositif != ''"
        " ORDER BY a.date_depot, a.ordre", (dossier_uid,)).fetchall()
    lignes = sans_les_doublons(lignes)

    sortie = []
    for l in lignes:
        a = dict(l)
        a["morceaux"] = json.loads(a["morceaux"] or "[]")
        document = numero_de_document(a.pop("texte_ref"))
        chiffre = re.match(r"\s*(\d+)", a["numero"] or "")
        if chiffre:
            cle = chiffre.group(1)
            fenetre = fenetres.get(l["texte_ref"])
            retenus = [v for v in votes.get(cle, ())
                       if not fenetre or fenetre[0] <= v["date"] <= fenetre[1]]
            if len(retenus) == 1:
                # Le scrutin entier, groupe par groupe : la fiche doit pouvoir
                # montrer qui a voté quoi sans aller chercher un autre fichier.
                a["vote"] = {**retenus[0],
                             "groupes": groupes_du_scrutin(cx, retenus[0]["uid"])}
            if (document, cle) in debats:
                a["debat"] = debats[(document, cle)]
        sortie.append(a)
    return sortie


def groupes_du_scrutin(cx: sqlite3.Connection, vote_uid: str) -> list[dict]:
    """Qui a voté quoi, rangé comme dans l'hémicycle.

    De la gauche à la droite, sur les rangs mesurés. Un groupe que la source
    ne nomme plus — un groupe dissous — passe en fin de liste plutôt que de
    disparaître.
    """
    return [dict(g) for g in cx.execute(
        "SELECT vg.sigle, vg.nom, vg.membres, vg.position, vg.pour, vg.contre,"
        " vg.abstentions, vg.non_votants, g.rang, g.couleur"
        " FROM vote_groupe vg LEFT JOIN groupe g ON g.ref = vg.organe_ref"
        " WHERE vg.vote_uid = ?"
        " ORDER BY g.rang IS NULL, g.rang, vg.membres DESC", (vote_uid,))]


# Le numéro d'amendement, tel que l'objet d'un scrutin le nomme : « sur
# l'amendement n° 885 (rect.) du Gouvernement à l'article 3 du projet de
# loi… ». On ne retient que le **premier** nommé : un objet qui ajoute « et
# les amendements identiques suivants » ne dit pas lesquels, et deviner ferait
# porter un vote à un amendement que la source ne désigne pas.
NUMERO_D_AMENDEMENT = re.compile(
    r"(?:l['’]amendement|le sous-amendement)\s+n°\s*(\d+)", re.IGNORECASE)


def numero_de_document(ref: str | None) -> str:
    """Le numéro de dépôt que porte la référence d'un document.

    « PRJLANR5L17BTC2984 » → « 2984 », « PIONANR5L17BTA0224 » → « 224 ». Les
    zéros de tête tombent : la séance dit « n° 224 ».
    """
    trouve = re.search(r"(\d+)$", ref or "")
    return str(int(trouve.group(1))) if trouve else ""


def votes_par_amendement(cx: sqlite3.Connection,
                         dossier_uid: str) -> dict[str, list[dict]]:
    """Les scrutins publics d'un dossier, rangés par numéro d'amendement.

    Mesuré le 2026-09-20 : les 2 248 scrutins sur amendement de la législature
    nomment tous un numéro dans leur objet, sans exception.

    **Un numéro ne désigne pas un amendement à lui seul.** 69 couples (dossier,
    numéro) sur 4 372 sont portés par deux documents du même dossier — deux
    lectures, où l'amendement n° 1 de l'une et celui de l'autre n'ont rien à
    voir. C'est pourquoi cette fonction rend une **liste** : c'est la date qui
    départage, et elle appartient à l'appelant, qui sait de quel document il
    parle et quand ce document a été discuté.
    """
    trouves: dict[str, list[dict]] = {}
    for l in cx.execute(
            "SELECT uid, numero, date, objet, sort, pour, contre, abstentions"
            " FROM vote WHERE dossier_uid = ? AND portee = 'amendement'",
            (dossier_uid,)):
        nomme = NUMERO_D_AMENDEMENT.search(l["objet"] or "")
        if not nomme:
            continue
        exprimes = (l["pour"] or 0) + (l["contre"] or 0)
        if not exprimes:
            continue
        trouves.setdefault(nomme.group(1), []).append({
            # L'identifiant du scrutin, pour que la fiche d'un amendement
            # puisse en montrer le détail groupe par groupe.
            "uid": l["uid"],
            "scrutin": l["numero"], "date": l["date"], "sort": l["sort"],
            "pour": l["pour"], "contre": l["contre"],
            "abstentions": l["abstentions"],
            # L'écart en part des suffrages exprimés : un 39 contre 37 et un
            # 390 contre 370 se lisent pareil, et c'est ce qui compte.
            "ecart": round(abs(l["pour"] - l["contre"]) / exprimes, 4)})
    return trouves


def debats_par_amendement(cx: sqlite3.Connection, dossier_uid: str) -> dict[tuple, dict]:
    """Combien de personnes ont parlé de chaque amendement, par document amendé.

    La clé est (numéro de dépôt du document, numéro d'amendement) : c'est ce
    qui sépare les lectures, deux amendements d'un même dossier pouvant porter
    le même numéro sur deux documents différents.
    """
    return {(l["texte_numero"], l["numero"]):
            {"orateurs": l["orateurs"], "paragraphes": l["paragraphes"]}
            for l in cx.execute(
                "SELECT texte_numero, numero, MAX(orateurs) orateurs,"
                " MAX(paragraphes) paragraphes FROM debat_amendement"
                " WHERE dossier_uid = ? GROUP BY texte_numero, numero",
                (dossier_uid,))}


def amendements_adoptes(cx: sqlite3.Connection, ref: str,
                        votes: dict[str, list[dict]] | None = None,
                        debats: dict[tuple, dict] | None = None,
                        fenetre: tuple[str, str] | None = None) -> dict:
    """Les amendements adoptés sur une version, rangés par article visé.

    Le rapprochement se fait par le numéro d'article et par la position que
    donne la source — « sur » l'article, ou « après » lui. **Jamais par le
    texte** : dire quel mot vient de quel amendement demanderait d'interpréter
    l'instruction de l'amendement, donc de fabriquer du texte de loi.

    Chaque amendement porte, quand la source les donne, son scrutin et
    l'ampleur de son débat. **Les deux manquent le plus souvent, et ce n'est
    pas un défaut** : 97 % des amendements adoptés l'ont été à main levée,
    sans qu'aucun décompte soit enregistré. Une absence ne dit donc pas qu'un
    amendement est passé sans discussion — elle dit qu'on n'en sait rien.

    `fenetre` est l'intervalle de dates pendant lequel ce document a été
    amendé : de son adoption à celle de la version suivante. C'est lui qui
    départage deux lectures qui numérotent leurs amendements pareil.
    """
    votes = votes or {}
    debats = debats or {}
    document = numero_de_document(ref)
    lignes = sans_les_doublons(cx.execute(
        # `texte_ref` et `dispositif` ne servent qu'à écarter les doublons de
        # la source — voir `sans_les_doublons` — et ne sont pas publiés ici.
        "SELECT a.uid, a.numero, a.article, a.ou, a.division, a.type_auteur,"
        " a.texte_ref, a.dispositif,"
        " ac.civilite, ac.prenom, ac.nom, g.sigle, g.couleur"
        " FROM amendement a"
        " LEFT JOIN acteur ac ON ac.ref = a.auteur_ref"
        " LEFT JOIN groupe g ON g.ref = a.groupe_ref"
        " WHERE a.texte_ref = ? AND a.sort = 'Adopté'"
        " ORDER BY a.ordre", (ref,)).fetchall())

    def chiffres(numero: str | None) -> dict:
        """Le scrutin et le débat de cet amendement, s'ils existent.

        Le numéro de la base porte parfois une mention — « 885 (Rect) » — que
        ni le scrutin ni la séance ne reprennent à l'identique. On le réduit
        donc à ses chiffres. Un numéro de commission, « CL755 », n'a jamais de
        scrutin en séance : il ne trouvera rien, et c'est juste.
        """
        chiffre = re.match(r"\s*(\d+)", numero or "")
        if not chiffre:
            return {}
        cle = chiffre.group(1)
        # Le scrutin doit tomber dans la fenêtre du document : sinon c'est
        # celui d'une autre lecture, qui numérote ses amendements pareil.
        candidats = [v for v in votes.get(cle, ())
                     if not fenetre or fenetre[0] <= v["date"] <= fenetre[1]]
        return {**({"vote": candidats[0]} if len(candidats) == 1 else {}),
                **({"debat": debats[(document, cle)]}
                   if (document, cle) in debats else {})}

    return textes_mod.amendements_du_document(
        [{"uid": l["uid"], "numero": l["numero"],
          "nom": " ".join(x for x in (l["prenom"], l["nom"]) if x) or None,
          "civilite": l["civilite"], "sigle": l["sigle"], "couleur": l["couleur"],
          # Un amendement du Gouvernement n'a pas de député pour auteur : sans
          # ce champ, sa ligne n'affiche qu'un numéro et personne.
          "typeAuteur": l["type_auteur"],
          "division": {"article": l["article"], "ou": l["ou"], "type": l["division"]},
          **chiffres(l["numero"])}
         for l in lignes])
