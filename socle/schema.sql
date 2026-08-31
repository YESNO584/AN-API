-- Modèle de données du socle — §3.1 de ../docs/PLAN.md
--
-- « Un dossier, des étapes datées, chacune rattachée à une chambre. »
-- C'est la forme dans laquelle l'Assemblée publie, et celle qui permet
-- d'afficher un parcours sans rien recalculer.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS dossier (
    uid                     TEXT PRIMARY KEY,
    legislature             TEXT    NOT NULL,
    titre                   TEXT    NOT NULL,
    titre_chemin            TEXT,
    type                    TEXT    NOT NULL,   -- procédure parlementaire, mot pour mot
    est_loi                 INTEGER NOT NULL,   -- 0 : résolution, rapport, mission… pas une loi
    chambre_initiale        TEXT,               -- assemblee | senat
    statut                  TEXT    NOT NULL,   -- en_cours | promulgue | retire | sans_acte
    etape                   INTEGER,            -- 1..6, NULL tant qu'aucun acte n'a eu lieu
    date_dernier_mouvement  TEXT,               -- AAAA-MM-JJ
    url_an                  TEXT,
    url_senat               TEXT,               -- publiée par l'Assemblée : aucun rapprochement à faire
    loi_numero              TEXT,
    loi_date                TEXT,
    loi_url_jo              TEXT
);

CREATE INDEX IF NOT EXISTS dossier_par_etape
    ON dossier (statut, est_loi, etape, date_dernier_mouvement DESC);
CREATE INDEX IF NOT EXISTS dossier_par_mouvement
    ON dossier (date_dernier_mouvement DESC);

CREATE TABLE IF NOT EXISTS etape (
    dossier_uid TEXT    NOT NULL REFERENCES dossier(uid) ON DELETE CASCADE,
    uid         TEXT,
    code        TEXT    NOT NULL,   -- AN1-DEBATS-SEANCE
    lecture     TEXT,               -- 1ère lecture, Nouvelle Lecture…
    libelle     TEXT,               -- Discussion en séance publique
    chambre     TEXT,               -- assemblee | senat | NULL (CMP, Conseil constitutionnel)
    date        TEXT    NOT NULL,
    rang        INTEGER NOT NULL,   -- position dans le fichier source : l'Assemblée
                                    -- range les lectures dans l'ordre où elles ont eu
                                    -- lieu, ce qui départage deux actes du même jour
    numero      INTEGER NOT NULL,   -- l'étape des six à laquelle cet acte appartient
    conclusion  TEXT,               -- adoptée, rejeté, Conforme…
    future      INTEGER NOT NULL    -- 1 : séance programmée, pas encore tenue
);

CREATE INDEX IF NOT EXISTS etape_par_dossier ON etape (dossier_uid, date);

-- Ce que le socle sait de la source, pour ne rien refaire inutilement.
--
-- `empreinte` n'est pas un luxe. L'Assemblée sert cette archive depuis
-- plusieurs machines qui ne publient pas toutes la même génération du
-- fichier : deux appels successifs peuvent renvoyer des `ETag` et des
-- `Last-Modified` différents pour un contenu identique (constaté le
-- 2026-08-31 : 06:16 et 10:16 en alternance). Se fier aux seuls en-têtes
-- ferait donc rebâtir la base pour rien une fois sur deux.
CREATE TABLE IF NOT EXISTS source (
    url         TEXT PRIMARY KEY,
    etag        TEXT,
    modifie_le  TEXT,               -- Last-Modified renvoyé par le serveur
    empreinte   TEXT,               -- sha256 de l'archive réellement reçue
    vu_le       TEXT NOT NULL       -- horodatage de notre dernier appel
);

-- Une ligne par exécution : c'est ce qui rend une panne visible.
CREATE TABLE IF NOT EXISTS journal (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    debut         TEXT NOT NULL,
    fin           TEXT,
    statut        TEXT NOT NULL,    -- succes | inchange | echec
    octets        INTEGER,
    dossiers_lus  INTEGER,
    etapes_ecrites INTEGER,
    message       TEXT
);
