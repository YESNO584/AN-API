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

/* Qui a déposé le texte : le Gouvernement, ou le nom de l'auteur et
   l'étiquette de son groupe — la même que sur la carte du fil. Un sénateur ou
   un député sans groupe a son nom seul : rien n'est rapproché par le nom. */
function auteurDeLEvenement(a) {
  const ligne = el("div", "depose-par");
  if (a.gouvernement) {
    ligne.append(document.createTextNode("Déposé par le Gouvernement"));
    return ligne;
  }
  ligne.append(document.createTextNode("Déposé par " + a.nom));
  if (a.sigle) {
    ligne.append(etiquetteGroupe({ auteur_sigle: a.sigle, auteur_groupe: a.groupe,
                                   auteur_couleur: a.couleur }));
  }
  return ligne;
}

/* Une résolution porte sa catégorie, telle que l'onglet « Travaux » la nomme. */
function etiquetteDeTravail(t) {
  const c = CATEGORIES_TRAVAUX.find((x) => x.nom === t.type);
  return etiquette("", t.type, c ? [c.nom, c.quoi] : [t.type, ""]);
}

function lignesDeLEvenement(e, texte) {
  const l = el("div", "lignes");
  const [nom] = GENRES[e.genre] || [e.genre, ""];
  l.append(el("span", "genre " + e.genre, nom));
  if (texte && !TEXTES.includes(texte)) l.append(etiquetteDeTravail(texte));
  if (e.chambre) l.append(etiquette("chambre-" + e.chambre, CHAMBRES[e.chambre][0],
                                    CHAMBRES[e.chambre]));
  if (e.lecture) l.append(etiquette("", e.lecture, EXPLICATIONS.lecture));
  if (e.conclusion) l.append(etiquette("", e.conclusion, EXPLICATIONS.conclusion));
  return l;
}

function resultatDuVote(vote) {
  const r = el("div", "resultat");
  r.append(el("b", null, vote.sort || "Scrutin"));
  r.append(document.createTextNode(
    ` — ${nb.format(vote.pour)} pour, ${nb.format(vote.contre)} contre, `
    + `${nb.format(vote.abstentions)} abstention${vote.abstentions > 1 ? "s" : ""}`));
  return r;
}

/* Où mène la ligne : la fiche d'un texte de loi ; le dossier d'une résolution
   sur le site de l'Assemblée, comme sa carte dans l'onglet « Travaux » ; nulle
   part pour une question ou un débat, qui ne portent sur aucun texte. */
function destinationDeLEvenement(b, e, texte) {
  const lien = texte && (texte.url_an || texte.url_senat);
  if (texte && TEXTES.includes(texte)) {
    b.addEventListener("click", () => { location.hash = "#/texte/" + e.texte; });
  } else if (lien) {
    b.addEventListener("click", () => window.open(lien, "_blank", "noopener"));
  } else {
    // Sans le texte dans la liste chargée, la fiche s'ouvrirait sur du vide.
    b.disabled = true;
    b.style.cursor = "default";
  }
}

function ligneEvenement(e) {
  const b = el("button", "evt");
  b.append(el("div", "quand", e.heure || "—"));
  const corps = el("div", "corps");
  // Le titre du texte vient des listes déjà chargées ; une question ou un débat
  // n'a pas de texte, et son intitulé tient lieu de titre.
  const texte = texteDuCalendrier(e.texte);
  corps.append(el("h4", null, texte ? texte.titre : e.quoi || "Texte"));
  corps.append(lignesDeLEvenement(e, texte));
  if (texte && e.quoi && e.quoi !== texte.titre) {
    corps.append(el("div", "resultat", e.quoi));
  }
  if (e.auteur) corps.append(auteurDeLEvenement(e.auteur));
  if (e.vote) corps.append(resultatDuVote(e.vote));
  b.append(corps);
  destinationDeLEvenement(b, e, texte);
  return b;
}
