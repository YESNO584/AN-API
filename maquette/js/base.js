/* Les aides que tout le reste emploie : l'adresse du socle, les formats de date, la recherche sans accent, les vues et ce qu'elles déclarent, les listes chargées au démarrage. */

// D'où viennent les données.
//
// Par défaut : à côté de la page. La maquette est publiée au même endroit
// que les fichiers du socle, donc une adresse relative marche partout — en
// ligne, en local, ou depuis un dossier copié ailleurs.
//
// `?socle=http://…` vise un autre socle : utile pour essayer une
// modification avant de la publier, ou pour ouvrir la page depuis un fichier
// (`file://`), où il n'y a rien à côté d'elle.
const SOCLE = new URLSearchParams(location.search).get("socle")
           || (location.protocol === "file:" ? "https://yesno584.github.io/AN-API" : ".");
const PAR_PAQUET = 25;

/* ------------------------------------------------------------------ */

let TEXTES = [];
let GROUPES = new Map();
let ETAT = {};
const filtres = { etapes: new Set(), etapesSenat: new Set(),
                  chambres: new Set(), types: new Set(), themes: new Set(),
                  activite: null, programme: false, vote: null, etat: null, mots: "" };

const nb = new Intl.NumberFormat("fr-FR");
const _dateCourte = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short", year: "numeric" });
const _dateLongue = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "long", year: "numeric" });
/* En français, le premier jour du mois s'écrit « 1er ». Le navigateur écrit
   « 1 janvier », qui se lit mal — et les dates d'entrée en vigueur tombent
   presque toujours un premier. */
// Le « 1 » n'est pas toujours en tête : « lundi 1 juin » le porte au milieu.
// On remplace donc le premier « 1 » isolé, quelle que soit sa place.
const premier = (rendu, d) => d.getDate() === 1 ? rendu.replace(/\b1\b/, "1er") : rendu;
const dateCourte = { format: (d) => premier(_dateCourte.format(d), d) };
const dateLongue = { format: (d) => premier(_dateLongue.format(d), d) };

/* Une archive facultative qui n'arrive pas ne vide plus la base : les données
   de la veille restent en place. Encore faut-il le dire — sans quoi la page se
   donnerait pour plus fraîche qu'elle n'est. `vuLe` est l'horodatage du dernier
   téléchargement réussi de l'archive, et `genereLe` celui de la publication du
   matin : quand les deux jours diffèrent, ce qu'on affiche date d'avant. */
function avisDeVeille(vuLe, quoi, poids) {
  if (!vuLe || !ETAT.genereLe) return null;
  const jour = (iso) => String(iso).slice(0, 10);
  if (jour(vuLe) === jour(ETAT.genereLe)) return null;
  return el("p", "avertissement",
    `${quoi} datent du ${dateLongue.format(enDate(jour(vuLe)))} : leur archive `
    + `de ${poids} n'est pas arrivée entière depuis. Rien n'a été effacé, et `
    + `le reste de la fiche est à jour. La récupération est retentée chaque `
    + `matin.`);
}

/* Le même avis pour le Sénat, dont les données ne viennent pas d'une archive
   mais de quatre sources. **La page ne doit jamais se donner pour plus fraîche
   qu'elle n'est** : quand la reconstruction échoue, celles de la veille
   restent affichées, et il faut le dire. */
function avisDuSenat() {
  if (!ETAT.senatVuLe || !ETAT.genereLe) return null;
  const jour = (iso) => String(iso).slice(0, 10);
  if (jour(ETAT.senatVuLe) === jour(ETAT.genereLe)) return null;
  return el("p", "avertissement",
    `Les données du Sénat datent du `
    + `${dateLongue.format(enDate(jour(ETAT.senatVuLe)))} : ses sources n'ont `
    + `pas pu être relues depuis. Rien n'a été effacé, et le reste du site est `
    + `à jour. La récupération est retentée chaque matin.`);
}

// Les six étapes du parcours, pour la frise. « Promulguée » n'en fait pas
// partie : c'est l'après, pas une septième étape.
const PARCOURS = ETAPES.filter((e) => e.n !== PROMULGUEE && e.n !== ARRETE)
                       .sort((a, b) => a.n - b.n);
const etapeDe = (n) => ETAPES.find((e) => e.n === n);
/* L'ordre du fil, de la frise et des filtres, qui doivent tous dire la même
   chose : les textes arrêtés d'abord, puis les six étapes, puis la
   promulgation. Le fil se lit de gauche à droite, et le premier trait de la
   frise mène à la première colonne — sans quoi la frise mentirait sur le fil. */
const FRISE_EN_ORDRE = [etapeDe(ARRETE), ...PARCOURS, etapeDe(PROMULGUEE)]
                       .filter(Boolean);
const statutDe = (t) => t.statut || (t.etape === PROMULGUEE ? "promulgue" : "en_cours");

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
let ONGLET = "textes";
let SENAT = [];
let THEMES = [];
let TRAVAUX = [];
let CATEGORIES_TRAVAUX = [];

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
    carte: (t) => carte(t),
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
    carte: (t) => carte(t),
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
    carte: (t) => carteTravail(t),
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

const $ = (id) => document.getElementById(id);
const enDate = (iso) => { const [a, m, j] = iso.split("-").map(Number); return new Date(a, m - 1, j); };
const jours = (iso) => Math.floor((Date.now() - enDate(iso)) / 86400000);

function el(balise, classe, texte) {
  const n = document.createElement(balise);
  if (classe) n.className = classe;
  if (texte != null) n.textContent = texte;
  return n;
}

function typeCourt(t) { return (TYPES[t] || [t])[0]; }

function expliquer(titre, texte, valeur) {
  document.querySelectorAll(".info .groupes").forEach((n) => n.remove());
  $("info-titre").textContent = titre;
  $("info-texte").textContent = texte;
  const v = $("info-valeur");
  // Ne pas répéter le titre juste au-dessus de lui-même.
  const utile = valeur && valeur !== titre;
  v.textContent = utile ? valeur : "";
  v.hidden = !utile;
  $("voile").hidden = false;
}
function fermer() { $("voile").hidden = true; }
$("info-fermer").addEventListener("click", fermer);
$("voile").addEventListener("click", (e) => { if (e.target === $("voile")) fermer(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") fermer(); });

/* ---------- filtrage ---------- */
const ACTIVITE = {
  semaine: ["Cette semaine", 7], mois: ["Ce mois-ci", 31],
  trimestre: ["3 derniers mois", 92], arret: ["À l'arrêt depuis 1 an", -365],
};
