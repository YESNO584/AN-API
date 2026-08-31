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
    -- en_cours | promulgue | rejete | non_adopte | caduc | retire | sans_acte
    -- Aucun de ces états ne prétend qu'un texte est fini pour de bon : un texte
    -- rejeté ou non adopté peut être redéposé, et les sources ne se prononcent
    -- pas là-dessus.
    statut                  TEXT    NOT NULL,
    etat_senat              TEXT,               -- « État du dossier », mot pour mot
    etape                   INTEGER,            -- 1..6, NULL tant qu'aucun acte n'a eu lieu
    date_dernier_mouvement  TEXT,               -- AAAA-MM-JJ
    -- Ce qui suit décrit le dernier acte connu. C'est de la redondance
    -- assumée : sans elle, afficher un fil de mille textes obligerait à
    -- ouvrir mille fichiers de détail.
    chambre                 TEXT,               -- où le texte se trouve aujourd'hui
    lecture                 TEXT,               -- 1ère lecture, Nouvelle Lecture…
    dernier_acte            TEXT,               -- Discussion en séance publique…
    conclusion              TEXT,               -- adoptée, rejeté, Conforme…
    prochaine_date          TEXT,               -- séance déjà programmée, si elle existe
    prochaine_quoi          TEXT,
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

-- Les scrutins publics.
--
-- Ils ne couvrent qu'une petite partie des textes : 71 des 1 990 textes en
-- cours en avaient un le 2026-08-31, soit 3,6 %. Ce n'est pas une lacune de
-- la récupération — la plupart des textes sont adoptés à main levée, ou
-- jamais examinés. Et 7 216 des 8 434 scrutins portent sur un amendement,
-- pas sur un texte entier : d'où la colonne `portee`, sans laquelle un
-- affichage laisserait croire qu'un texte a été adopté alors qu'un seul de
-- ses amendements l'a été.
CREATE TABLE IF NOT EXISTS vote (
    uid          TEXT PRIMARY KEY,
    dossier_uid  TEXT REFERENCES dossier(uid) ON DELETE SET NULL,
    date         TEXT NOT NULL,
    numero       INTEGER,
    type         TEXT,               -- scrutin public ordinaire | solennel | motion de censure
    portee       TEXT NOT NULL,      -- ensemble | article | amendement | motion | autre
    objet        TEXT,
    sort         TEXT,               -- adopté | rejeté
    annonce      TEXT,
    demandeur    TEXT,
    votants      INTEGER,
    requis       INTEGER,
    pour         INTEGER,
    contre       INTEGER,
    abstentions  INTEGER,
    non_votants  INTEGER
);

CREATE INDEX IF NOT EXISTS vote_par_dossier ON vote (dossier_uid, date DESC);
CREATE INDEX IF NOT EXISTS vote_par_portee  ON vote (portee, date DESC);

-- Comment chaque groupe politique a voté.
--
-- `position` est **calculée sur le décompte**, pas reprise de la source :
-- celle-ci contredit son propre décompte dans 3 % des cas. Voir
-- `position_dominante()` dans extraction.py.
CREATE TABLE IF NOT EXISTS vote_groupe (
    vote_uid     TEXT NOT NULL REFERENCES vote(uid) ON DELETE CASCADE,
    organe_ref   TEXT,
    sigle        TEXT,
    nom          TEXT,
    membres      INTEGER,
    position     TEXT,               -- pour | contre | abstention | partagé | NULL
    pour         INTEGER,
    contre       INTEGER,
    abstentions  INTEGER,
    non_votants  INTEGER
);

CREATE INDEX IF NOT EXISTS vote_groupe_par_vote ON vote_groupe (vote_uid);

-- Les groupes politiques, rangés de la gauche à la droite de l'hémicycle.
--
-- `siege_median` et `rang` sont **mesurés** : chaque vote publie le numéro de
-- siège de chaque député, et l'hémicycle est numéroté de la droite vers la
-- gauche. Rien n'est écrit à la main, donc rien ne se périme.
--
-- `couleur` est en revanche une **convention d'affichage** : l'open data n'en
-- publie aucune. Voir COULEURS_GROUPES dans extraction.py.
CREATE TABLE IF NOT EXISTS groupe (
    ref           TEXT PRIMARY KEY,
    sigle         TEXT NOT NULL,
    nom           TEXT,
    rang          INTEGER NOT NULL,   -- 0 = le plus à gauche
    siege_median  REAL,
    couleur       TEXT NOT NULL
);

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
