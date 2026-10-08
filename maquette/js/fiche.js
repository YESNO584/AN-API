/* La fiche d'un texte : son en-tête, sa description, ses onglets, et ce que la loi change. */

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

/* Le nom d'usage, et d'où il vient : il n'est écrit nulle part dans la source. */
function ligneNomUsage(n) {
  const ligne = el("button", "nom-usage");
  ligne.append(el("b", null, "« " + n.nom + " »"));
  ligne.append(el("u", null, "le nom qu'on lui donne en séance"));
  ligne.title = "Ce nom n'est écrit nulle part dans la source — touchez pour"
              + " savoir d'où il vient.";
  ligne.addEventListener("click", () => expliquer(
    "« " + n.nom + " »",
    "Ce nom n'est écrit nulle part dans les documents de l'Assemblée "
    + "nationale : c'est celui que les orateurs emploient en séance. Il est "
    + "affiché parce qu'on cherche un texte sous le nom qu'on lui connaît, "
    + "pas sous son intitulé officiel. Le compte affiché est relevé dans "
    + "les prises de parole publiées ici, mot entier — il n'est pas écrit "
    + "par la rédaction.",
    n.citations ? "prononcé " + n.citations + " fois en séance" : null));
  return ligne;
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

function blocDescription(description) {
  const origine = ORIGINES[description.origine] || ORIGINES.ia;
  const boite = el("div", "description");
  // Le nom d'usage d'abord : c'est sous ce nom-là qu'on cherche le texte.
  if (description.nomUsage && description.nomUsage.nom) {
    boite.append(ligneNomUsage(description.nomUsage));
  }
  // Le contexte : ce qui se passait avant. Un paragraphe, et facultatif — un
  // texte dont le titre suffit n'en a pas besoin.
  if (description.contexte) boite.append(el("p", "contexte", description.contexte));
  boite.append(el("p", "accroche", description.accroche));
  // Une mesure par puce. Une accroche sans puce reste valable : une loi qui
  // autorise l'approbation d'un traité n'a qu'une chose à dire.
  const points = description.points || [];
  if (points.length) {
    const liste = el("ul");
    for (const point of points) liste.append(el("li", null, point));
    boite.append(liste);
    // Au-delà de trois mesures, la description prenait tout l'écran et la
    // fiche commençait sous le pli. Les autres se demandent.
    if (points.length > VISIBLES) {
      boite.append(boutonDeplier(liste, points.length - VISIBLES));
    }
  }

  boite.append(boutonOrigine(description.origine, origine, description.le,
                             description.modele, "écrite"));
  return boite;
}

/* La fiche prend l'écran : le fil, ses filtres et sa frise se retirent, et le
   bouton de retour se pose en premier. Rend la zone et ce bouton. */
function preparerLaFiche() {
  const f = $("fiche");
  f.textContent = "";
  f.hidden = false;
  document.body.classList.add("fiche-ouverte");
  mesurerLePied();
  $("fil").hidden = true;
  $("filtres").hidden = true;
  // La frise décrit la colonne du fil, pas le texte ouvert : elle se retire.
  $("frise-bas").hidden = true;
  $("bascule").setAttribute("aria-expanded", "false");
  window.scrollTo(0, 0);

  $("compte").hidden = true;
  document.querySelector(".barre").hidden = true;

  const retour = el("button", "retour", "‹ Retour au fil");
  retour.addEventListener("click", () => { location.hash = ""; });
  f.append(retour);
  f.append(el("p", "avertissement", "Chargement de la fiche…"));
  return [f, retour];
}

/* Ce que la loi change au droit se lit en deux endroits, parce que ce sont
   deux questions. **Quand elle s'applique est une question sur le texte
   entier** : c'est la première chose qu'on vient vérifier devant une loi
   promulguée, elle passe donc avant son titre. Le détail de ses articles,
   lui, est une rubrique parmi d'autres — il est dans son onglet, plus bas. */
function laLoiDeLaFiche(uid, d) {
  return d.statut === "promulgue" && !ETAT.droitConsolideIndisponible
    ? { ...d, uid, change: (TEXTES.find((x) => x.uid === uid) || {}).change,
        etape: PROMULGUEE }
    : null;
}

/* Les étiquettes sous le titre : la chambre, l'étape, la nature, l'issue, les
   sujets, le repère des amendements disputés, la procédure accélérée. */
function etiquettesDeLaFiche(uid, d) {
  const l = el("div", "lignes");
  const ch = d.chambre || null;
  l.append(etiquette("chambre-" + (ch || "aucune"), CHAMBRES[ch][0], CHAMBRES[ch]));
  // Où le texte en est : la fiche le taisait, alors que c'est la première
  // chose qu'on vient y chercher.
  if (d.statut === "en_cours" && d.etape) {
    const e = etapeDe(d.etape);
    if (e) l.append(etiquette("", e.nom, [e.nom, e.quoi], `Étape ${e.n} sur 6`));
  }
  l.append(etiquette("", typeCourt(d.type), TYPES[d.type] || [typeCourt(d.type), ""]));
  const issue = ISSUES[d.statut];
  if (issue) l.append(etiquette("arrete", issue[0], issue));
  if (d.statut === "promulgue") {
    l.append(etiquette("promulguee", "Promulguée",
      [etapeDe(PROMULGUEE).nom, etapeDe(PROMULGUEE).quoi],
      d.loi_numero ? "loi n° " + d.loi_numero : null));
  }
  // La procédure accélérée change le parcours entier, et le site de
  // l'Assemblée en fait une bannière : elle mérite mieux qu'une ligne au
  // milieu de trente-sept étapes.
  // Le même repère que sur la carte du fil, et il mène au même écran. Il lit
  // la ligne de la liste, pas la fiche : c'est `textes.json` qui porte les
  // chiffres, parce que la carte en a besoin sans ouvrir le texte.
  const ligne = TEXTES.find((x) => x.uid === uid) || {};
  // Le sujet, comme sur la carte, et lu au même endroit : `textes.json` le
  // porte, la fiche n'a donc rien de plus à charger. Elle les montre **tous**,
  // là où la carte n'en montre qu'un : la place ne manque pas ici.
  for (const sujet of ligne.themes || []) {
    l.append(etiquette("sujet", sujet, EXPLICATIONS.theme));
  }
  const dispute = repereDisputes(ligne);
  if (dispute) l.append(dispute);
  if (d.procedureAcceleree) {
    l.append(etiquette("acceleree", "Procédure accélérée",
      EXPLICATIONS.procedureAcceleree,
      "engagée le " + dateLongue.format(enDate(d.procedureAcceleree.date))));
  }
  return l;
}

/* Les sources, tout en haut : c'est ce qu'on veut sous la main pour aller
   vérifier, pas une annexe à chercher en bas de fiche. */
function sourcesDeLaFiche(d) {
  const sources = el("div", "liens");
  for (const [url, nom, classe] of [
        [d.url_an, "Dossier à l'Assemblée", "officiel"],
        [d.url_senat, "Dossier au Sénat", null],
        [d.loi_url_jo, "Texte au Journal officiel", null]]) {
    if (!url) continue;
    const a = el("a", classe, nom);
    a.href = url; a.target = "_blank"; a.rel = "noopener";
    sources.append(a);
  }
  return sources.children.length ? sources : null;
}

function blocCosignataires(d) {
  const b = bloc(`Cosignataires — ${nb.format(d.cosignatairesTotal)}`);
  for (const p of d.cosignataires) b.append(personne(p));
  if (d.cosignatairesTotal > d.cosignataires.length) {
    b.append(el("p", "avertissement",
      `et ${nb.format(d.cosignatairesTotal - d.cosignataires.length)} autres.`));
  }
  return b;
}

/* Ce qui a été dit en séance. Juste après les articles, et juste après le
   vote qui le précède à l'écran : c'est l'argumentaire du texte entier, pas
   le détail d'une étape. */
async function rubriqueDebats(uid, d) {
  const nbParoles = (TEXTES.find((t) => t.uid === uid) || {}).paroles || 0;
  if (nbParoles) return ["Débats", await blocParoles(uid, nbParoles, true, d.resumeDebats)];
  if (!ETAT.debatsIndisponibles) return null;
  // Ne pas laisser croire que personne n'a parlé du texte alors que c'est
  // la source qui a manqué.
  const b = bloc("Ce que les groupes en ont dit", false, true);
  b.append(el("p", "avertissement",
    "Les comptes rendus de séance n'ont pas pu être récupérés ce matin : leur "
    + "archive de 55,8 Mo n'est pas arrivée entière. Le reste de la fiche est "
    + "à jour. La récupération est retentée chaque matin."));
  return ["Débats", b];
}

function rubriqueParcours(uid, d) {
  const items = filDuParcours(d);
  const nbVotes = (d.votes || []).length;
  const parcours = bloc(
    `Parcours — ${nb.format((d.parcours || []).length)} étapes`
    + (nbVotes ? `, ${nb.format(nbVotes)} vote${nbVotes > 1 ? "s" : ""}` : ""),
    false, true);
  if (!nbVotes) {
    parcours.append(el("p", "avertissement",
      "Aucun scrutin public sur ce texte. C'est le cas le plus fréquent : la " +
      "plupart des textes sont votés à main levée, sans que le vote de chacun " +
      "soit enregistré. La décision de chaque étape, elle, est connue."));
  }
  const ul = el("ul", "parcours");
  for (const x of items) {
    ul.append(x.e ? ligneParcours(x.e)
              : x.s ? ligneVoteSenat(x.s) : ligneVoteParcours(x.v));
    // La version que cette étape a produite, s'il y en a une. Elle se pose
    // sous l'étape parce que c'est l'étape qui l'explique : un texte de
    // commission n'existe qu'à cause de la réunion qui l'a adopté.
    for (const v of (d.versions || [])) {
      if (!x.e || v.etape !== x.e.code || v.date !== x.e.date) continue;
      ul.append(ligneVersion(uid, v));
    }
  }
  parcours.append(ul);
  return ["Parcours", parcours];
}

async function rubriqueAmendements(uid) {
  const nbAmdt = (TEXTES.find((t) => t.uid === uid) || {}).amendements || 0;
  if (nbAmdt) return ["Amendements", await blocAmendements(uid, nbAmdt, true)];
  if (!ETAT.amendementsIndisponibles) return null;
  // Ne pas laisser croire qu'un texte n'a pas d'amendements alors que
  // c'est la source qui a manqué. L'archive pèse 297 Mo et n'arrive pas
  // toujours ; le reste des données, lui, est à jour.
  const b = bloc("Amendements", false, true);
  b.append(el("p", "avertissement",
    "Les amendements n'ont pas pu être récupérés ce matin : leur archive de "
    + "297 Mo n'est pas arrivée entière. Le reste de la fiche est à jour. "
    + "La récupération est retentée chaque matin."));
  return ["Amendements", b];
}

/* Les rubriques de fond, en onglets. Chacune garde son titre exact, avec
   ses comptes : l'onglet dit laquelle on regarde, le titre dit ce qu'elle
   contient. */
async function rubriquesDeLaFiche(uid, d, loi) {
  const rubriques = [];

  // Le vote qui décide : celui sur l'ensemble du texte, et il ouvre la fiche.
  // Le plus récent, car un texte peut être voté dans les deux chambres. Peu de
  // textes en ont un — 71 sur 1 990 — et ceux-là commencent donc par leurs
  // articles ou leur parcours, sans onglet vide.
  const finaux = (d.votes || []).filter((v) => v.portee === "ensemble");
  if (finaux.length) {
    rubriques.push(["Vote", blocVote(finaux.reduce((a, b) => (a.date >= b.date ? a : b)))]);
  }

  // Ce que la loi change au droit, en entier : la liste des articles s'affiche
  // ici même, et se demande à l'ouverture de l'onglet.
  if (loi) rubriques.push(["Articles", ...blocChangements(uid, loi)]);

  // Le texte lui-même, juste après le vote — sauf pour une loi promulguée, où
  // il passe **après les débats, juste avant le parcours** : ce qui compte
  // alors est ce que la loi change au droit, pas le brouillon qu'elle était.
  const versions = d.versions || [];
  const ongletTexte = ["Texte", ...blocTexte(uid, versions, true)];
  if (d.statut !== "promulgue") rubriques.push(ongletTexte);

  const debats = await rubriqueDebats(uid, d);
  if (debats) rubriques.push(debats);

  // Pour une loi promulguée, l'onglet « Texte » se pose ici, juste avant le
  // parcours.
  if (d.statut === "promulgue") rubriques.push(ongletTexte);

  rubriques.push(rubriqueParcours(uid, d));

  const amendements = await rubriqueAmendements(uid);
  if (amendements) rubriques.push(amendements);
  return rubriques;
}

async function ouvrirFiche(uid) {
  const [f, retour] = preparerLaFiche();

  let d;
  try {
    d = await lire(`textes/${uid}.json`, true);
  } catch (e) {
    f.append(el("div", "vide", "Fiche indisponible : " + e.message));
    return;
  }
  f.textContent = "";
  f.append(retour);

  const loi = laLoiDeLaFiche(uid, d);
  if (loi) {
    const vigueur = laVigueur(loi);
    if (vigueur) f.append(vigueur);
  }

  f.append(el("h2", "fiche-titre", d.titre));
  f.append(etiquettesDeLaFiche(uid, d));

  // La description du texte, avant les sources. **C'est la seule exception à
  // la règle « rien n'est écrit par une IA »**, décidée pour cette rubrique et
  // pour elle seule : le reste de la fiche est recopié de la source ou calculé.
  // Elle ne s'affiche que si le socle en publie une — pas de cadre vide.
  if (d.description && d.description.accroche) f.append(blocDescription(d.description));

  const sources = sourcesDeLaFiche(d);
  if (sources) f.append(sources);

  if (d.auteur) f.append(personne(d.auteur, "Auteur du texte"));
  if (d.cosignatairesTotal) f.append(blocCosignataires(d));

  f.append(...ongletsDeFiche(await rubriquesDeLaFiche(uid, d, loi)));
}

/* ------------------------------------------------------------------ *
 * Ce qu'une loi change au droit
 *
 * Deux écrans. La liste des articles, groupés par code, qui ne porte aucun
 * texte et sert à choisir ; puis la fiche d'un article, avec son texte entier
 * et la comparaison. On n'y accède que depuis la fiche du texte : ce n'est
 * pas une rubrique du fil, c'est le détail d'une loi.
 * ------------------------------------------------------------------ */
