/* La fiche d'un texte : son en-tête, ses étiquettes, sa description, ses sources, ses cosignataires, son parcours. */

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
