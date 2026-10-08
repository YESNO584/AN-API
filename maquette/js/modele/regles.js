/* Les règles : ce que chaque onglet déclare, ce qu'un filtre retient, l'ordre des colonnes, la recherche sans accent, les seuils du repère des amendements disputés, le parcours d'un texte fondu avec ses votes. Rien ici ne touche l'écran. */

/* **La recherche doit être souple, parce que le clavier l'est.** « legitime »
   doit trouver « Légitime », « coeur » trouver « cœur », et « l'usage »
   trouver « l’usage » — la source écrit l'apostrophe typographique, qu'aucun
   clavier ne donne au premier coup. Trois transformations, dans cet ordre :
   les ligatures (que la décomposition Unicode ne défait pas), puis les
   accents, puis les apostrophes. */
const LIGATURES = [[/œ/g, "oe"], [/æ/g, "ae"], [/[’‘‛´`]/g, "'"]];

function normaliser(s) {
  let t = (s || "").toLowerCase();
  for (const [de, vers] of LIGATURES) t = t.replace(de, vers);
  return t.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

/* ---------- les deux onglets ---------- *
 * « Textes » : ce qui peut devenir une loi, rangé par étape du parcours.
 * « Travaux » : tout le reste — enquêtes, rapports, prises de position,
 * motions — rangé par catégorie. Ces dossiers n'aboutissent à aucune loi,
 * mais rien n'est écarté : ils ont leur onglet.
 *
 * Les deux se dessinent avec la même machinerie de colonnes. Chaque onglet
 * dit seulement ce qui le distingue : sa liste, la catégorie d'un élément,
 * l'ordre des colonnes, et la carte à dessiner.
 * ------------------------------------------------------------------ */

const VUES = {
  // À gauche des deux autres, parce que c'est l'autre chambre qu'on vient
  // chercher : le fil de l'Assemblée reste l'onglet par défaut.
  senat: {
    nom: "Sénat",
    base: () => SENAT,
    liste: () => retenus("senat"),
    total: () => SENAT.length,
    // Pas d'étape de l'Assemblée ici — l'onglet range sur celles du Sénat.
    // Pas de « Votes » non plus : les votes portés par la carte sont ceux de
    // l'Assemblée, et un filtre les donnerait pour des votes du Sénat.
    filtres: ["etapesSenat", "etat", "themes", "chambres", "types", "activite"],
    categorieDe: (t) => t.senat.moment,
    ordre: () => ETAPES_SENAT,
    cleDe: (e) => e.cle,
    // Les étapes du Sénat sont un parcours, comme celles de l'Assemblée : une
    // colonne est « derrière » la colonne ouverte. Les travaux, eux, ne se
    // traversent pas.
    parcours: true,
    // La colonne la plus avancée, comme pour les textes : c'est là que se
    // passe l'actualité du Sénat.
    ouverture: (categories) => Math.max(categories.length - 1, 0),
  },
  textes: {
    nom: "Textes",
    parcours: true,
    base: () => TEXTES,
    liste: () => retenus("textes"),
    total: () => TEXTES.length,
    filtres: ["etapes", "etat", "themes", "chambres", "types", "activite",
              "vote", "programme"],
    categorieDe: (t) => t.etape,
    ordre: () => FRISE_EN_ORDRE,
    cleDe: (e) => e.n,
    // La colonne la plus avancée : c'est là que se passe l'actualité.
    ouverture: (categories) => {
      for (let i = categories.length - 1; i >= 0; i--) {
        if (categories[i][0] !== ARRETE) return i;
      }
      return 0;
    },
  },
  travaux: {
    nom: "Travaux",
    parcours: false,
    base: () => TRAVAUX,
    liste: () => retenus("travaux"),
    total: () => TRAVAUX.length,
    // **Un travail n'a ni étape du parcours, ni vote, ni séance programmée,
    // ni sujet**, et le socle ne publie pas ces champs pour lui. Le sujet
    // surtout : mesuré le 2026-10-04, **aucun des 721 travaux n'a de dossier
    // au Sénat** — ce sont des résolutions, des commissions d'enquête, des
    // rapports, qui ne quittent jamais l'Assemblée. Un filtre « Sujet » y
    // serait vide à jamais. Un filtre qui ne trouve jamais rien ne s'affiche
    // pas.
    filtres: ["etat", "chambres", "types", "activite"],
    categorieDe: (t) => t.type,
    ordre: () => CATEGORIES_TRAVAUX,
    cleDe: (c) => c.nom,
    ouverture: () => 0,
  },
};

const vue = () => VUES[ONGLET];

/* **Les filtres valent dans les trois onglets, et chacun n'affiche que les
   siens** (2026-10-04). Avant, le panneau ne servait que l'onglet « Textes » :
   chercher « santé » au Sénat ne donnait rien, puisque la recherche était
   cachée. Un filtre absent de la liste `filtres` d'une vue n'est **ni
   dessiné, ni appliqué, ni compté** dans le badge du bouton — les trois
   doivent dire la même chose, sinon le badge annonce un filtre que le fil
   ignore. */
const aLeFiltre = (nom, v = ONGLET) => VUES[v].filtres.includes(nom);

// La catégorie affichée, décrite : son nom, ce qu'elle est, son rang.
function categorieDite(cle) {
  const liste = vue().ordre();
  const trouve = liste.find((c) => vue().cleDe(c) === cle);
  return trouve || { nom: String(cle), quoi: "" };
}

const enDate = (iso) => { const [a, m, j] = iso.split("-").map(Number); return new Date(a, m - 1, j); };

const jours = (iso) => Math.floor((Date.now() - enDate(iso)) / 86400000);

function retenus(v = ONGLET) {
  const mots = normaliser(filtres.mots.trim());
  const a = (nom) => aLeFiltre(nom, v);
  return VUES[v].base().filter((t) => {
    if (a("etat") && filtres.etat && statutDe(t) !== filtres.etat) return false;
    if (a("etapes") && filtres.etapes.size && !filtres.etapes.has(t.etape)) return false;
    // L'onglet du Sénat range sur les étapes du Sénat : c'est donc sur
    // celles-là qu'il filtre, et jamais sur celles de l'Assemblée.
    if (a("etapesSenat") && filtres.etapesSenat.size
        && !filtres.etapesSenat.has((t.senat || {}).moment)) return false;
    if (a("chambres") && filtres.chambres.size
        && !filtres.chambres.has(t.chambre || "aucune")) return false;
    if (a("types") && filtres.types.size && !filtres.types.has(t.type)) return false;
    // Un texte sans thème n'est pas « hors sujet » : il n'est jamais allé au
    // Sénat, qui est le seul à classer. Le filtre l'écarte, et le dit.
    if (a("themes") && filtres.themes.size
        && !(t.themes || []).some((x) => filtres.themes.has(x))) return false;
    if (a("programme") && filtres.programme && !t.prochaine_date) return false;
    if (a("vote") && filtres.vote) {
      const v = filtres.vote;
      if (v === "tous" && !t.votes) return false;
      if (v === "ensemble" && !t.voteEnsemble) return false;
      if (v === "adopte" && !(t.voteEnsemble && t.voteEnsemble.sort === "adopté")) return false;
      if (v === "rejete" && !(t.voteEnsemble && t.voteEnsemble.sort !== "adopté")) return false;
    }
    if (a("activite") && filtres.activite) {
      const seuil = ACTIVITE[filtres.activite][1];
      const age = jours(t.date_dernier_mouvement);
      if (seuil > 0 ? age > seuil : age < -seuil) return false;
    }
    if (mots && !normaliser(t.titre).includes(mots)) return false;
    return true;
  });
}

/* Le badge du bouton « Filtres » ne compte que ce que **cet onglet** applique.
   Sans cette restriction, un filtre d'étape posé dans « Textes » comptait pour
   un dans « Travaux », qui ne s'en sert pas : le badge annonçait un filtre que
   le fil ignorait. */
function combienActifs(v = ONGLET) {
  const a = (nom) => aLeFiltre(nom, v);
  return (a("etapes") ? filtres.etapes.size : 0)
       + (a("etapesSenat") ? filtres.etapesSenat.size : 0)
       + (a("chambres") ? filtres.chambres.size : 0)
       + (a("types") ? filtres.types.size : 0)
       + (a("themes") ? filtres.themes.size : 0)
       + (a("activite") && filtres.activite ? 1 : 0)
       + (a("programme") && filtres.programme ? 1 : 0)
       + (a("vote") && filtres.vote ? 1 : 0)
       + (a("etat") && filtres.etat ? 1 : 0);
}

/* ---------- les colonnes ---------- *
 * Une colonne par catégorie d'étape, côte à côte, **dans l'ordre du parcours** :
 * le dépôt à gauche, la promulgation à droite. Le fil se lit donc comme une
 * frise, de la plus ancienne étape à la plus récente. Une seule colonne est
 * visible ; on passe à la suivante en faisant glisser, ou avec les flèches.

 *
 * Chaque colonne charge ses textes par paquets, pour elle seule. Un compteur
 * commun à tout le fil ne marcherait plus ici : les dernières colonnes
 * resteraient vides jusqu'à ce qu'on ait tout affiché dans les premières.
 * ------------------------------------------------------------------ */

// Les textes rangés par étape, les colonnes remises dans l'ordre du parcours.
// L'ordre des textes *à l'intérieur* d'une colonne ne bouge pas : c'est celui
// de la liste, déjà triée. Les étapes sans texte n'ont pas d'entrée — une
// colonne vide ne s'affiche pas.
function parCategorie(liste) {
  const paquets = new Map();
  for (const t of liste) {
    const cle = vue().categorieDe(t);
    if (!paquets.has(cle)) paquets.set(cle, []);
    paquets.get(cle).push(t);
  }
  const ordre = vue().ordre();
  const rangDe = (cle) => {
    const i = ordre.findIndex((c) => vue().cleDe(c) === cle);
    return i === -1 ? ordre.length : i;
  };
  return [...paquets.entries()].sort((a, x) => rangDe(a[0]) - rangDe(x[0]));
}

// La catégorie la plus avancée du parcours : celle sur laquelle le fil
// s'ouvre. C'est là que se passe l'actualité — les 1 729 textes restés au
// dépôt sont à un glissement de là, vers la gauche. « Arrêté en chemin » ne
// compte pas : ce n'est pas une étape mais une sortie de route.
function colonneDOuverture(categories) {
  return vue().ouverture(categories);
}

// La place d'une catégorie dans l'ordre des colonnes de l'onglet courant.
// Les étapes de l'Assemblée se comparent par leur numéro ; celles du Sénat
// n'en ont pas, et c'est leur rang qui dit laquelle vient avant l'autre.
function rangDansLOrdre(cle) {
  return vue().ordre().findIndex((c) => vue().cleDe(c) === cle);
}

// Le numéro que l'objet d'un scrutin nomme : « l'amendement n° 885 (rect.) du
// Gouvernement à l'article 3 du projet de loi… ». Le premier nommé seulement —
// un objet qui ajoute « et les amendements identiques suivants » ne dit pas
// lesquels.
const NUMERO_D_AMENDEMENT = /(l['’]amendement|le sous-amendement)\s+n°\s*(\d+(?:\s*\(rect[^)]*\))?)/i;

/* Étapes et votes dans un seul fil, par date. Les étapes d'un même jour
   gardent l'ordre du fichier source ; les votes de ce jour-là viennent
   ensuite, parce que **l'open data ne dit pas à quel moment de la journée un
   scrutin a eu lieu** — son champ `referenceLegislative` est vide dans les
   8 434 scrutins de la législature (mesuré le 2026-08-31). */
function filDuParcours(d) {
  const items = [];
  (d.parcours || []).forEach((e, i) => items.push({ date: e.date, rang: [0, i], e }));
  (d.votes || []).forEach((v, i) => items.push({ date: v.date, rang: [1, i], v }));
  // Les scrutins du Sénat, à leur date, **à côté de ceux de l'Assemblée et
  // jamais mêlés à eux** : chaque ligne dit sa chambre, et rien n'additionne
  // ni ne compare les deux. Les chiffres viennent de l'open data du Sénat, le
  // lien avec le texte de ses pages de scrutins publics.
  (d.votesSenat || []).forEach((v, i) => items.push({ date: v.date, rang: [2, i], s: v }));
  items.sort((a, b) => a.date.localeCompare(b.date) ||
                       a.rang[0] - b.rang[0] || a.rang[1] - b.rang[1]);
  return items;
}

/* Ce que la loi change au droit se lit en deux endroits, parce que ce sont
   deux questions. **Quand elle s'applique est une question sur le texte
   entier** : c'est la première chose qu'on vient vérifier devant une loi
   promulguée, elle passe donc avant son titre. Le détail de ses articles,
   lui, est une rubrique parmi d'autres — il est dans son onglet, plus bas. */
function laLoiDeLaFiche(uid, d) {
  return d.statut === "promulgue" && !ETAT.droitConsolideIndisponible
    ? { ...d, uid, change: (TEXTES.find((x) => x.uid === uid) || {}).change,
        etape: PROMULGUEE }
    : null;
}

/* Un amendement « débattu » : adopté de justesse, après un long échange.
 *
 * Les deux seuils sont ici, et pas dans le socle, parce que c'est un choix
 * d'affichage : le socle publie les chiffres bruts — le scrutin et le nombre
 * d'orateurs — et ne tranche rien.
 *
 * **Le repère ne dit pas « controversé », et c'est voulu.** Mesuré le
 * 2026-09-20 sur les 967 amendements dont on connaît à la fois le vote et le
 * débat : le volume de débat et le serré du vote sont indépendants
 * (corrélation de rang −0,07). Un amendement voté 54 contre 54 a eu 48
 * paragraphes de débat, un autre voté 50 contre 50 en a eu 12. Le repère dit
 * donc ce qu'il compte, et rien de plus.
 *
 * Avec ces seuils, 4 amendements sur les 183 mesurables de la législature le
 * portent — dont celui qui permet de suspendre le permis de conduire d'un
 * usager de stupéfiants, adopté 39 contre 37 après 15 orateurs. */
const ECART_DEBATTU = 0.10;

const ORATEURS_DEBATTU = 8;

const estDebattu = (a) => Boolean(
  a.vote && a.debat && a.vote.ecart != null && a.vote.ecart < ECART_DEBATTU
  && a.debat.orateurs >= ORATEURS_DEBATTU);

// L'écart d'un scrutin, en part des suffrages exprimés : un 39 contre 37 et un
// 390 contre 370 se lisent pareil. Le socle le calcule déjà pour un amendement
// rattaché à un article ; le parcours, lui, part du scrutin brut.
function ecartDuVote(v) {
  const exprimes = (v.pour || 0) + (v.contre || 0);
  return exprimes ? Math.abs(v.pour - v.contre) / exprimes : null;
}

/* L'ordre d'affichage : ce qu'on sait le plus, d'abord. Les amendements dont
   on ne sait rien gardent l'ordre de la source — un tri stable ne les
   mélange pas entre eux. */
function rangAmendement(a) {
  if (estDebattu(a)) return 0;
  if (a.vote && a.debat) return 1;
  if (a.vote || a.debat) return 2;
  return 3;
}

function amendementsClasses(liste) {
  return liste
    .map((a, i) => [a, i])
    .sort(([a, ia], [b, ib]) =>
      rangAmendement(a) - rangAmendement(b)
      // À rang égal, le vote le plus serré passe devant ; à défaut de vote,
      // le débat le plus fourni.
      || ((a.vote ? a.vote.ecart : 2) - (b.vote ? b.vote.ecart : 2))
      || ((b.debat ? b.debat.orateurs : 0) - (a.debat ? a.debat.orateurs : 0))
      || ia - ib)
    .map(([a]) => a);
}

/* Les amendements d'un texte que le socle a pu **mesurer** : ceux dont on
   connaît à la fois le scrutin et le nombre d'orateurs. Ce sont les seuls sur
   lesquels le repère peut se prononcer. Les deux seuils restent ici, dans la
   maquette, parce que c'est un choix d'affichage : le socle publie les
   chiffres et ne tranche rien. */
const amendementsDisputes = (t) =>
  (t.amendementsMesurables || []).filter(estDebattu);

/* ------------------------------------------------------------------ *
 * Les versions successives d'un texte
 *
 * Un texte de loi n'est pas figé : il est déposé, puis la commission le
 * réécrit, puis la séance le réécrit encore. L'Assemblée publie chacune de
 * ces versions ; l'écran les montre **superposées**, comme les rédactions
 * d'un article de loi — ce qui a été retiré en rouge barré, ce qui a été
 * ajouté en vert.
 *
 * À côté de chaque article changé, **les amendements adoptés sur cet
 * article** : leur numéro, leur auteur, son groupe. Le rapprochement se fait
 * par le numéro d'article, jamais par le texte — dire quel mot vient de quel
 * amendement demanderait d'interpréter l'instruction de l'amendement, donc de
 * fabriquer du texte de loi. Mesuré le 2026-09-18 : 420 amendements adoptés
 * sur 470 tombent sur un article qui a réellement changé, 2 sur un article
 * resté identique — le rapprochement est presque toujours juste, et souvent
 * incomplet. **Un article sans amendement le dit.**
 * ------------------------------------------------------------------ */

// Ce que le compte d'une version annonce, sous son nom, dans le parcours.

function chiffresDeVersion(r) {
  if (!r) return "";
  if (r.initiaux) return `${nb.format(r.initiaux)} article${r.initiaux > 1 ? "s" : ""}`;
  const bouts = [];
  // « 3 articles modifiés » plutôt que « 3 modifiés » : le premier morceau
  // porte le mot, les suivants s'y rattachent.
  if (r.modifies) bouts.push(`${nb.format(r.modifies)} article${r.modifies > 1 ? "s" : ""} `
                             + `modifié${r.modifies > 1 ? "s" : ""}`);
  if (r.nouveaux) bouts.push(`${nb.format(r.nouveaux)} `
                             + (bouts.length ? "" : `article${r.nouveaux > 1 ? "s" : ""} `)
                             + `nouveau${r.nouveaux > 1 ? "x" : ""}`);
  if (r.retires) bouts.push(`${nb.format(r.retires)} `
                            + (bouts.length ? "" : `article${r.retires > 1 ? "s" : ""} `)
                            + `retiré${r.retires > 1 ? "s" : ""}`);
  // Une version qui ne change rien est un fait, pas un vide : la commission
  // peut adopter le texte sans y toucher.
  return bouts.length ? bouts.join(", ")
                      : `aucun changement sur ${nb.format(r.total)} article${r.total > 1 ? "s" : ""}`;
}

/* ---------- l'onglet « Texte » ---------- *
 * Le contenu réel d'un projet ou d'une proposition de loi, que la fiche ne
 * montrait nulle part : il n'existait qu'au fond du parcours, une version à la
 * fois. Trois choses ici, et pas une de plus :
 *
 *   — le texte **déposé**, celui qu'on a voulu faire voter ;
 *   — ce que la **dernière version** a changé, différences comprises ;
 *   — cette dernière version **à jour**, sans les différences, telle qu'elle
 *     se lit aujourd'hui.
 *
 * Chaque partie se charge à la demande : une version pèse jusqu'à 2,8 Mo
 * (mesuré le 2026-09-19 sur le projet de loi de finances pour 2026), et
 * personne n'ouvre les trois à la fois. Quand le socle n'a lu aucune
 * version — les textes déposés au Sénat, qui publie ses documents ailleurs —
 * l'onglet le dit au lieu d'afficher un cadre vide.
 * ------------------------------------------------------------------ */

/* Les articles sur lesquels une liste d'amendements a un sens : ceux qui ont
   bougé. Un article inchangé n'a pas d'amendement adopté par définition, et
   lui afficher « la source ne relie ce changement à aucun amendement »
   nommerait un changement qui n'a pas eu lieu. Un article initial non plus :
   la version déposée ne vient d'aucun amendement. */
const A_CHANGE = new Set(["modifie", "nouveau", "retire"]);

/* ---------- la description du texte ---------- *
 * Écrite, et non recopiée : c'est la seule rubrique de l'application dans ce
 * cas. Une phrase d'accroche, puis une puce par mesure concrète — un pavé de
 * six lignes se saute, une liste se parcourt.
 *
 * Elle porte son origine à l'écran, en toutes lettres — une icône,
 * un mot, et l'explication complète au toucher. Le `title` sert l'ordinateur,
 * où le survol existe ; le bouton sert le téléphone, où il n'existe pas. Les
 * deux disent la même chose : sans le bouton, la mention serait invisible sur
 * la moitié des écrans.
 * ------------------------------------------------------------------ */

// Combien de mesures s'affichent avant qu'il faille les demander.
const VISIBLES = 3;

/* Femmes et hommes, comptés sur la civilité imprimée par la source. Un député
   dont la civilité manque n'est compté ni d'un côté ni de l'autre : mieux vaut
   un total qui ne tombe pas juste qu'un classement inventé. */
function femmesEtHommes(deputes) {
  let femmes = 0, hommes = 0;
  for (const x of deputes || []) {
    if (x.civilite === "Mme") femmes++;
    else if (x.civilite === "M.") hommes++;
  }
  return { femmes, hommes };
}

function moisVoisin(mois, pas) {
  const [a, m] = mois.split("-").map(Number);
  const d = new Date(a, m - 1 + pas, 1);
  return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0");
}

const moisDe = (iso) => iso.slice(0, 7);

const aujourdhui = () => new Date().toISOString().slice(0, 10);
