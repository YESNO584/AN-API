/* Les données publiées par le socle : d'où elles viennent, les listes chargées au démarrage, et ce qui se charge à la demande — versions, députés d'un groupe, mois du calendrier. Aucun dessin ici. */

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

let TEXTES = [];

let GROUPES = new Map();

let ETAT = {};

let SENAT = [];

let THEMES = [];

let TRAVAUX = [];

let CATEGORIES_TRAVAUX = [];

function lire(nom, obligatoire = false) {
  return fetch(`${SOCLE}/${nom}`).then((r) => {
    if (!r.ok) throw new Error(nom + " : réponse " + r.status);
    return r.json();
  }).catch((e) => { if (obligatoire) throw e; return null; });
}

/* Les sept fichiers du démarrage, lus d'un coup, et les listes qu'ils
   remplissent. Rend le fichier des textes, pour sa date. Lève si le fichier
   principal manque ; les autres sont facultatifs. */
async function chargerLesDonnees() {
  const [textes, promulguees, arretes, etat, groupes, travaux, etapes] =
    await Promise.all([
      lire("textes.json", true),
      lire("promulgues.json"),
      lire("arretes.json"),
      lire("etat.json"),
      lire("groupes.json"),
      lire("travaux.json"),
      // Les sujets du Sénat vivent ici, avec les comptes par étape.
      lire("etapes.json"),
    ]);
  // Trois fichiers, trois issues. Les lois promulguées ouvrent le fil — une
  // application qui s'appelle « Qui vote quoi » doit montrer celles
  // qui sont allées au bout. Les textes arrêtés le ferment.
  TEXTES = textes.textes.concat(
    (promulguees?.textes || []).map((t) => ({ ...t, etape: PROMULGUEE })),
    (arretes?.textes || []).map((t) => ({ ...t, etape: ARRETE })));
  // Le plus avancé d'abord — les lois promulguées ouvrent le fil, les textes
  // déposés et jamais examinés le ferment.
  TEXTES.sort((a, b) => b.etape - a.etape ||
              b.date_dernier_mouvement.localeCompare(a.date_dernier_mouvement));
  GROUPES = new Map((groupes?.groupes || []).map((g) => [g.sigle, g]));
  // Les travaux de l'Assemblée : le second onglet. S'ils manquent, l'onglet
  // reste, vide et honnête, plutôt que de disparaître sans explication.
  // L'onglet « Sénat » : les mêmes textes, mais seulement ceux qui y sont
  // passés, et rangés selon les étapes du Sénat. Deux textes sur trois n'y
  // sont jamais allés — ce n'est pas un trou, et l'onglet le dit.
  SENAT = TEXTES.filter((t) => t.senat);
  // Les sujets que le Sénat publie. L'application n'en avait aucun avant
  // lui : on filtrait par étape, par chambre, par type, jamais par « santé ».
  THEMES = (etapes?.themes) || [];
  TRAVAUX = travaux?.travaux || [];
  CATEGORIES_TRAVAUX = travaux?.categories || [];
  ETAT = etat || {};
  return textes;
}

/* Le texte d'une ligne du calendrier, cherché dans les listes déjà chargées :
   un texte de loi dans `TEXTES`, une résolution dans `TRAVAUX`. Le calendrier
   ne répète pas les titres dans ses fichiers. */
function texteDuCalendrier(uid) {
  if (!uid) return null;
  return TEXTES.find((t) => t.uid === uid) || TRAVAUX.find((t) => t.uid === uid) || null;
}

// Le texte demandé, gardé une fois lu : passer d'un bouton à l'autre ne doit
// pas retélécharger 2,8 Mo. La clé est le nom du fichier, pas le mode — deux
// des trois vues se dessinent à partir du même.
const VERSIONS_LUES = new Map();

async function versionLue(uid, nom) {
  const cle = uid + "/" + nom;
  if (!VERSIONS_LUES.has(cle)) {
    VERSIONS_LUES.set(cle, await lire(`versions/${uid}/${nom}.json`));
  }
  return VERSIONS_LUES.get(cle);
}

// Les députés d'un groupe, une fois lus, ne se relisent pas : douze fichiers,
// 113 Ko, et l'écran s'en sert pour deux choses — compter les femmes et les
// hommes de chaque groupe, et déplier la liste de celui qu'on ouvre.
const MEMBRES = new Map();

async function membresDuGroupe(g) {
  if (MEMBRES.has(g.ref)) return MEMBRES.get(g.ref);
  const d = await lire(`groupes/${g.ref}.json`);
  const liste = d?.deputes || null;
  MEMBRES.set(g.ref, liste);
  return liste;
}

let AGENDA = null;              // l'index des mois, chargé une fois

const MOIS_EN_CACHE = new Map();

async function moisCharge(mois) {
  if (MOIS_EN_CACHE.has(mois)) return MOIS_EN_CACHE.get(mois);
  const d = await lire(`calendrier/${mois}.json`);
  const evenements = d?.evenements || [];
  MOIS_EN_CACHE.set(mois, evenements);
  return evenements;
}
