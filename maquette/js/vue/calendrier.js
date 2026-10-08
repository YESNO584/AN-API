/* Le calendrier : la barre des mois, la grille des jours, la liste du jour choisi — pour l'une ou l'autre chambre. */

/* La barre des mois : le mois affiché, et une flèche de chaque côté tant
   qu'il y a un mois à voir dans ce sens. */
function barreDesMois(zone, source, connus) {
  const barre = el("div", "mois-barre");
  const fleche = (signe, pas, actif) => {
    const b = el("button", null, signe);
    b.setAttribute("aria-label", pas < 0 ? "Mois précédent" : "Mois suivant");
    b.disabled = !actif;
    b.addEventListener("click", () => allerAuMoisVoisin(zone, source, pas));
    return b;
  };
  barre.append(fleche("‹", -1, MOIS_VU > connus[0]),
               el("b", null, moisLong.format(enDate(MOIS_VU + "-01"))),
               fleche("›", 1, MOIS_VU < connus[connus.length - 1]));
  return barre;
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
