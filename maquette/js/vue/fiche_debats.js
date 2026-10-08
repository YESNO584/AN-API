/* Ce qui se dit d'un texte : la carte d'un amendement, une prise de parole mot pour mot, et le résumé des débats groupe par groupe. */

function carteAmendement(a) {
  const c = el("article", "amdt");
  const tete = el("div", "tete");
  tete.append(el("span", "num", a.numero || "—"));
  if (a.article) tete.append(el("span", null, a.article));
  if (a.sort) {
    tete.append(el("span", "sort " + (SORTS_AMDT[a.sort] || ""), a.sort));
  }
  if (a.sigle) {
    const g = el("span", "grp");
    const teinte = el("i");
    if (a.couleur) teinte.style.background = a.couleur;
    g.append(teinte);
    g.append(document.createTextNode(a.sigle));
    tete.append(g);
  }
  if (a.nom) tete.append(el("span", null, [a.prenom, a.nom].filter(Boolean).join(" ")));
  c.append(tete);

  const disp = el("p", "disp");
  for (const m of a.morceaux || []) {
    if (m.role === "neutre") disp.append(document.createTextNode(m.texte));
    else {
      const marque = el("span", m.role, "« " + m.texte + " »");
      disp.append(marque);
    }
  }
  c.append(disp);
  if (a.expose) {
    c.append(el("p", "expose", a.expose + (a.exposeTronque ? "" : "")));
  }
  return c;
}

/* ---------- ce que les groupes en ont dit ---------- */

/* Une prise de parole, telle que le compte rendu de séance la publie. **Rien
   n'est résumé ni reformulé** : le texte affiché est celui de la source, et
   le repliement est une affaire de hauteur d'écran, pas de contenu — le
   paragraphe entier est dans la page dès le premier affichage. */
function carteParole(p) {
  const c = el("article", "parole");
  if (p.couleur) c.style.borderLeftColor = p.couleur;

  const tete = el("div", "tete");
  tete.append(el("span", "qui", p.nom || "—"));
  if (p.sigle) {
    const g = el("span", "grp");
    const teinte = el("i");
    if (p.couleur) teinte.style.background = p.couleur;
    g.append(teinte);
    g.append(document.createTextNode(p.sigle));
    tete.append(g);
  }
  if (p.qualite) tete.append(el("span", null, p.qualite));
  tete.append(el("span", "quand",
                 `${dateCourte.format(enDate(p.date))} · ${p.section}`));
  c.append(tete);

  const dit = el("p", "dit replie", p.texte);
  c.append(dit);
  // Le bouton n'apparaît que si le texte dépasse vraiment : sur une parole
  // courte, « Lire la suite » ne mènerait nulle part.
  const plus = el("button", "plus", "Lire la suite");
  c.append(plus);
  requestAnimationFrame(() => {
    if (dit.scrollHeight <= dit.clientHeight + 2) plus.remove();
  });
  plus.addEventListener("click", () => {
    const replie = dit.classList.toggle("replie");
    plus.textContent = replie ? "Lire la suite" : "Replier";
  });
  return c;
}

/* Un groupe et ses arguments, sous sa couleur. */
function carteDuGroupe(g) {
  const carte = el("div", "groupe-dit");
  const tete = el("div", "qui");
  const teinte = el("i");
  const connu = GROUPES.get(g.sigle);
  if (connu?.couleur) teinte.style.background = connu.couleur;
  tete.append(teinte, el("b", null, g.sigle));
  if (connu?.nom) tete.append(el("span", null, connu.nom));
  carte.append(tete);
  const liste = el("ul");
  for (const a of g.arguments) liste.append(el("li", null, a));
  carte.append(liste);
  return carte;
}

function carteDOrateur(o) {
  const carte = el("div", "groupe-dit");
  const tete = el("div", "qui");
  tete.append(el("b", null, o.nom));
  carte.append(tete);
  const liste = el("ul");
  for (const a of o.arguments) liste.append(el("li", null, a));
  carte.append(liste);
  return carte;
}

/* Les camps dans cet ordre, puis les groupes que le scrutin ne nomme pas. */
function campsDuResume(resume) {
  const zones = [];
  const camps = [["pour", []], ["contre", []], ["abstention", []],
                 ["partagé", []], ["aucun_vote", []], [null, []]];
  for (const g of resume.groupes) {
    (camps.find(([nom]) => nom === (g.position || null)) || camps[5])[1].push(g);
  }
  for (const [nom, groupes] of camps) {
    if (!groupes.length) continue;
    const zone = el("div", "camp " + (nom ? nom.replace("é", "e") : "sans-vote"));
    // Sans position et sans scrutin, il n'y a rien à annoncer qu'une parole.
    // Sans position mais avec un scrutin, le groupe n'y figure pas : le dire
    // ainsi, plutôt que de le ranger parmi ceux qui n'ont pas voté.
    zone.append(el("h5", null, nom ? CAMPS[nom]
      : (resume.vote ? "Groupes absents de ce scrutin" : "Ce qui a été dit")));
    for (const g of groupes) zone.append(carteDuGroupe(g));
    zones.push(zone);
  }
  return zones;
}

/* Les orateurs que la source n'a rattachés à aucun groupe : un ministre, un
   non-inscrit. **Ils viennent après les camps, jamais dedans** — un ministre
   n'est pas député, il ne vote pas, il n'a donc pas de camp. Les afficher
   sous un sigle inventé ferait dire à un groupe ce qu'il n'a pas dit. */
function blocDesOrateurs(orateurs) {
  const zone = el("div", "camp orateurs");
  zone.append(el("h5", null, "Dit aussi en séance"));
  // La mention une fois pour toutes, sous le titre : répétée sur chaque
  // carte, elle tenait sur la ligne d'un nom court et passait à la ligne
  // sur un nom long, ce qui donnait deux mises en page pour une même chose.
  zone.append(el("p", "pourquoi-orateurs",
    "Le compte rendu ne rattache ces orateurs à aucun groupe : ce sont des "
    + "membres du gouvernement ou des députés sans groupe. Ils ne votent "
    + "donc pas dans les camps ci-dessus."));
  for (const o of orateurs) zone.append(carteDOrateur(o));
  return zone;
}

function blocResumeDebats(resume) {
  const boite = el("div", "description resume-debats");
  const origine = ORIGINE_RESUME[resume.origine] || ORIGINE_RESUME.ia;

  if (resume.vote) {
    const quand = resume.vote.date
      ? dateLongue.format(enDate(resume.vote.date)) : null;
    const ligne = el("p", "sur-quel-vote");
    ligne.append(document.createTextNode("Groupes rangés d'après le scrutin"
      + (quand ? " du " + quand : "") + " sur l'ensemble du texte"));
    if (resume.vote.sort) ligne.append(el("b", null, " — " + resume.vote.sort));
    boite.append(ligne);
  } else {
    boite.append(el("p", "sur-quel-vote",
      "Aucun scrutin public sur l'ensemble de ce texte : les groupes sont "
      + "rangés comme dans l'hémicycle, de la gauche à la droite."));
  }

  for (const zone of campsDuResume(resume)) boite.append(zone);

  if ((resume.orateurs || []).length) boite.append(blocDesOrateurs(resume.orateurs));

  boite.append(boutonOrigine(resume.origine, origine, resume.le, resume.modele, "écrit"));
  return boite;
}
