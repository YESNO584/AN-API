/* L'hémicycle : les sièges en arcs, par groupe ou par numéro de siège, la liste des groupes et des députés. */

/* ------------------------------------------------------------------ *
 * L'hémicycle : la composition de l'Assemblée
 *
 * Les 577 sièges, coloriés par groupe, de la gauche à la droite. Ce qui est
 * mesuré : l'effectif de chaque groupe (un compte de députés) et l'ordre des
 * groupes (le numéro de siège médian de leurs députés, publié par
 * l'Assemblée). Ce qui est une convention : la place d'un siège dans le
 * dessin — l'open data ne dit pas où chaque député s'assied — et les
 * couleurs. L'écran le dit lui-même, au toucher.
 * ------------------------------------------------------------------ */

const RANGEES = 12;            // rangées d'arcs, du fond de la salle au perchoir

const CREUX = 0.45;            // rayon de la rangée la plus courte, en part du grand

function siegesEnArcs(total, rangees = RANGEES) {
  // Une rangée longue porte plus de sièges qu'une rangée courte : on répartit
  // au prorata du rayon. L'arrondi ne tombe jamais juste — on rattrape le
  // reste sur les rangées extérieures, les plus longues.
  const rayons = [];
  for (let i = 0; i < rangees; i++) {
    rayons.push(CREUX + (1 - CREUX) * i / (rangees - 1));
  }
  const somme = rayons.reduce((a, b) => a + b, 0);
  const parRangee = rayons.map((r) => Math.max(1, Math.round(total * r / somme)));
  let ecart = total - parRangee.reduce((a, b) => a + b, 0);
  for (let i = rangees - 1; ecart !== 0; i = (i + rangees - 1) % rangees) {
    const pas = ecart > 0 ? 1 : -1;
    parRangee[i] += pas;
    ecart -= pas;
  }

  const sieges = [];
  parRangee.forEach((combien, i) => {
    for (let k = 0; k < combien; k++) {
      // π à gauche, 0 à droite, avec un demi-pas de marge aux deux bouts.
      sieges.push({ angle: Math.PI * (1 - (k + 0.5) / combien), rayon: rayons[i] });
    }
  });
  // De la gauche vers la droite ; à angle égal, du fond vers le perchoir.
  sieges.sort((a, b) => b.angle - a.angle || a.rayon - b.rayon);
  return sieges;
}

const SVG = "http://www.w3.org/2000/svg";

function dessinerHemicycle(groupes, total) {
  const sieges = siegesEnArcs(total);
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("viewBox", "0 0 100 56");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label",
    `${total} sièges coloriés par groupe, de la gauche à la droite de l'hémicycle`);
  let pris = 0;
  for (const g of groupes) {
    const part = document.createElementNS(SVG, "g");
    part.dataset.sigle = g.sigle;
    part.setAttribute("fill", g.couleur || "#8d8d8d");
    for (let k = 0; k < g.effectif && pris < sieges.length; k++, pris++) {
      const s = sieges[pris];
      const point = document.createElementNS(SVG, "circle");
      point.setAttribute("cx", (50 + 46 * s.rayon * Math.cos(s.angle)).toFixed(2));
      point.setAttribute("cy", (53 - 46 * s.rayon * Math.sin(s.angle)).toFixed(2));
      point.setAttribute("r", "1.05");
      part.append(point);
    }
    svg.append(part);
  }
  return svg;
}

/* ---------- les députés d'un groupe ---------- */
/* La circonscription telle que la source la donne : un département en clair et
   un numéro. Le numéro s'écrit comme on l'écrit en français — « 1re », puis
   « 2e ». C'est la seule retouche, et elle ne porte que sur la forme. */
function circonscription(d) {
  if (!d.departement && !d.circo) return "";
  if (!d.circo) return d.departement;
  const rang = d.circo === "1" ? "1re" : d.circo + "e";
  return `${d.departement}, ${rang} circonscription`;
}

function ligneDepute(x) {
  const ligne = el("div", "depute");
  // Les photos ne sont pas dans l'open data : ce sont des fichiers du site de
  // l'Assemblée, chargés depuis lui. `loading = "lazy"` compte ici — sans
  // cela, ouvrir le RN demanderait 122 images d'un coup.
  if (x.photo) {
    const img = el("img");
    img.src = x.photo;
    img.alt = "";
    img.loading = "lazy";
    // Toutes ne sont pas en ligne : on remplace sans casser la mise en page
    // plutôt que d'afficher une image brisée.
    img.addEventListener("error", () => img.replaceWith(el("div", "sans-photo", "—")));
    ligne.append(img);
  } else {
    ligne.append(el("div", "sans-photo", "—"));
  }
  const corps = el("div", "corps");
  corps.append(el("b", null, [x.civilite, x.prenom, x.nom].filter(Boolean).join(" ")));
  // Le siège vient après la circonscription. Un député sur 577 n'en a pas :
  // la ligne n'en affiche alors aucun.
  const ou = [circonscription(x), x.siege ? "siège " + x.siege : ""]
             .filter(Boolean).join(" · ");
  if (ou) corps.append(el("span", "ou", ou));
  ligne.append(corps);
  return ligne;
}

/* Le second dessin : chaque député à **son** numéro de siège.
 *
 * Ce que la source donne, c'est un numéro par député, et l'ordre de ces
 * numéros — ils vont de la droite (1) vers la gauche (650). Ce qu'elle ne donne
 * pas, c'est l'endroit où chaque siège se trouve dans la salle : les numéros
 * sont donc posés dans la même géométrie d'arcs que l'autre dessin, dans leur
 * ordre. Plus fidèle, pas exact.
 *
 * Ce dessin montre ce que le dessin par groupe cache : deux groupes peuvent
 * être imbriqués. Mesuré le 2026-09-19 — LIOT occupe les sièges 382 à 483 et
 * SOC 409 à 569 : il n'y a pas de frontière entre eux. Et les onze non-inscrits
 * vont du siège 111 au siège 422, d'un bout à l'autre de la salle.
 */
const SIEGES_DE_LA_SALLE = 650;

function placesParSiege(groupes) {
  const par = new Map();
  for (const g of groupes) {
    for (const x of MEMBRES.get(g.ref) || []) {
      if (x.siege) par.set(Number(x.siege), g);
    }
  }
  return par;
}

function dessinerParSiege(groupes) {
  const par = placesParSiege(groupes);
  const hautNumero = Math.max(SIEGES_DE_LA_SALLE, ...par.keys());
  const places = siegesEnArcs(hautNumero);
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("viewBox", "0 0 100 56");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label",
    `${par.size} députés placés à leur numéro de siège, de la gauche à la droite`);
  // Un groupe de dessin par groupe politique : c'est lui qui porte la couleur,
  // le sigle, et donc l'effacement et le toucher.
  const paquets = new Map();
  for (const g of groupes) {
    const part = document.createElementNS(SVG, "g");
    part.dataset.sigle = g.sigle;
    part.setAttribute("fill", g.couleur || "#8d8d8d");
    paquets.set(g.sigle, part);
    svg.append(part);
  }
  const vides = document.createElementNS(SVG, "g");
  vides.setAttribute("class", "vides");
  svg.append(vides);

  places.forEach((s, i) => {
    // La place la plus à gauche porte le plus grand numéro : la salle est
    // numérotée de la droite vers la gauche.
    const numero = hautNumero - i;
    const g = par.get(numero);
    const point = document.createElementNS(SVG, "circle");
    point.setAttribute("cx", (50 + 46 * s.rayon * Math.cos(s.angle)).toFixed(2));
    point.setAttribute("cy", (53 - 46 * s.rayon * Math.sin(s.angle)).toFixed(2));
    point.setAttribute("r", "1.05");
    (g ? paquets.get(g.sigle) : vides).append(point);
  });
  return { svg, places: par.size, vides: places.length - par.size };
}

/* Poser le dessin, dans le mode choisi, et le relier au reste : les sièges d'un
   groupe s'ouvrent au toucher, et le groupe ouvert garde sa couleur pendant que
   les autres s'effacent. Appelé à l'ouverture de l'écran et à chaque bascule,
   pour ne pas refaire toute la page — et ne pas renvoyer la vue en haut. */
function poserLeDessin(zone, groupes, total, choisi, sigle, parSiege) {
  zone.querySelectorAll("svg, .sous-dessin").forEach((n) => n.remove());
  const fait = parSiege ? dessinerParSiege(groupes)
                        : { svg: dessinerHemicycle(groupes, total) };
  const svg = fait.svg;
  zone.append(svg);
  if (parSiege) {
    // Ce mode perd un député : celui dont la source ne donne pas le siège.
    const manquants = total - fait.places;
    zone.append(el("p", "sous-dessin",
      `${nb.format(fait.places)} députés à leur numéro de siège, `
      + `${nb.format(fait.vides)} sièges vides`
      + (manquants > 0
         ? ` — ${nb.format(manquants)} député${manquants > 1 ? "s" : ""} `
           + "sans numéro, donc absent du dessin." : ".")));
  }
  svg.classList.toggle("un-seul", !!choisi);
  svg.querySelectorAll("g").forEach(
    (n) => n.classList.toggle("vu", !!choisi && n.dataset.sigle === choisi.sigle));
  svg.addEventListener("click", (ev) => {
    const part = ev.target.closest("g");
    const vise = part && part.dataset.sigle;
    if (vise) location.hash = vise === sigle
      ? "#/hemicycle" : "#/hemicycle/" + encodeURIComponent(vise);
  });
}

/* La ligne d'un groupe dans la liste sous l'hémicycle — la même pour les
   deux chambres. `hf`, s'il est donné, est l'emplacement du compte femmes /
   hommes, rempli plus tard. Toucher la ligne ouvre le groupe, ou le referme
   s'il l'était : c'est l'adresse qui porte l'état. */
function ligneDeGroupe(g, choisi, sigle, nom, unite, racine, hf = null) {
  const ligne = el("button", "hemi-groupe");
  ligne.setAttribute("aria-expanded", String(g === choisi));
  const teinte = el("i");
  if (g.couleur) teinte.style.background = g.couleur;
  ligne.append(teinte);
  ligne.append(el("span", "sigle", sigle));
  ligne.append(el("span", "nom", nom));
  const compte = el("span", "n", nb.format(g.effectif));
  compte.append(el("span", null, unite));
  ligne.append(compte);
  if (hf) ligne.append(hf);
  ligne.append(el("span", "chevron", g === choisi ? "‹" : "›"));
  ligne.addEventListener("click", () => {
    location.hash = g === choisi ? racine : racine + "/" + encodeURIComponent(g.sigle);
  });
  return ligne;
}

/* La phrase sous le titre, et l'emplacement du total femmes / hommes qui se
   complète quand les douze fichiers sont lus, comme les comptes par groupe :
   la phrase ne fait pas attendre l'écran. */
function sousTitreDeLAssemblee(total, groupes) {
  const sous = el("p", "fiche-sous",
    `${nb.format(total)} députés, ${groupes.length} groupes, `
    + "de la gauche à la droite de l'hémicycle. ");
  // Le total femmes / hommes se complète quand les douze fichiers sont lus,
  // comme les comptes par groupe : la phrase ne fait pas attendre l'écran.
  const totalHF = el("span", "hf-total");
  sous.append(totalHF);
  const aide = el("button", "aide", "ⓘ");
  aide.setAttribute("aria-label", "Ce que ce dessin montre, et ce qu'il ne montre pas");
  aide.addEventListener("click",
    () => expliquer(...EXPLICATIONS.hemicycle, "Effectifs mesurés, places dessinées"));
  sous.append(aide);
  return [sous, totalHF];
}

/* La bascule entre les deux dessins, dans le coin haut droit. « Par siège »
   attend que les douze fichiers de groupes soient lus : un hémicycle à
   moitié vide serait pire qu'un dessin par blocs. Rend ses deux boutons ;
   `surChoix(siege, boutons)` est le geste du contrôleur. */
function basculeDuDessin(zone, surChoix) {
  const bascule = el("div", "bascule-hemi");
  bascule.setAttribute("role", "group");
  bascule.setAttribute("aria-label", "Façon de dessiner l'hémicycle");
  const boutons = [["groupe", false], ["siège", true]].map(([mot, siege]) => {
    const b = el("button", null, mot);
    b.setAttribute("aria-pressed", String(PAR_SIEGE === siege));
    b.disabled = siege;               // levé dès que les députés sont lus
    b.addEventListener("click", () => surChoix(siege, boutons));
    bascule.append(b);
    return b;
  });
  zone.append(bascule);
  return boutons;
}
