/* Les écrans du Sénat : sa composition et ses séances à venir — les mêmes dessins que ceux de l'Assemblée. */

/* ------------------------------------------------------------------ *
 * La fiche d'un amendement adopté
 *
 * Ce qu'il fait mot pour mot, ce que son auteur en dit, qui a voté quoi, et
 * combien de monde en a parlé. **Un fichier par amendement**, demandé à
 * l'ouverture : deux kilo-octets de médiane, et on n'en demande qu'un — le
 * prix d'une fiche ne dépend pas du texte dont elle vient.
 *
 * Seuls les amendements **adoptés** en ont une : ce sont eux que l'onglet
 * « Texte » relie à un article. Un amendement rejeté reste dans la liste de
 * l'onglet « Amendements », sans fiche à ouvrir.
 * ------------------------------------------------------------------ */

/* Les amendements d'un texte adoptés de justesse après un long échange. Un
   écran à part, et non une rubrique de plus dans la fiche : c'est une question
   qu'on se pose depuis le fil, devant la carte, avant même d'ouvrir le texte.

   Il ne demande aucun fichier — tout est déjà dans la liste chargée au
   démarrage. Chaque ligne mène à la fiche entière de l'amendement, qui elle se
   charge à la demande. */
/* ---------- les deux écrans du Sénat ---------- *
 * La composition et le calendrier, au même endroit que ceux de l'Assemblée :
 * les deux boutons ronds du haut, qui suivent l'onglet ouvert.
 * ------------------------------------------------------------------ */

/* **Le même écran que celui de l'Assemblée, et les mêmes fonctions.** Le
   dessin, la liste des groupes, l'ouverture d'un groupe : tout vient de
   `dessinerHemicycle` et de `.hemi-liste`. Deux versions d'un même dessin
   divergeraient.

   Trois différences, et chacune tient à ce que la source donne ou ne donne
   pas — jamais à un choix d'écran :

   - **Pas de bouton « par siège ».** Il faut un plan de salle. Le Sénat en
     publie un (`senat.fr/vos-senateurs/groupes-politiques.html`), mais ses
     numéros ne sont pas des positions : mesuré le 2026-10-04 sur ce plan,
     le groupe change **152 fois** quand on suit les numéros, contre 9 à
     l'Assemblée. Les placer ainsi éparpillerait chaque groupe sur tout
     l'arc.
   - **Pas de photos** : les mentions légales du Sénat les couvrent par le
     droit d'auteur.
   - **Pas de compte femmes / hommes** : la civilité est publiée, mais elle
     sert déjà à nommer, et rien d'autre ne l'appuie.

   Les couleurs, elles, viennent du site et **ne sont pas de nous** —
   contrairement à celles de l'Assemblée, qui sont une convention. */

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

function ligneSenateur(x) {
  const ligne = el("div", "depute");
  ligne.append(el("div", "sans-photo", "—"));
  const corps = el("div", "corps");
  corps.append(el("b", null, [x.civilite, x.prenom, x.nom].filter(Boolean).join(" ")));
  if (x.circonscription) corps.append(el("span", "ou", x.circonscription));
  ligne.append(corps);
  return ligne;
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
