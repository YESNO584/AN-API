/* Le calendrier : un mois, une grille de jours, la liste du jour choisi — pour l'une ou l'autre chambre. */

function moisVoisin(mois, pas) {
  const [a, m] = mois.split("-").map(Number);
  const d = new Date(a, m - 1 + pas, 1);
  return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0");
}

async function moisCharge(mois) {
  if (MOIS_EN_CACHE.has(mois)) return MOIS_EN_CACHE.get(mois);
  const d = await lire(`calendrier/${mois}.json`);
  const evenements = d?.evenements || [];
  MOIS_EN_CACHE.set(mois, evenements);
  return evenements;
}

async function ouvrirAgenda() {
  const f = ouvrirEcran();
  const retour = boutonRetour("", "Retour au fil");
  f.append(retour);
  f.append(el("h2", "fiche-titre", "Calendrier"));

  if (!AGENDA) AGENDA = await lire("calendrier.json");
  if (!AGENDA || !(AGENDA.mois || []).length) {
    f.append(el("div", "vide", "Calendrier indisponible."));
    return;
  }
  f.append(el("p", "fiche-sous",
    `${nb.format(AGENDA.total)} séances, votes et décisions, de `
    + moisLong.format(enDate(AGENDA.mois[0].mois + "-01")) + " à "
    + moisLong.format(enDate(AGENDA.mois[AGENDA.mois.length - 1].mois + "-01")) + "."));

  // On ouvre sur le mois en cours s'il porte quelque chose, sinon sur le
  // dernier mois qui en porte : un calendrier vide au premier regard ne dit
  // pas où aller.
  if (!MOIS_VU) {
    const connus = AGENDA.mois.map((m) => m.mois);
    MOIS_VU = connus.includes(moisDe(aujourdhui()))
      ? moisDe(aujourdhui()) : connus[connus.length - 1];
  }
  const zone = el("div");
  f.append(zone);
  await dessinerMois(zone, CALENDRIER_AN);
}

async function dessinerMois(zone, source) {
  const evenements = await source.charger(MOIS_VU);
  const connus = source.mois();
  zone.textContent = "";

  const barre = el("div", "mois-barre");
  const fleche = (signe, pas, actif) => {
    const b = el("button", null, signe);
    b.setAttribute("aria-label", pas < 0 ? "Mois précédent" : "Mois suivant");
    b.disabled = !actif;
    b.addEventListener("click", async () => {
      MOIS_VU = moisVoisin(MOIS_VU, pas);
      JOUR_VU = null;
      await dessinerMois(zone, source);
    });
    return b;
  };
  barre.append(fleche("‹", -1, MOIS_VU > connus[0]),
               el("b", null, moisLong.format(enDate(MOIS_VU + "-01"))),
               fleche("›", 1, MOIS_VU < connus[connus.length - 1]));
  zone.append(barre);

  const parJour = new Map();
  for (const e of evenements) {
    if (!parJour.has(e.date)) parJour.set(e.date, []);
    parJour.get(e.date).push(e);
  }

  // Le jour choisi se décide **avant** de dessiner la grille : sinon la case
  // du jour ne serait pas marquée, la grille ayant été construite avant de
  // savoir lequel montrer.
  //
  // **Et il doit porter quelque chose dans *ce* calendrier.** Les deux
  // chambres partagent `JOUR_VU` : passer du calendrier du Sénat à celui de
  // l'Assemblée gardait un jour chargé au Sénat et vide à l'Assemblée, qui
  // rendait une liste vide sous une grille pleine.
  if (evenements.length
      && (!JOUR_VU || moisDe(JOUR_VU) !== MOIS_VU || !parJour.has(JOUR_VU))) {
    // Aujourd'hui s'il porte quelque chose, sinon le premier jour du mois qui
    // en porte.
    JOUR_VU = parJour.has(aujourdhui()) ? aujourdhui() : [...parJour.keys()].sort()[0];
  }
  zone.append(grilleDuMois(parJour, zone, source));

  if (!evenements.length) {
    zone.append(el("div", "vide", source.vide));
    return;
  }
  zone.append(listeDuJour(parJour.get(JOUR_VU) || [], source));
}

/* **Une seule mécanique de calendrier, deux chambres.** La barre des mois, la
   grille, le jour choisi et sa liste sont les mêmes ; une source dit seulement
   quels mois existent, comment charger l'un d'eux, et comment dessiner la
   ligne d'un événement. Deux calendriers séparés divergeraient. */
const CALENDRIER_AN = {
  mois: () => (AGENDA.mois || []).map((m) => m.mois),
  charger: (mois) => moisCharge(mois),
  ligne: (e) => ligneEvenement(e),
  vide: "Aucune séance ni aucun vote ce mois-ci. Le Parlement ne siège pas "
      + "toute l'année : les mois d'été et de fin d'année sont creux.",
};

function grilleDuMois(parJour, zone, source) {
  const grille = el("div", "grille");
  for (const j of JOURS) grille.append(el("div", "jour-nom", j));

  const [an, mois] = MOIS_VU.split("-").map(Number);
  const premier = new Date(an, mois - 1, 1);
  // `getDay()` met dimanche à 0 ; la semaine française commence le lundi.
  const decalage = (premier.getDay() + 6) % 7;
  for (let i = 0; i < decalage; i++) grille.append(el("button", "vide"));

  const derniers = new Date(an, mois, 0).getDate();
  for (let n = 1; n <= derniers; n++) {
    const iso = `${MOIS_VU}-${String(n).padStart(2, "0")}`;
    const dessus = parJour.get(iso) || [];
    const b = el("button", [dessus.length ? "" : "rien",
                            iso === aujourdhui() ? "aujourdhui" : "",
                            iso === JOUR_VU ? "choisi" : ""].filter(Boolean).join(" "));
    b.append(el("span", null, String(n)));
    const points = el("div", "points");
    for (let i = 0; i < Math.min(dessus.length, 3); i++) points.append(el("i"));
    b.append(points);
    if (dessus.length) {
      b.setAttribute("aria-label",
        `${n} : ${dessus.length} événement${dessus.length > 1 ? "s" : ""}`);
      b.addEventListener("click", async () => { JOUR_VU = iso; await dessinerMois(zone, source); });
    } else {
      b.disabled = true;
    }
    grille.append(b);
  }
  return grille;
}

function listeDuJour(evenements, source) {
  const zone = el("div");
  zone.append(el("h3", "jour-titre", jourLong.format(enDate(JOUR_VU))));
  for (const e of evenements) zone.append(source.ligne(e));
  return zone;
}

function ligneEvenement(e) {
  const b = el("button", "evt");
  b.append(el("div", "quand", e.heure || "—"));
  const corps = el("div", "corps");
  // Le titre du texte vient de la liste déjà chargée : le calendrier ne le
  // répète pas dans ses fichiers.
  const texte = TEXTES.find((t) => t.uid === e.texte);
  corps.append(el("h4", null, texte ? texte.titre : e.quoi || "Texte"));

  const l = el("div", "lignes");
  const [nom, quoi] = GENRES[e.genre] || [e.genre, ""];
  const genre = el("span", "genre " + e.genre, nom);
  l.append(genre);
  if (e.chambre) l.append(etiquette("chambre-" + e.chambre, CHAMBRES[e.chambre][0],
                                    CHAMBRES[e.chambre]));
  if (e.lecture) l.append(etiquette("", e.lecture, EXPLICATIONS.lecture));
  if (e.conclusion) l.append(etiquette("", e.conclusion, EXPLICATIONS.conclusion));
  corps.append(l);

  if (texte && e.quoi && e.quoi !== texte.titre) {
    corps.append(el("div", "resultat", e.quoi));
  }
  if (e.vote) {
    const r = el("div", "resultat");
    r.append(el("b", null, e.vote.sort || "Scrutin"));
    r.append(document.createTextNode(
      ` — ${nb.format(e.vote.pour)} pour, ${nb.format(e.vote.contre)} contre, `
      + `${nb.format(e.vote.abstentions)} abstention${e.vote.abstentions > 1 ? "s" : ""}`));
    corps.append(r);
  }
  b.append(corps);

  if (texte) {
    b.addEventListener("click", () => { location.hash = "#/texte/" + e.texte; });
  } else {
    // Sans le texte dans la liste chargée, la fiche s'ouvrirait sur du vide.
    b.disabled = true;
    b.style.cursor = "default";
  }
  return b;
}

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
