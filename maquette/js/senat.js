/* Les deux écrans du Sénat : sa composition et ses séances à venir — les mêmes dessins que ceux de l'Assemblée. */

function sousTitreDuSenat(d, groupes) {
  const sous = el("p", "fiche-sous",
    `${nb.format(d.effectif)} sénateurs, ${groupes.length} groupes, `
    + "de la gauche à la droite de l'hémicycle. ");
  const aide = el("button", "aide", "ⓘ");
  aide.setAttribute("aria-label", "Ce que ce dessin montre, et ce qu'il ne montre pas");
  aide.addEventListener("click", () => expliquer(...EXPLICATIONS.compositionSenat,
                                                 "Ordre mesuré, sens convenu"));
  sous.append(aide);
  return sous;
}

/* L'hémicycle du Sénat, et ce que l'écran doit dire au lieu de le cacher : un
   hémicycle de 169 sièges sans explication laisserait croire à un Sénat à
   moitié vide. */
function dessinDuSenat(zone, d, groupes, places, choisi, sigle) {
  const svg = dessinerHemicycle(groupes, places);
  svg.setAttribute("aria-label",
    `${nb.format(places)} sièges coloriés par groupe, de la gauche à la droite`);
  zone.append(svg);
  svg.classList.toggle("un-seul", !!choisi);
  svg.querySelectorAll("g").forEach(
    (n) => n.classList.toggle("vu", !!choisi && n.dataset.sigle === choisi.sigle));
  svg.addEventListener("click", (ev) => {
    const part = ev.target.closest("g");
    const vise = part && part.dataset.sigle;
    if (vise) location.hash = vise === sigle
      ? "#/senat/composition" : "#/senat/composition/" + encodeURIComponent(vise);
  });

  // **Ce que l'écran doit dire au lieu de le cacher.** Un hémicycle de 169
  // sièges sans explication laisserait croire à un Sénat à moitié vide.
  if (d.sansGroupe) {
    zone.append(el("p", "sous-dessin",
      `${nb.format(places)} sénateurs dans un groupe. Les `
      + `${nb.format(d.sansGroupe)} autres ne sont pas des non-inscrits : `
      + "après le renouvellement du 27 septembre 2026, les groupes ont été "
      + "clos et ne se sont pas encore reformés. Le dessin se remplira de "
      + "lui-même."));
  }
}

/* Les sénateurs du groupe ouvert — la même ligne qu'un député, sans la photo :
   les mentions légales du Sénat couvrent les photographies par le droit
   d'auteur. */
function senateursDuGroupe(f, d, choisi) {
  const membres = (d.senateurs || []).filter((x) => x.groupe === choisi.sigle);
  const detail = el("p", "fiche-sous",
    `${nb.format(membres.length)} sénateurs, classés par nom. `);
  const aideNoms = el("button", "aide", "ⓘ");
  aideNoms.setAttribute("aria-label", "D'où viennent ces noms");
  aideNoms.addEventListener("click",
    () => expliquer(...EXPLICATIONS.senateurs, choisi.nom || choisi.sigle));
  detail.append(aideNoms);
  f.append(detail);

  // La même ligne qu'un député, sans la photo : les mentions légales du Sénat
  // couvrent les photographies par le droit d'auteur.
  const lignes = el("div", "deputes");
  for (const x of membres) lignes.append(ligneSenateur(x));
  f.append(lignes);
}

async function ouvrirCompositionSenat(sigle = null) {
  const f = ouvrirEcran();
  f.append(boutonRetour("", "Retour au fil"));
  f.append(el("h2", "fiche-titre", "Le Sénat"));
  f.append(el("p", "avertissement", "Chargement…"));

  const d = await lire("senat/composition.json");
  f.textContent = "";
  f.append(boutonRetour("", "Retour au fil"));
  f.append(el("h2", "fiche-titre", "Le Sénat"));
  if (!d || !(d.groupes || []).length) {
    f.append(el("div", "vide",
      "La composition du Sénat n'est pas publiée aujourd'hui. Les données du "
      + "Sénat sont une source facultative : le reste du site est à jour."));
    return;
  }

  const groupes = d.groupes.filter((g) => g.effectif > 0);
  const choisi = groupes.find((g) => g.sigle === sigle) || null;
  // Le dessin montre les sénateurs **qui ont un groupe**. Les 179 qui n'en ont
  // pas encore ne sont pas des non-inscrits : les faire figurer en gris les
  // donnerait pour tels.
  const places = groupes.reduce((n, g) => n + g.effectif, 0);

  f.append(sousTitreDuSenat(d, groupes));

  const veille = avisDuSenat();
  if (veille) f.append(veille);

  const zone = el("div", "hemicycle");
  f.append(zone);
  dessinDuSenat(zone, d, groupes, places, choisi, sigle);

  const liste = el("div", "hemi-liste");
  f.append(liste);
  for (const g of (choisi ? [choisi] : groupes)) {
    liste.append(ligneDeGroupe(g, choisi, g.nom || g.sigle, g.nomComplet || "",
                               " sén.", "#/senat/composition"));
  }

  f.append(el("p", "avertissement",
    "L'ordre des groupes est mesuré sur leur façon de voter, et non sur leurs "
    + "sièges : la numérotation du Sénat tourne rang par rang, et le groupe y "
    + "change 152 fois quand on suit les numéros. Il sépare nettement la "
    + "gauche, le centre et la droite ; à l'intérieur de ces blocs il ne "
    + "départage pas, et le sens — quel bout est la gauche — est une "
    + "convention assumée. Les couleurs, elles, sont celles du Sénat."));

  if (!choisi) return;

  senateursDuGroupe(f, d, choisi);

}

function ligneSenateur(x) {
  const ligne = el("div", "depute");
  ligne.append(el("div", "sans-photo", "—"));
  const corps = el("div", "corps");
  corps.append(el("b", null, [x.civilite, x.prenom, x.nom].filter(Boolean).join(" ")));
  if (x.circonscription) corps.append(el("span", "ou", x.circonscription));
  ligne.append(corps);
  return ligne;
}

/* **La même grille que celle de l'Assemblée**, remplie des séances à venir au
   Sénat. Il n'y en a que quelques-unes, et c'est normal : le Sénat ne publie
   une séance qu'une fois inscrite à son ordre du jour. Le mois s'ouvre donc
   sur celui qui en porte, pas sur le mois en cours s'il est vide. */
async function ouvrirCalendrierSenat() {
  const f = ouvrirEcran();
  f.append(boutonRetour("", "Retour au fil"));
  f.append(el("h2", "fiche-titre", "Les séances à venir au Sénat"));
  f.append(el("p", "avertissement", "Chargement…"));

  const d = await lire("senat/calendrier.json");
  f.textContent = "";
  f.append(boutonRetour("", "Retour au fil"));
  f.append(el("h2", "fiche-titre", "Les séances à venir au Sénat"));
  const jours = (d && d.jours) || [];
  if (!jours.length) {
    f.append(el("div", "vide",
      "Aucune séance annoncée. Le Sénat ne publie une séance qu'une fois "
      + "inscrite à son ordre du jour, et le calendrier se vide pendant les "
      + "vacances parlementaires."));
    return;
  }

  // Un événement par texte inscrit, à plat : c'est la forme que la grille
  // attend, et elle n'a pas à connaître celle du fichier du Sénat.
  const evenements = [];
  for (const j of jours) {
    for (const t of j.textes) evenements.push({ ...t, date: j.date });
  }
  const mois = [...new Set(evenements.map((e) => moisDe(e.date)))].sort();

  f.append(el("p", "fiche-sous",
    `${nb.format(evenements.length)} séance${evenements.length > 1 ? "s" : ""} `
    + `annoncée${evenements.length > 1 ? "s" : ""}, sur `
    + `${nb.format(jours.length)} jour${jours.length > 1 ? "s" : ""}.`));
  const veille = avisDuSenat();
  if (veille) f.append(veille);

  const source = {
    mois: () => mois,
    charger: (m) => evenements.filter((e) => moisDe(e.date) === m),
    ligne: (e) => ligneSeanceSenat(e),
    vide: "Aucune séance ce mois-ci. Le Sénat ne publie une séance qu'une "
        + "fois inscrite à son ordre du jour.",
  };

  // Le mois en cours s'il porte quelque chose, sinon le premier qui en porte :
  // une grille vide au premier regard ne dit pas où aller.
  MOIS_VU = mois.includes(moisDe(aujourdhui())) ? moisDe(aujourdhui()) : mois[0];
  JOUR_VU = null;
  const zone = el("div");
  f.append(zone);
  await dessinerMois(zone, source);
}

/* La ligne d'une séance du Sénat, bâtie comme celle d'un événement de
   l'Assemblée. Pas d'heure — le Sénat ne la publie pas — et pas de genre : ce
   sont toutes des séances publiques. */
function ligneSeanceSenat(e) {
  const b = el("button", "evt");
  b.append(el("div", "quand", "—"));
  const corps = el("div", "corps");
  // Un texte que nous ne suivons pas : on le dit plutôt que de le taire.
  corps.append(el("h4", null, e.titre || "Un texte du Sénat que nous ne suivons pas encore"));
  const l = el("div", "lignes");
  l.append(etiquette("chambre-senat", CHAMBRES.senat[0], CHAMBRES.senat));
  l.append(etiquette("", "Séance publique", EXPLICATIONS.friseSenat));
  corps.append(l);
  b.append(corps);
  if (e.uid && e.titre) {
    b.addEventListener("click", () => { location.hash = "#/texte/" + e.uid; });
  } else {
    b.disabled = true;
    b.style.cursor = "default";
  }
  return b;
}
