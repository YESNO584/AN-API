/* Les briques que toutes les vues emploient : créer un élément, formater un nombre ou une date, une étiquette, une puce, un bloc, une personne, la mention d'origine, le voile d'explication, l'ouverture et la fermeture d'un écran à part. */

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

const moisLong = new Intl.DateTimeFormat("fr-FR", { month: "long", year: "numeric" });

const _jourLong = new Intl.DateTimeFormat("fr-FR",
  { weekday: "long", day: "numeric", month: "long" });

// « lundi 1er juin », comme partout ailleurs.
const jourLong = { format: (d) => premier(_jourLong.format(d), d) };

const $ = (id) => document.getElementById(id);

function el(balise, classe, texte) {
  const n = document.createElement(balise);
  if (classe) n.className = classe;
  if (texte != null) n.textContent = texte;
  return n;
}

function etiquette(classe, libelle, explication, valeur) {
  const b = el("button", "etiq " + (classe || ""), libelle);
  b.addEventListener("click", (ev) => {
    // Dans le parcours, ces étiquettes vivent à l'intérieur d'un dépliant :
    // sans ça, demander une explication ouvrirait ou fermerait l'étape. Et
    // dans le calendrier, à l'intérieur d'une ligne qui mène à une fiche :
    // sans le second, l'explication s'ouvrait pendant que la page partait.
    ev.preventDefault();
    ev.stopPropagation();
    expliquer(explication[0], explication[1], valeur ?? libelle);
  });
  return b;
}

/* ---------- panneau des filtres ---------- */
function puce(libelle, actif, compte, surClic, explication) {
  const enveloppe = el("span", "puce-groupe");
  const b = el("button", "puce");
  b.setAttribute("aria-pressed", actif ? "true" : "false");
  b.append(document.createTextNode(libelle));
  if (compte != null) b.append(el("span", "c", nb.format(compte)));
  if (compte === 0) { b.disabled = true; b.setAttribute("aria-pressed", "false"); }
  b.addEventListener("click", surClic);
  enveloppe.append(b);

  // Un bouton séparé pour l'explication : sur un téléphone il n'y a ni
  // survol ni clic droit, et le toucher est déjà pris par le filtre.
  if (explication) {
    const aide = el("button", "aide", "ⓘ");
    aide.setAttribute("aria-label", "Que veut dire « " + libelle + " » ?");
    aide.addEventListener("click", (e) => {
      e.stopPropagation();
      expliquer(explication[0], explication[1], explication[2] || libelle);
    });
    enveloppe.append(aide);
  }
  return enveloppe;
}

function groupe(titre, contenu) {
  const g = el("div", "groupe");
  g.append(el("div", "titre", titre));
  const p = el("div", "puces");
  contenu.forEach((c) => p.append(c));
  g.append(p);
  return g;
}

// Une rubrique de la fiche. Par défaut un dépliant ; `plat` la rend toujours
// ouverte, pour une rubrique posée dans un onglet — l'onglet a déjà fait le
// choix de ce qu'on regarde, et il n'y aurait rien à déplier de plus.
function bloc(titre, ouvert, plat) {
  if (plat) {
    const b = el("div", "bloc");
    b.append(el("h3", null, titre));
    return b;
  }
  const b = el("details", "bloc");
  if (ouvert) b.open = true;
  b.append(el("summary", null, titre));
  return b;
}

function personne(p, role) {
  const bloc = el("div", "auteur");
  if (p.photo) {
    const img = el("img");
    img.src = p.photo;
    img.alt = "";
    img.loading = "lazy";
    // Toutes les photos ne sont pas en ligne : on remplace sans casser la mise
    // en page plutôt que d'afficher une image brisée.
    img.addEventListener("error", () => img.replaceWith(el("div", "sans-photo", "—")));
    bloc.append(img);
  } else {
    bloc.append(el("div", "sans-photo", "—"));
  }
  const qui = el("div", "qui");
  qui.append(el("div", "nom", [p.civilite, p.prenom, p.nom].filter(Boolean).join(" ")));
  if (role) qui.append(el("div", "role", role));
  if (p.sigle) {
    const g = el("div", "grp");
    const teinte = el("i");
    if (p.couleur) teinte.style.background = p.couleur;
    g.append(teinte);
    g.append(document.createTextNode(p.nom_groupe || p.sigle));
    qui.append(g);
  }
  bloc.append(qui);
  return bloc;
}

/* ---------- le parcours ---------- */

/* La même étiquette que dans le fil : même forme, mêmes couleurs. Une pastille
   propre au parcours donnerait deux vocabulaires visuels pour une seule idée. */
function pastilleChambre(chambre) {
  return etiquette("chambre-" + (chambre || "aucune"),
                   CHAMBRES[chambre][0], CHAMBRES[chambre]);
}

function iconeOrigine(origine) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 16 16");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  const forme = document.createElementNS("http://www.w3.org/2000/svg", "path");
  forme.setAttribute("d", origine === "humain"
    ? "M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm0 1.5c-3 0-5.5 1.6-5.5 3.6V15h11v-1.9c0-2-2.5-3.6-5.5-3.6Z"
    : "M8 0.8 9.5 5 13.7 6.5 9.5 8 8 12.2 6.5 8 2.3 6.5 6.5 5 8 0.8Z"
      + "M13 10.5 13.7 12.3 15.5 13 13.7 13.7 13 15.5 12.3 13.7 10.5 13 12.3 12.3 13 10.5Z");
  svg.append(forme);
  return svg;
}

/* La mention « Générée par une IA » — ou « écrite par une personne » — et son
   explication au toucher. Sur un ordinateur, la mention complète apparaît au
   survol ; sur un téléphone, où il n'y a pas de survol, le toucher ouvre la
   même explication. Elle dit quand la rubrique a été écrite, et par quel
   modèle si le socle le dit : le modèle n'est pas toujours renseigné — une
   rubrique rédigée par une personne n'en a pas — et la ligne se tait alors
   plutôt que d'annoncer un vide. */
function boutonOrigine(code, origine, le, modele, verbe) {
  const mention = el("button", "origine");
  mention.append(iconeOrigine(code));
  mention.append(el("u", null, origine.court));
  mention.title = origine.mot + " — touchez pour en savoir plus.";
  mention.setAttribute("aria-label", origine.mot);
  mention.addEventListener("click", (ev) => {
    ev.preventDefault();
    const quand = le ? verbe + " le " + dateLongue.format(enDate(le)) : null;
    const par = modele ? "modèle " + modele : null;
    expliquer(origine.titre, origine.quoi,
              [quand, par].filter(Boolean).join(" · ") || null);
  });
  return mention;
}

/* Au-delà de trois mesures, la description prenait tout l'écran et la fiche
   commençait sous le pli. Les autres se demandent. */
function boutonDeplier(liste, reste) {
  liste.classList.add("replie");
  const bouton = el("button", "deplier",
    `Voir ${reste} autre${reste > 1 ? "s" : ""} mesure${reste > 1 ? "s" : ""}`);
  bouton.addEventListener("click", () => {
    const replie = liste.classList.toggle("replie");
    bouton.textContent = replie
      ? `Voir ${reste} autre${reste > 1 ? "s" : ""} mesure${reste > 1 ? "s" : ""}`
      : "Replier";
  });
  return bouton;
}

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

/* ------------------------------------------------------------------ *
 * Ce qu'une loi change au droit
 *
 * Deux écrans. La liste des articles, groupés par code, qui ne porte aucun
 * texte et sert à choisir ; puis la fiche d'un article, avec son texte entier
 * et la comparaison. On n'y accède que depuis la fiche du texte : ce n'est
 * pas une rubrique du fil, c'est le détail d'une loi.
 * ------------------------------------------------------------------ */

function ouvrirEcran() {
  const f = $("fiche");
  f.textContent = "";
  f.hidden = false;
  document.body.classList.add("fiche-ouverte");
  mesurerLePied();
  $("fil").hidden = true;
  $("filtres").hidden = true;
  $("frise-bas").hidden = true;
  $("bascule").setAttribute("aria-expanded", "false");
  $("compte").hidden = true;
  document.querySelector(".barre").hidden = true;
  window.scrollTo(0, 0);
  return f;
}

function boutonRetour(vers, libelle) {
  const b = el("button", "retour", "‹ " + libelle);
  b.addEventListener("click", () => { location.hash = vers; });
  return b;
}

function fermerFiche() {
  document.body.classList.remove("fiche-ouverte");
  $("frise-bas").hidden = false;
  $("fiche").hidden = true;
  $("fiche").textContent = "";
  $("fil").hidden = false;
  $("compte").hidden = false;
  // La recherche et les filtres valent dans les trois onglets : la barre
  // revient quel que soit celui d'où l'on vient.
  document.querySelector(".barre").hidden = false;
}

/* ---------- démarrage ---------- */
// L'en-tête se colle sous le bandeau : il lui faut sa hauteur, mesurée, car
// le texte du bandeau passe à deux lignes sur un écran étroit.
function mesurerLeBandeau() {
  const b = document.querySelector(".bandeau");
  if (b) document.documentElement.style
          .setProperty("--haut-bandeau", b.offsetHeight + "px");
}

// Le bas de page collé sur une fiche recouvre autant de hauteur qu'il en fait.
// On la mesure — deux phrases tiennent sur deux lignes ou sur quatre selon la
// largeur — pour réserver dessous exactement ce qu'il faut.
function mesurerLePied() {
  const p = document.querySelector("footer");
  if (p) document.documentElement.style
          .setProperty("--haut-pied", p.offsetHeight + "px");
}

/* Ce que les deux boutons promettent change avec l'onglet : une étiquette qui
   dirait « Assemblée » dans l'onglet du Sénat tromperait un lecteur qui
   n'entend que ça. */
function nommerLesBoutons() {
  const senat = ONGLET === "senat";
  $("bouton-agenda").setAttribute("aria-label", senat
    ? "Les séances à venir au Sénat" : "Calendrier des séances et des votes");
  $("bouton-hemicycle").setAttribute("aria-label", senat
    ? "La composition du Sénat" : "La composition de l'Assemblée");
}
