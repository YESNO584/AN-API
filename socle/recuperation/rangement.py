"""Remplacer le contenu de la base par celui des archives, tout ou rien : lire chaque archive, rapprocher ce qui doit l'être, écrire en une transaction.
"""
from __future__ import annotations

import collections
import json
import pathlib
import sqlite3
import sys
import extraction
from recuperation.reprise import a_reprendre, reposer


def lire_les_references(archives: dict[str, pathlib.Path]) -> dict:
    """Ce que les autres lectures consultent : groupes, organes, acteurs,
    documents, réunions, et l'état que le Sénat donne à chaque dossier."""
    groupes = extraction.lire_groupes(archives["groupes"])
    organes = extraction.lire_organes(archives["groupes"])
    # Les députés en exercice d'abord — ils apportent le groupe et la photo —
    # puis les autres, qui n'apportent qu'un nom mais le portent seuls.
    acteurs = extraction.lire_acteurs(archives["acteurs"], groupe_et_photo=False)
    acteurs.update(extraction.lire_acteurs(archives["groupes"]))
    documents = extraction.lire_documents(archives["dossiers"])
    reunions = extraction.lire_reunions(archives["agenda"])
    etats_senat = extraction.lire_senat(archives["senat"])
    return dict(groupes=groupes, organes=organes, acteurs=acteurs,
                documents=documents, reunions=reunions, etats_senat=etats_senat)


def lire_les_scrutins(archives: dict[str, pathlib.Path], groupes: dict
                      ) -> tuple[list[dict], dict[str, dict], list[dict]]:
    """Les scrutins, rangés aussi par identifiant, et l'ordre des groupes
    mesuré sur les sièges qu'ils occupent."""
    # Les scrutins d'abord : on a besoin de savoir, pour chaque dossier, quels
    # votes le concernent — et le lien se lit dans les deux sens.
    # Les numéros de siège se comptent par millions sur une législature : on
    # les compte au vol, valeur par valeur, plutôt que de les empiler.
    sieges: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    votes, par_ref = [], {}
    for brut in extraction.lire_scrutins(archives["scrutins"]):
        v = extraction.analyser_scrutin(brut, groupes)
        votes.append(v)
        par_ref[v["uid"]] = v
        for ref, place in extraction.places_du_scrutin(brut):
            sieges[ref][place] += 1
    rangs = extraction.ordonner_groupes(sieges, groupes)
    return votes, par_ref, rangs


def lire_les_dossiers(archives: dict[str, pathlib.Path], aujourdhui: str,
                      ref: dict, par_ref: dict[str, dict]
                      ) -> tuple[list[tuple], list[tuple]]:
    """Les dossiers et leurs étapes, prêts à écrire — et le lien scrutin →
    dossier complété dans l'autre sens au passage."""
    organes, documents, reunions, acteurs, etats_senat = (
        ref["organes"], ref["documents"], ref["reunions"], ref["acteurs"],
        ref["etats_senat"])
    dossiers, etapes = [], []
    for brut in extraction.lire_archive(archives["dossiers"]):
        dp = brut["dossierParlementaire"]
        # Le dossier cite parfois ses scrutins ; le scrutin nomme parfois son
        # dossier. Aucun des deux sens ne suffit seul : réunis, ils font passer
        # la couverture de 34 et 68 textes à 71 (mesuré le 2026-08-31).
        for ref in extraction.refs_de_vote(dp):
            if ref in par_ref and not par_ref[ref]["dossier"]:
                par_ref[ref]["dossier"] = dp["uid"]
        d = extraction.analyser(brut, aujourdhui, etats_senat,
                                reunions, organes, documents, acteurs)
        courant = d["etapeCourante"] or {}
        prochaine = next((e for e in d["etapes"] if e["future"]), None)
        # Le document de dépôt porte la description du texte et son auteur.
        depot = next((a for a in extraction.aplatir(dp.get("actesLegislatifs") or {})
                      if a.get("@xsi:type") == "DepotInitiative_Type"), None)
        doc = documents.get((depot or {}).get("texteAssocie")) or {}
        auteur = (doc.get("auteurs") or [{}])[0].get("ref")
        cosign = json.dumps([c["ref"] for c in doc.get("cosignataires") or []],
                            ensure_ascii=False)
        dossiers.append((
            d["uid"], d["legislature"], d["titre"], d["titreChemin"], d["type"],
            int(d["estLoi"]), d["chambreInitiale"], d["statut"], d["etatSenat"],
            d["etape"], d["dateDernierMouvement"],
            courant.get("chambre"), courant.get("lecture"),
            courant.get("libelle"), courant.get("conclusion"),
            (prochaine or {}).get("date"), (prochaine or {}).get("libelle"),
            d["urlAN"], d["urlSenat"],
            doc.get("description"), auteur, doc.get("type"), cosign,
            d["loiNumero"], d["loiDate"], d["loiUrlJO"],
        ))
        etapes += [(
            d["uid"], e["uid"], e["code"], e["lecture"], e["libelle"], e["chambre"],
            e["date"], e["rang"], e["numero"], e["conclusion"], int(e["future"]),
            e["precision"],
            json.dumps(e["details"], ensure_ascii=False) if e["details"] else None,
        ) for e in d["etapes"]]
    return dossiers, etapes


def lignes_de_vote(votes: list[dict], connus: set[str]
                   ) -> tuple[list[tuple], list[tuple]]:
    """Les scrutins et le détail par groupe, prêts à écrire."""
    # Un scrutin peut nommer un dossier d'une autre législature, ou disparu :
    # la clé étrangère refuserait la ligne. On coupe le lien plutôt que de
    # perdre le vote, qui reste exact en lui-même.
    lignes_vote, lignes_groupe = [], []
    for v in votes:
        dossier = v["dossier"] if v["dossier"] in connus else None
        lignes_vote.append((
            v["uid"], dossier, v["date"], v["numero"], v["type"], v["portee"],
            v["objet"], v["sort"], v["annonce"], v["demandeur"], v["votants"],
            v["requis"], v["pour"], v["contre"], v["abstentions"], v["nonVotants"],
        ))
        lignes_groupe += [(
            v["uid"], g["ref"], g["sigle"], g["nom"], g["membres"], g["position"],
            g["pour"], g["contre"], g["abstentions"], g["nonVotants"],
        ) for g in v["groupes"]]
    return lignes_vote, lignes_groupe


def lignes_d_amendement(archives: dict[str, pathlib.Path], connus: set[str]
                        ) -> list[tuple]:
    """Les amendements des dossiers connus, prêts à écrire."""
    # Les amendements : 110 000 sur 289 dossiers, lus au vol depuis l'archive.
    # Elle est facultative — voir FACULTATIVES — donc elle peut manquer.
    lignes_amdt = []
    for a in extraction.lire_amendements(archives["amendements"]) \
            if "amendements" in archives else ():
        if a["dossier"] not in connus:
            continue
        lignes_amdt.append((
            a["uid"], a["dossier"], a["numero"], a["ordre"], a["article"],
            a["texte"], a["ou"], a["divisionType"],
            a["auteurRef"], a["groupeRef"], a["typeAuteur"], a["dateDepot"],
            a["etat"], a["sort"], a["dispositif"], a["expose"],
            json.dumps(a["morceaux"], ensure_ascii=False),
        ))
    return lignes_amdt


def lignes_de_parole(archives: dict[str, pathlib.Path], documents: dict,
                     etapes: list[tuple], rangs: list[dict], connus: set[str]
                     ) -> tuple[list[tuple], dict[tuple, tuple]]:
    """Les prises de parole rattachées à leur dossier, et l'ampleur du débat
    de chaque amendement discuté seul."""
    # Les argumentaires : ce que les groupes ont dit du texte en séance,
    # recopié mot pour mot. Le compte rendu ne cite aucun identifiant de
    # dossier — il cite le numéro de dépôt du texte, qu'il faut rapprocher des
    # documents, la date de séance départageant les numéros ambigus.
    lignes_parole = []
    debats_amdt: dict[tuple, tuple] = {}
    if "debats" in archives:
        sigles = {g["sigle"] for g in rangs if g["sigle"]}
        par_numero = {n: refs & connus for n, refs
                      in extraction.documents_par_numero(documents).items()}
        dates_du_dossier: dict[str, set[str]] = {}
        for e in etapes:
            dates_du_dossier.setdefault(e[0], set()).add(e[6])
        for parole in extraction.lire_debats(archives["debats"], sigles):
            uid = extraction.dossier_des_numeros(
                parole["numeros"], parole["date"], par_numero, dates_du_dossier)
            if not uid:
                continue
            lignes_parole.append((
                uid, parole["seance"], parole["date"], parole["section"],
                parole["ordre"], parole["acteur_ref"], parole["nom"],
                parole["qualite"], parole["sigle"], parole["texte"],
            ))
        # Et, dans la même archive, l'ampleur du débat de chaque amendement
        # discuté seul. Le dossier se trouve comme pour une parole ; le numéro
        # de dépôt, lui, est gardé tel quel — c'est lui qui rattachera le
        # compte au bon document amendé, donc à la bonne lecture.
        for bloc in extraction.lire_debats_par_amendement(archives["debats"]):
            uid = extraction.dossier_des_numeros(
                bloc["numeros"], bloc["date"], par_numero, dates_du_dossier)
            if not uid:
                continue
            for numero_texte in bloc["numeros"]:
                cle = (uid, numero_texte, bloc["amendement"], bloc["seance"])
                # Un amendement peut revenir dans la même séance — après une
                # suspension, ou en seconde délibération. On garde le débat le
                # plus fourni plutôt que d'additionner des orateurs qui sont
                # peut-être les mêmes.
                vu = debats_amdt.get(cle)
                if not vu or bloc["orateurs"] > vu[0]:
                    debats_amdt[cle] = (bloc["orateurs"], bloc["paragraphes"],
                                        bloc["date"])
    return lignes_parole, debats_amdt


def reprendre_la_veille(connexion: sqlite3.Connection,
                        archives: dict[str, pathlib.Path]) -> dict[str, list[tuple]]:
    """Les lignes de la veille à reposer après la reconstruction, par table."""
    # **Ce qu'une source absente ne doit pas emporter avec elle.** La base est
    # reconstruite de fond en comble à chaque exécution — c'est ce qui garantit
    # qu'un amendement retiré par l'Assemblée disparaisse aussi de chez nous.
    # Mais quand l'archive n'arrive pas, il n'y a rien pour réécrire ce qu'on
    # vient d'effacer, et une minute d'indisponibilité chez eux effaçait les
    # amendements de toute la journée. Mesuré : trois publications sur six, du
    # 2026-09-20 au 2026-09-23.
    #
    # On garde donc les lignes de la veille, et on les repose après la
    # reconstruction. **Effacer ligne à ligne ne suffirait pas** : les
    # amendements, les paroles et les comptes d'orateurs pendent au dossier par
    # une clé étrangère en cascade, si bien que `DELETE FROM dossier` les
    # emporte de toute façon (vérifié le 2026-09-23 sur une base neuve).
    #
    # Seules reviennent les lignes dont le dossier existe encore : un dossier
    # que l'archive ne porte plus n'a pas à ressusciter par ses amendements.
    repris = a_reprendre(connexion, archives)
    for table, lignes in repris.items():
        print(f"  {table:<18} {len(lignes):>7,} lignes de la veille gardées",
              file=sys.stderr)
    return repris


def lignes_d_agenda(archives: dict[str, pathlib.Path]) -> list[tuple]:
    """Les questions, les débats et les votes solennels de séance, tels que
    l'agenda les publie."""
    return [(p["seance"], p["point"], p["date"], p["heure"], p["genre"],
             p["type"], p["objet"], p["dossier"])
            for p in extraction.lire_points_de_seance(archives["agenda"])]


def ecrire_les_points(connexion: sqlite3.Connection, points: list[tuple]) -> None:
    """Remplace les points d'agenda — dans la transaction de l'appelant."""
    connexion.execute("DELETE FROM point_agenda")
    connexion.executemany("INSERT INTO point_agenda VALUES (?,?,?,?,?,?,?,?)", points)


def ecrire_la_base(connexion: sqlite3.Connection, archives: dict[str, pathlib.Path],
                   connus: set[str], ref: dict, rangs: list[dict],
                   dossiers: list[tuple], etapes: list[tuple],
                   lignes_vote: list[tuple], lignes_groupe: list[tuple],
                   lignes_amdt: list[tuple], lignes_parole: list[tuple],
                   debats_amdt: dict[tuple, tuple], points: list[tuple]
                   ) -> tuple[list[tuple], list[tuple]]:
    """Une transaction, tout ou rien — les lignes de la veille reposées dedans."""
    acteurs = ref["acteurs"]
    repris = reprendre_la_veille(connexion, archives)
    with connexion:                     # une transaction, ouverte et refermée ici
        connexion.execute("DELETE FROM debat_amendement")
        connexion.execute("DELETE FROM parole")
        connexion.execute("DELETE FROM amendement")
        connexion.execute("DELETE FROM acteur")
        connexion.executemany(
            "INSERT INTO acteur VALUES (?,?,?,?,?,?,?,?,?)",
            [(x["ref"], x["civilite"], x["prenom"], x["nom"], x["groupeRef"],
              x["departement"], x["circo"], x["siege"], x["photo"])
             for x in acteurs.values()])
        connexion.execute("DELETE FROM groupe")
        connexion.executemany(
            "INSERT INTO groupe VALUES (?,?,?,?,?,?)",
            [(g["ref"], g["sigle"], g["nom"], g["rang"], g["siegeMedian"], g["couleur"])
             for g in rangs])
        connexion.execute("DELETE FROM vote_groupe")
        connexion.execute("DELETE FROM vote")
        connexion.execute("DELETE FROM etape")
        connexion.execute("DELETE FROM dossier")
        connexion.executemany(
            "INSERT INTO dossier VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", dossiers)
        connexion.executemany(
            "INSERT INTO etape VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", etapes)
        connexion.executemany(
            "INSERT INTO vote VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", lignes_vote)
        connexion.executemany(
            "INSERT INTO vote_groupe VALUES (?,?,?,?,?,?,?,?,?,?)", lignes_groupe)
        connexion.executemany(
            "INSERT INTO amendement VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", lignes_amdt)
        connexion.executemany(
            "INSERT INTO parole VALUES (?,?,?,?,?,?,?,?,?,?)", lignes_parole)
        ecrire_les_points(connexion, points)
        connexion.executemany(
            "INSERT INTO debat_amendement VALUES (?,?,?,?,?,?,?)",
            [(uid, numero_texte, numero, seance, date, orateurs, paragraphes)
             for (uid, numero_texte, numero, seance), (orateurs, paragraphes, date)
             in debats_amdt.items()])
        # Les lignes de la veille, reposées dans la même transaction : la base
        # reste « tout ou rien », et l'application affiche les amendements
        # d'hier plutôt qu'un zéro qui serait faux.
        gardees = reposer(connexion, repris, connus)
        lignes_amdt = gardees.get("amendement", lignes_amdt)
        lignes_parole = gardees.get("parole", lignes_parole)
    return lignes_amdt, lignes_parole


def ranger(connexion: sqlite3.Connection, archives: dict[str, pathlib.Path],
           aujourdhui: str) -> tuple[int, int, int, int, int]:
    """Remplace le contenu de la base par celui des archives. Tout ou rien."""
    ref = lire_les_references(archives)
    votes, par_ref, rangs = lire_les_scrutins(archives, ref["groupes"])
    dossiers, etapes = lire_les_dossiers(archives, aujourdhui, ref, par_ref)
    connus = {d[0] for d in dossiers}
    lignes_vote, lignes_groupe = lignes_de_vote(votes, connus)
    lignes_amdt = lignes_d_amendement(archives, connus)
    lignes_parole, debats_amdt = lignes_de_parole(
        archives, ref["documents"], etapes, rangs, connus)
    lignes_amdt, lignes_parole = ecrire_la_base(
        connexion, archives, connus, ref, rangs, dossiers, etapes,
        lignes_vote, lignes_groupe, lignes_amdt, lignes_parole, debats_amdt,
        lignes_d_agenda(archives))
    return len(dossiers), len(etapes), len(lignes_vote), len(lignes_amdt), len(lignes_parole)
