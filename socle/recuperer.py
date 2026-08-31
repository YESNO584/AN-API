#!/usr/bin/env python3
"""Récupère les dossiers législatifs et les range dans la base.
Ce que fait ce programme, une fois par jour :
1. Il demande l'archive à l'Assemblée **en disant ce qu'il a déjà**. Si rien
   n'a changé, le serveur répond « 304 » et les 10 Mo ne sont pas retéléchargés.
2. Il lit l'archive et classe chaque dossier (voir `extraction.py`).
3. Il remplace le contenu de la base **en une seule transaction** : soit tout
   passe, soit rien ne bouge. Il n'y a jamais de base à moitié remplie.
4. Il écrit une ligne dans le journal. C'est ce qui rend une panne visible.
Usage :
    ./recuperer.py                  # cycle normal
    ./recuperer.py --forcer         # ignore le « rien n'a changé »
    ./recuperer.py --zip fichier    # depuis une archive locale, sans réseau
    ./recuperer.py --journal        # affiche les dernières exécutions
À programmer une fois par jour, par exemple :
    17 6 * * *  cd /chemin/socle && ./recuperer.py >> recuperer.log 2>&1
"""
from __future__ import annotations
import argparse
import collections
import datetime as dt
import hashlib
import json
import pathlib
import sqlite3
import sys
import tempfile
import extraction
RACINE = pathlib.Path(__file__).resolve().parent
BASE = RACINE / "parlement.db"
SCHEMA = RACINE / "schema.sql"
def maintenant() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
def ouvrir(chemin: pathlib.Path) -> sqlite3.Connection:
    connexion = sqlite3.connect(chemin)
    connexion.row_factory = sqlite3.Row
    connexion.executescript(SCHEMA.read_text(encoding="utf-8"))
    return connexion
# Les trois jeux dont le socle a besoin. Les groupes politiques ne sont pas un
# supplément : les scrutins ne nomment pas les groupes, ils y renvoient par un
# identifiant. Sans cette table, « PO845401 a voté contre » n'apprend rien.
SOURCES = {
    "dossiers": extraction.URL_ARCHIVE,
    "scrutins": extraction.URL_SCRUTINS,
    "groupes": extraction.URL_ORGANES,
    "senat": extraction.URL_SENAT,
    "amendements": extraction.URL_AMENDEMENTS,
}
def connue(connexion: sqlite3.Connection, url: str) -> sqlite3.Row | None:
    return connexion.execute("SELECT * FROM source WHERE url = ?", (url,)).fetchone()
def entetes_conditionnelles(ligne: sqlite3.Row | None) -> dict[str, str]:
    """De quoi demander « seulement si ça a changé » et économiser 10 Mo."""
    if not ligne:
        return {}
    entetes = {}
    if ligne["etag"]:
        entetes["If-None-Match"] = ligne["etag"]
    if ligne["modifie_le"]:
        entetes["If-Modified-Since"] = ligne["modifie_le"]
    return entetes
def empreinte(fichier: pathlib.Path) -> str:
    """Le sha256 de l'archive, lu par morceaux pour ne pas la charger en mémoire."""
    condensat = hashlib.sha256()
    with fichier.open("rb") as flux:
        for morceau in iter(lambda: flux.read(1 << 20), b""):
            condensat.update(morceau)
    return condensat.hexdigest()
def ranger(connexion: sqlite3.Connection, archives: dict[str, pathlib.Path],
           aujourdhui: str) -> tuple[int, int, int]:
    """Remplace le contenu de la base par celui des archives. Tout ou rien."""
    groupes = extraction.lire_groupes(archives["groupes"])
    acteurs = extraction.lire_acteurs(archives["groupes"])
    documents = extraction.lire_documents(archives["dossiers"])
    etats_senat = extraction.lire_senat(archives["senat"])
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
    dossiers, etapes = [], []
    for brut in extraction.lire_archive(archives["dossiers"]):
        dp = brut["dossierParlementaire"]
        # Le dossier cite parfois ses scrutins ; le scrutin nomme parfois son
        # dossier. Aucun des deux sens ne suffit seul : réunis, ils font passer
        # la couverture de 34 et 68 textes à 71 (mesuré le 2026-08-31).
        for ref in extraction.refs_de_vote(dp):
            if ref in par_ref and not par_ref[ref]["dossier"]:
                par_ref[ref]["dossier"] = dp["uid"]
        d = extraction.analyser(brut, aujourdhui, etats_senat)
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
        ) for e in d["etapes"]]
    connus = {d[0] for d in dossiers}
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
    # Les amendements : 110 000 sur 289 dossiers, lus au vol depuis l'archive.
    lignes_amdt = []
    for a in extraction.lire_amendements(archives["amendements"]):
        if a["dossier"] not in connus:
            continue
        lignes_amdt.append((
            a["uid"], a["dossier"], a["numero"], a["ordre"], a["article"],
            a["auteurRef"], a["groupeRef"], a["typeAuteur"], a["dateDepot"],
            a["etat"], a["sort"], a["dispositif"], a["expose"],
            json.dumps(a["morceaux"], ensure_ascii=False),
        ))
    with connexion:                     # une transaction, ouverte et refermée ici
        connexion.execute("DELETE FROM amendement")
        connexion.execute("DELETE FROM acteur")
        connexion.executemany(
            "INSERT INTO acteur VALUES (?,?,?,?,?,?)",
            [(x["ref"], x["civilite"], x["prenom"], x["nom"], x["groupeRef"], x["photo"])
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
            "INSERT INTO etape VALUES (?,?,?,?,?,?,?,?,?,?,?)", etapes)
        connexion.executemany(
            "INSERT INTO vote VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", lignes_vote)
        connexion.executemany(
            "INSERT INTO vote_groupe VALUES (?,?,?,?,?,?,?,?,?,?)", lignes_groupe)
        connexion.executemany(
            "INSERT INTO amendement VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", lignes_amdt)
    return len(dossiers), len(etapes), len(lignes_vote), len(lignes_amdt)
def afficher_journal(connexion: sqlite3.Connection, combien: int = 10) -> None:
    lignes = connexion.execute(
        "SELECT * FROM journal ORDER BY id DESC LIMIT ?", (combien,)).fetchall()
    if not lignes:
        print("Le journal est vide : le programme n'a encore jamais tourné.")
        return
    print(f"{'début':<27}{'statut':<10}{'dossiers':>9}{'étapes':>9}  message")
    for l in lignes:
        print(f"{l['debut']:<27}{l['statut']:<10}"
              f"{l['dossiers_lus'] or 0:>9}{l['etapes_ecrites'] or 0:>9}  {l['message'] or ''}")
def main() -> int:
    analyseur = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analyseur.add_argument("--forcer", action="store_true",
                           help="recharger même si la source est inchangée")
    analyseur.add_argument("--zip", nargs=len(SOURCES),
                           metavar=tuple(n.upper() for n in SOURCES),
                           type=pathlib.Path,
                           help="lire des fichiers locaux au lieu de les télécharger")
    analyseur.add_argument("--base", type=pathlib.Path, default=BASE,
                           help=f"fichier de base de données (défaut : {BASE.name})")
    analyseur.add_argument("--journal", action="store_true",
                           help="afficher les dernières exécutions et s'arrêter")
    options = analyseur.parse_args()
    if options.zip:
        options.zip = dict(zip(SOURCES, options.zip))
    connexion = ouvrir(options.base)
    if options.journal:
        afficher_journal(connexion)
        return 0
    debut = maintenant()
    aujourdhui = dt.date.today().isoformat()
    curseur = connexion.execute(
        "INSERT INTO journal (debut, statut) VALUES (?, 'en_cours')", (debut,))
    execution = curseur.lastrowid
    connexion.commit()
    def clore(statut: str, *, octets=None, dossiers=None, etapes=None, message=None) -> None:
        connexion.execute(
            "UPDATE journal SET fin=?, statut=?, octets=?, dossiers_lus=?,"
            " etapes_ecrites=?, message=? WHERE id=?",
            (maintenant(), statut, octets, dossiers, etapes, message, execution))
        connexion.commit()
    try:
        with tempfile.TemporaryDirectory() as travail:
            archives, comptes_rendus = {}, {}
            if options.zip:
                for nom, chemin in options.zip.items():
                    if not chemin.exists():
                        raise FileNotFoundError(f"archive introuvable : {chemin}")
                    archives[nom] = chemin
                    comptes_rendus[nom] = {"octets": chemin.stat().st_size}
                    print(f"Archive locale ({nom}) : {chemin}", file=sys.stderr)
            else:
                inchangees = 0
                for nom, url in SOURCES.items():
                    precedente = None if options.forcer else connue(connexion, url)
                    chemin = pathlib.Path(travail) / f"{nom}.zip"
                    cr = extraction.telecharger(
                        chemin, entetes_conditionnelles(precedente), url)
                    if not cr["modifie"]:
                        # Le serveur dit « rien de neuf » : on garde la copie de
                        # la fois précédente. Elle n'existe pas ici — la machine
                        # est neuve à chaque exécution — donc on retélécharge
                        # sans condition plutôt que de travailler sans elle.
                        cr = extraction.telecharger(chemin, None, url)
                        inchangees += 1
                    cr["empreinte"] = empreinte(chemin)
                    if precedente and cr["empreinte"] == precedente["empreinte"]:
                        inchangees += 1
                    archives[nom], comptes_rendus[nom] = chemin, cr
                    print(f"  {nom:<10} {cr['octets']:>12,} octets", file=sys.stderr)
                if inchangees == len(SOURCES) and not options.forcer:
                    for nom, url in SOURCES.items():
                        connexion.execute(
                            "UPDATE source SET etag=?, modifie_le=?, vu_le=? WHERE url=?",
                            (comptes_rendus[nom]["etag"], comptes_rendus[nom]["modifieLe"],
                             maintenant(), url))
                    clore("inchange",
                          octets=sum(c["octets"] for c in comptes_rendus.values()),
                          message="aucune des trois sources n'a changé")
                    print("Rien n'a changé côté Assemblée : base laissée telle quelle.",
                          file=sys.stderr)
                    return 0
            dossiers, etapes, votes, amendements = ranger(connexion, archives, aujourdhui)
        if not options.zip:
            for nom, url in SOURCES.items():
                cr = comptes_rendus[nom]
                connexion.execute(
                    "INSERT INTO source (url, etag, modifie_le, empreinte, vu_le)"
                    " VALUES (?,?,?,?,?)"
                    " ON CONFLICT(url) DO UPDATE SET etag=excluded.etag,"
                    " modifie_le=excluded.modifie_le, empreinte=excluded.empreinte,"
                    " vu_le=excluded.vu_le",
                    (url, cr["etag"], cr["modifieLe"], cr["empreinte"], maintenant()))
        clore("succes", octets=sum(c["octets"] for c in comptes_rendus.values()),
              dossiers=dossiers, etapes=etapes,
              message=f"{votes} scrutins, {amendements} amendements")
    except Exception as erreur:                       # noqa: BLE001 — on veut tout journaliser
        clore("echec", message=f"{type(erreur).__name__}: {erreur}")
        print(f"Échec : {type(erreur).__name__}: {erreur}", file=sys.stderr)
        return 1
    print("Textes de loi, par issue :", file=sys.stderr)
    for l in connexion.execute(
            "SELECT statut, COUNT(*) n FROM dossier WHERE est_loi = 1"
            " GROUP BY statut ORDER BY n DESC"):
        print(f"     {l['n']:5d}  {l['statut']}", file=sys.stderr)
    resume = connexion.execute("""
        SELECT etape, COUNT(*) n FROM dossier
         WHERE statut = 'en_cours' AND est_loi = 1 AND etape IS NOT NULL
         GROUP BY etape ORDER BY etape""").fetchall()
    print(f"\n{dossiers} dossiers, {etapes} étapes, {votes} scrutins,"
          f" {amendements} amendements rangés.", file=sys.stderr)
    lie = connexion.execute(
        "SELECT COUNT(DISTINCT dossier_uid) n FROM vote WHERE dossier_uid IS NOT NULL"
    ).fetchone()["n"]
    print(f"Scrutins rattachés à {lie} dossiers.", file=sys.stderr)
    ordre = connexion.execute(
        "SELECT sigle FROM groupe ORDER BY rang").fetchall()
    if ordre:
        print("Groupes, de gauche à droite : "
              + " · ".join(l["sigle"] for l in ordre), file=sys.stderr)
    print("Textes de loi en cours, par étape :", file=sys.stderr)
    for numero, nom, _ in extraction.ETAPES:
        n = next((l["n"] for l in resume if l["etape"] == numero), 0)
        print(f"     {n:5d}  {numero}. {nom}", file=sys.stderr)
    return 0
if __name__ == "__main__":
    sys.exit(main())
