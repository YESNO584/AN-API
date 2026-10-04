-- La base du Sénat, séparée de celle de l'Assemblée — et c'est voulu.
--
-- Les deux ne se remplissent pas aux mêmes heures, ne cassent pas pour les
-- mêmes raisons, et n'ont pas les mêmes règles de lecture. Les garder dans le
-- même fichier obligeait à tout refaire quand l'une des deux bougeait. C'est le
-- même motif que `legi.db` et `textes.db`, pour la même raison.
--
-- **Le pont entre les deux est une seule colonne : `signet`.** Le Sénat appelle
-- ainsi l'adresse courte d'un dossier (`pjl25-689`) ; l'Assemblée publie la
-- même pour chacun de ses textes, dans `dossier.url_senat`. Le rapprochement
-- est donc une lecture, pas une devinette — 730 de nos 731 textes passés au
-- Sénat s'y retrouvent (mesuré le 2026-10-04).

CREATE TABLE IF NOT EXISTS source (
    url        TEXT PRIMARY KEY,
    etag       TEXT,
    modifie_le TEXT,
    vu_le      TEXT,
    empreinte  TEXT
);

-- Un dossier vu par le Sénat. On n'en garde que de quoi faire le pont et
-- nommer ce qu'on affiche : le titre vient de chez nous pour les textes qu'on
-- suit déjà.
CREATE TABLE IF NOT EXISTS dossier_senat (
    signet TEXT PRIMARY KEY,
    loicod TEXT,
    titre  TEXT,
    etat   TEXT                    -- le code d'état du Sénat (01 à 06)
);

-- Un scrutin public du Sénat. `signet` vient des pages de scrutins publics du
-- site, pas de l'open data : **aucun fichier publié ne relie un scrutin à un
-- texte**, et c'est la seule raison pour laquelle on lit une page web.
-- Il peut rester vide : un scrutin sur une déclaration du Gouvernement ne porte
-- sur aucun texte.
CREATE TABLE IF NOT EXISTS scrutin_senat (
    session     INTEGER NOT NULL,
    numero      INTEGER NOT NULL,
    signet      TEXT,
    date        TEXT,
    objet       TEXT,
    pour        INTEGER,
    contre      INTEGER,
    abstentions INTEGER,
    PRIMARY KEY (session, numero)
);

CREATE INDEX IF NOT EXISTS scrutin_senat_par_signet
    ON scrutin_senat (signet);

-- Qui a voté quoi, groupe par groupe. Le groupe est celui **du jour du
-- scrutin**, relevé dans l'historique des appartenances : un sénateur change de
-- groupe, et lui donner son groupe d'aujourd'hui ferait dire au passé ce qu'il
-- n'a pas dit.
CREATE TABLE IF NOT EXISTS vote_groupe_senat (
    session     INTEGER NOT NULL,
    numero      INTEGER NOT NULL,
    groupe      TEXT    NOT NULL,
    pour        INTEGER NOT NULL DEFAULT 0,
    contre      INTEGER NOT NULL DEFAULT 0,
    abstentions INTEGER NOT NULL DEFAULT 0,
    non_votants INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (session, numero, groupe)
);

-- Les sénateurs en exercice. **Pas de photo** : les mentions légales du Sénat
-- couvrent les photographies par le droit d'auteur (vérifié le 2026-10-04).
CREATE TABLE IF NOT EXISTS senateur (
    matricule       TEXT PRIMARY KEY,
    civilite        TEXT,
    prenom          TEXT,
    nom             TEXT,
    groupe          TEXT,           -- le sigle, ou NULL : 179 sur 348 n'en ont
    circonscription TEXT,           -- plus depuis le renouvellement de 2026
    serie           TEXT,
    siege           INTEGER         -- 280 sur 348 en ont un
);

-- Les groupes politiques du Sénat, et leur rang de la gauche à la droite.
-- **Ce rang n'est pas mesuré sur les sièges**, contrairement à l'Assemblée :
-- la numérotation du Sénat tourne rang par rang, le groupe change 152 fois en
-- la suivant, et aucun plan de salle n'est publié. Il est mesuré sur la façon
-- de voter — voir `senat.rang_par_les_votes`.
CREATE TABLE IF NOT EXISTS groupe_senat (
    sigle    TEXT PRIMARY KEY,
    nom      TEXT,
    effectif INTEGER NOT NULL DEFAULT 0,
    rang     INTEGER
);

-- Les séances à venir, et le texte qu'elles examinent. C'est le calendrier.
CREATE TABLE IF NOT EXISTS seance_senat (
    date   TEXT NOT NULL,
    signet TEXT NOT NULL,
    PRIMARY KEY (date, signet)
);
