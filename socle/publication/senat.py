"""Ce que la base du Sénat apporte à la publication : ses votes rattachés à nos textes, les sujets, la composition et les séances à venir.
"""
from __future__ import annotations

import sqlite3
from publication.commun import BASE_SENAT
from publication.commun import ecrire
from publication.contexte import Publication


def ouvrir_senat() -> sqlite3.Connection | None:
    """La base du Sénat, si elle existe.

    **Elle est facultative**, comme celle du droit consolidé : sans elle, tout
    le reste se publie et l'application n'affiche simplement ni les votes du
    Sénat, ni sa composition, ni son calendrier.
    """
    if not BASE_SENAT.exists():
        return None
    cx = sqlite3.connect(f"file:{BASE_SENAT}?mode=ro", uri=True)
    cx.row_factory = sqlite3.Row
    return cx


def votes_du_senat(senat_cx: sqlite3.Connection | None,
                   signets: dict[str, str]) -> dict[str, list[dict]]:
    """Les scrutins du Sénat, rangés par texte de chez nous.

    **Rien n'est mélangé avec les votes de l'Assemblée** : ni total commun, ni
    comparaison. Chaque scrutin dit sa chambre, sa date et ce que chaque groupe
    a fait, et c'est tout.
    """
    if senat_cx is None:
        return {}
    par_texte: dict[str, list[dict]] = {}
    groupes = {l["sigle"]: dict(l) for l in senat_cx.execute(
        "SELECT sigle, nom, rang FROM groupe_senat")}
    detail: dict[tuple, list[dict]] = {}
    for l in senat_cx.execute("SELECT * FROM vote_groupe_senat"):
        g = groupes.get(l["groupe"], {})
        detail.setdefault((l["session"], l["numero"]), []).append({
            "sigle": l["groupe"], "nom": g.get("nom") or l["groupe"],
            "rang": g.get("rang"), "pour": l["pour"], "contre": l["contre"],
            "abstentions": l["abstentions"], "nonVotants": l["non_votants"]})
    for l in senat_cx.execute(
            "SELECT * FROM scrutin_senat WHERE signet IS NOT NULL"
            " ORDER BY date, numero"):
        uid = signets.get(l["signet"])
        if not uid:
            continue
        v = {"session": l["session"], "numero": l["numero"], "date": l["date"],
             "objet": l["objet"], "pour": l["pour"], "contre": l["contre"]}
        groupes_du = sorted(detail.get((l["session"], l["numero"]), []),
                            key=lambda g: (g["rang"] is None, g["rang"]))
        if groupes_du:
            v["groupes"] = groupes_du
        par_texte.setdefault(uid, []).append(v)
    return par_texte


def themes_par_texte(senat_cx: sqlite3.Connection | None,
                     signets: dict[str, str]) -> dict[str, list[str]]:
    """Le sujet de chaque texte, tel que le Sénat le classe.

    **L'application n'avait aucune notion de sujet avant lui** : on pouvait
    filtrer par étape, par chambre, par type, jamais par « santé » ou
    « logement ». 730 textes en portent un — tous ceux passés au Sénat, dont
    les 107 lois promulguées ; les deux tiers restants n'y sont jamais allés,
    et le filtre doit le dire plutôt que de les faire disparaître.
    """
    if senat_cx is None:
        return {}
    par_texte: dict[str, list[str]] = {}
    for l in senat_cx.execute("SELECT signet, theme FROM theme_senat"
                              " ORDER BY signet, rang"):
        uid = signets.get(l["signet"])
        if uid:
            par_texte.setdefault(uid, []).append(l["theme"])
    return par_texte


def composition_du_senat(senat_cx: sqlite3.Connection | None) -> dict | None:
    """Qui siège au Sénat, et dans quel groupe.

    **Trois choses que cet écran doit dire au lieu de les cacher** : que 179
    sénateurs sur 348 n'ont plus de groupe depuis le renouvellement du
    2026-09-27 ; que l'ordre des groupes est mesuré sur leur façon de voter et
    non sur les sièges, faute de plan de salle ; et qu'il n'y a pas de photos,
    parce qu'elles ne sont pas libres.

    La **couleur** et le **nom complet** d'un groupe viennent de la page des
    groupes politiques du site, et ne sont pas de nous — contrairement à celles
    de l'Assemblée, qui sont une convention d'affichage. Les deux peuvent
    manquer : un groupe sans couleur se dessine en gris plutôt qu'en une
    teinte inventée.
    """
    if senat_cx is None:
        return None
    senateurs = [dict(l) for l in senat_cx.execute(
        "SELECT matricule, civilite, prenom, nom, groupe, circonscription"
        " FROM senateur ORDER BY nom, prenom")]
    if not senateurs:
        return None
    return {
        "effectif": len(senateurs),
        "sansGroupe": sum(1 for s in senateurs if not s["groupe"]),
        # `nom` reste l'abrégé courant — « SER », « CRCE-K » — qui tient
        # sur une pastille ; `nomComplet` est la phrase entière, pour la
        # ligne. L'Assemblée publie les deux de la même façon.
        "groupes": [{"sigle": l["sigle"], "nom": l["nom"],
                     "nomComplet": l["nom_complet"], "couleur": l["couleur"],
                     "effectif": l["effectif"], "rang": l["rang"]}
                    for l in senat_cx.execute(
            "SELECT sigle, nom, nom_complet, couleur, effectif, rang"
            " FROM groupe_senat ORDER BY rang IS NULL, rang")],
        "senateurs": senateurs,
    }


def calendrier_du_senat(senat_cx: sqlite3.Connection | None,
                        signets: dict[str, str],
                        titres: dict[str, str]) -> list[dict] | None:
    """Les séances à venir au Sénat, et le texte que chacune examine.

    Mesuré le 2026-10-04 : 18 des 19 séances annoncées nomment un texte que
    nous suivons — nettement mieux que l'agenda de l'Assemblée, où une seule
    réunion à venir sur 35 nomme un texte.
    """
    if senat_cx is None:
        return None
    jours: dict[str, list[dict]] = {}
    for l in senat_cx.execute("SELECT date, signet FROM seance_senat"
                              " ORDER BY date, signet"):
        uid = signets.get(l["signet"])
        jours.setdefault(l["date"], []).append(
            {"uid": uid, "titre": titres.get(uid) if uid else None,
             "signet": l["signet"]})
    return [{"date": d, "textes": t} for d, t in sorted(jours.items())]


def ecrire_senat(p: Publication) -> None:
    """La composition du Sénat et ses séances à venir : deux écrans, deux fichiers."""
    sortie = p.sortie
    genere_le = p.genere_le
    tailles = p.tailles
    senat_cx = p.senat_cx
    signets = p.signets
    titres = p.titres
    compo = composition_du_senat(senat_cx)
    if compo:
        tailles["senat/composition.json"] = ecrire(
            sortie / "senat" / "composition.json", {"genereLe": genere_le, **compo})
    agenda_senat = calendrier_du_senat(senat_cx, signets, titres)
    if agenda_senat:
        tailles["senat/calendrier.json"] = ecrire(
            sortie / "senat" / "calendrier.json",
            {"genereLe": genere_le, "jours": agenda_senat})

