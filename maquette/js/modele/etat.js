/* L'état de l'écran : ce que le lecteur a choisi — l'onglet, les filtres, la colonne regardée, le mois et le jour du calendrier, la façon de dessiner l'hémicycle, la lecture d'un article. Le contrôleur l'écrit, les vues le lisent. */

let ONGLET = "textes";

const filtres = { etapes: new Set(), etapesSenat: new Set(),
                  chambres: new Set(), types: new Set(), themes: new Set(),
                  activite: null, programme: false, vote: null, etat: null, mots: "" };

// Les catégories affichées, dans l'ordre, telles que la dernière construction
// les a posées. La frise s'en sert pour savoir où mène chaque trait.
let CATEGORIES = [];

// La catégorie qu'on regardait au dernier passage. Sert à savoir quand on
// vient d'en changer — et donc quand remonter en haut.
let CATEGORIE_VUE = null;

let MOIS_VU = null;             // « 2026-07 »

let JOUR_VU = null;             // « 2026-07-21 »

// Le mode choisi vaut pour l'écran, pas pour la visite suivante : il survit à
// l'ouverture d'un groupe, pas à un rechargement de la page.
let PAR_SIEGE = false;

// Comment le texte est montré : les différences, le texte en vigueur seul, ou
// celui d'avant seul. Le choix se garde d'un article à l'autre.
let MODE_TEXTE = "diff";
