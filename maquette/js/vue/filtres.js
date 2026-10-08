/* Le panneau des filtres : un groupe de puces par filtre, et le bouton qui efface tout. */

/* Les six étapes du parcours. */
function groupeEtapes(base, compteur) {
  return groupe("Étape du parcours", FRISE_EN_ORDRE.map((e) =>
    puce(e.nom, filtres.etapes.has(e.n), compteur((t) => t.etape === e.n),
         () => bascule(filtres.etapes, e.n),
         [e.nom, e.quoi, e.n === PROMULGUEE ? "Parcours terminé" : `Étape ${e.n} sur 6`])));
}

/* Les cinq moments du Sénat. */
function groupeEtapesSenat(base, compteur) {
  return groupe("Étape au Sénat", ETAPES_SENAT.map((e) =>
    puce(e.nom, filtres.etapesSenat.has(e.cle),
         compteur((t) => (t.senat || {}).moment === e.cle),
         () => bascule(filtres.etapesSenat, e.cle),
         [e.nom, e.quoi])));
}

/* L'issue : en cours, promulguée, rejetée… */
function groupeIssue(base, compteur) {
  const issues = [
    ["en_cours", "En cours d'examen", ["Un texte encore en chemin",
      "Il est quelque part entre son dépôt et sa promulgation. Rien ne dit " +
      "qu'il ira au bout : la plupart s'arrêtent en route."]],
    ["promulgue", "Promulguée",
     [etapeDe(PROMULGUEE).nom, etapeDe(PROMULGUEE).quoi]],
    ["rejete", "Rejeté", ISSUES.rejete],
    ["non_adopte", "Non adopté", ISSUES.non_adopte],
    ["retire", "Retiré", ISSUES.retire],
    ["caduc", "Caduc", ISSUES.caduc],
  ];
  return groupe("Issue", issues.map(([cle, nom, aide]) =>
    puce(nom, filtres.etat === cle, compteur((t) => statutDe(t) === cle),
         () => { filtres.etat = filtres.etat === cle ? null : cle; dessiner(); },
         aide)));
}

/* **Le sujet d'un texte, et la seule chose que l'application ne savait pas
   dire.** Les thèmes viennent du Sénat, qui est le seul à classer : les
   textes qui n'y sont jamais allés n'en portent aucun, et le groupe le dit
   sous les puces plutôt que de les faire disparaître sans raison. */
function groupeSujets(base, compteur) {
  if (!THEMES.length) return null;
  const compte = new Map(THEMES.map((x) =>
    [x.nom, compteur((t) => (t.themes || []).includes(x.nom))]));
  const ranges = [...THEMES].sort((x, y) => compte.get(y.nom) - compte.get(x.nom)
                                            || x.nom.localeCompare(y.nom, "fr"));
  const sujets = groupe("Sujet", ranges.map((x) =>
    puce(x.nom, filtres.themes.has(x.nom), compte.get(x.nom),
         () => bascule(filtres.themes, x.nom),
         ["Le sujet d'un texte",
          "Le classement est celui du Sénat, repris tel quel : c'est le seul " +
          "des deux à en publier un. Un texte peut porter plusieurs sujets."])));
  // **La raison d'un sujet manquant n'est pas la même dans les deux
  // onglets.** Dans « Textes », c'est que le texte n'est jamais allé au
  // Sénat ; dans « Sénat », il y est forcément allé — c'est le Sénat qui
  // n'a rien classé. Dire la première phrase ici serait faux.
  const sans = base.filter((t) => !(t.themes || []).length).length;
  if (sans > 0) {
    sujets.append(el("p", "rien",
      `${nb.format(sans)} texte${sans > 1 ? "s" : ""} sur `
      + `${nb.format(base.length)} n'${sans > 1 ? "ont" : "a"} aucun sujet : `
      + (ONGLET === "senat"
          ? "le Sénat n'en a publié aucun pour eux."
          : "ils ne sont jamais allés au Sénat, et l'Assemblée n'en publie "
            + "pas.")
      + " Filtrer par sujet les écarte."));
  }
  return sujets;
}

/* Où le texte se trouve. */
function groupeChambres(base, compteur) {
  return groupe("Où le texte se trouve", ["assemblee", "senat", "aucune"].map((c) =>
    puce(c === "aucune" ? "Les deux" : CHAMBRES[c][0],
         filtres.chambres.has(c), compteur((t) => (t.chambre || "aucune") === c),
         () => bascule(filtres.chambres, c),
         c === "aucune" ? CHAMBRES[null] : CHAMBRES[c])));
}

/* La nature du texte, les plus fréquentes d'abord. */
function groupeNature(base, compteur) {
  const compte = new Map();
  for (const t of base) compte.set(t.type, (compte.get(t.type) || 0) + 1);
  const presents = [...compte.keys()].sort((x, y) => compte.get(y) - compte.get(x));
  return groupe("Nature du texte", presents.map((ty) =>
    puce(typeCourt(ty), filtres.types.has(ty), compte.get(ty),
         () => bascule(filtres.types, ty),
         TYPES[ty] || [ty, "Une catégorie de texte que le Parlement distingue."])));
}

/* Le dernier mouvement : récent, ou à l'arrêt. */
function groupeMouvement(base, compteur) {
  return groupe("Dernier mouvement", Object.entries(ACTIVITE).map(([cle, [nom, seuil]]) =>
    puce(nom, filtres.activite === cle,
         compteur((t) => { const x = jours(t.date_dernier_mouvement);
                           return seuil > 0 ? x <= seuil : x >= -seuil; }),
         () => { filtres.activite = filtres.activite === cle ? null : cle; dessiner(); },
         seuil > 0
           ? ["Textes qui ont bougé récemment",
              "Un événement — dépôt, réunion, débat, vote — a eu lieu sur ce texte " +
              "pendant la période choisie. C'est la façon la plus simple de voir ce " +
              "sur quoi le Parlement travaille en ce moment.", nom]
           : EXPLICATIONS.dormant)));
}

/* Les votes de l'Assemblée. */
function groupeVotes(base, compteur) {
  return groupe("Votes", [
    puce("A fait l'objet d'un vote", filtres.vote === "tous",
         compteur((t) => t.votes > 0),
         () => { filtres.vote = filtres.vote === "tous" ? null : "tous"; dessiner(); },
         EXPLICATIONS.vote),
    puce("Voté sur le texte entier", filtres.vote === "ensemble",
         compteur((t) => !!t.voteEnsemble),
         () => { filtres.vote = filtres.vote === "ensemble" ? null : "ensemble"; dessiner(); },
         EXPLICATIONS.voteEnsemble),
    puce("Adopté", filtres.vote === "adopte",
         compteur((t) => t.voteEnsemble && t.voteEnsemble.sort === "adopté"),
         () => { filtres.vote = filtres.vote === "adopte" ? null : "adopte"; dessiner(); },
         ["Adopté sur l'ensemble",
          "La chambre a voté pour le texte entier. Il poursuit son parcours — " +
          "cela ne veut pas dire qu'il est devenu une loi."]),
    puce("Rejeté", filtres.vote === "rejete",
         compteur((t) => t.voteEnsemble && t.voteEnsemble.sort !== "adopté"),
         () => { filtres.vote = filtres.vote === "rejete" ? null : "rejete"; dessiner(); },
         ["Rejeté sur l'ensemble",
          "La chambre a voté contre le texte entier."]),
  ]);
}

/* Ce qui est déjà programmé. */
function groupeCalendrier(base, compteur) {
  return groupe("Calendrier", [
    puce("Séance déjà programmée", filtres.programme,
         compteur((t) => !!t.prochaine_date),
         () => { filtres.programme = !filtres.programme; dessiner(); },
         EXPLICATIONS.prochaine),
    puce("Vote annoncé", false, 0, () => {},
         EXPLICATIONS.aucunVote)]);
}

function boutonToutEffacer() {
  const effacer = el("button", "effacer", "Tout effacer");
  effacer.disabled = combienActifs() === 0 && !filtres.mots;
  effacer.addEventListener("click", effacerLesFiltres);
  return effacer;
}

function dessinerFiltres() {
  const boite = $("filtres");
  boite.textContent = "";
  const v = ONGLET;
  // **Les comptes se mesurent sur l'onglet, pas sur l'Assemblée.** Dans
  // l'onglet du Sénat, « Justice 40 » doit vouloir dire 40 textes passés au
  // Sénat — afficher 67 ferait promettre à la puce des textes qu'elle
  // n'ouvrira jamais.
  const base = VUES[v].base();
  const compteur = (predicat) => base.filter(predicat).length;

  // Un groupe de puces par filtre, dans cet ordre — et seulement ceux que
  // l'onglet déclare : un filtre absent de sa liste n'est ni dessiné, ni
  // appliqué, ni compté.
  const groupes = [
    ["etapes", groupeEtapes], ["etapesSenat", groupeEtapesSenat], ["etat", groupeIssue],
    ["themes", groupeSujets], ["chambres", groupeChambres], ["types", groupeNature],
    ["activite", groupeMouvement], ["vote", groupeVotes], ["programme", groupeCalendrier],
  ];
  for (const [nom, dessin] of groupes) {
    if (!aLeFiltre(nom, v)) continue;
    const g = dessin(base, compteur);
    if (g) boite.append(g);
  }
  boite.append(boutonToutEffacer());
}
