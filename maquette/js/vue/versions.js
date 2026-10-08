/* Les versions d'un texte et ce que chaque étape en a fait, amendements adoptés compris. */

function ligneVersion(uid, v) {
  const li = el("li", "sans-trait");
  const bouton = el("button", "version");
  const q = el("div", "q");
  q.append(el("b", null, v.nom), el("span", "chiffres", chiffresDeVersion(v.resume)));
  bouton.append(q, el("span", "chevron", "›"));
  bouton.addEventListener("click", () => {
    location.hash = `#/version/${uid}/${v.ref}`;
  });
  li.append(bouton);
  return li;
}

function carteAmendementsDeLArticle(liste, uid) {
  const boite = el("div", "amdts");
  if (!liste.length) {
    boite.append(el("p", "rien",
      "Aucun amendement adopté sur cet article : la source ne relie ce "
      + "changement à aucun amendement."));
    return boite;
  }
  const classes = amendementsClasses(liste);
  const debattus = classes.filter(estDebattu).length;
  boite.append(el("div", "chapeau",
    `${nb.format(liste.length)} amendement${liste.length > 1 ? "s" : ""} `
    + `adopté${liste.length > 1 ? "s" : ""}`
    + (debattus ? ` — ${nb.format(debattus)} débattu${debattus > 1 ? "s" : ""}` : "")));
  for (const a of classes) boite.append(ligneAmendement(a, uid));
  return boite;
}

/* Une ligne d'amendement : son numéro, son auteur, son repère s'il en porte
   un, et ses chiffres. **Un seul rendu pour tous les écrans qui en listent** —
   l'onglet « Texte » et l'écran des amendements disputés — sans quoi la même
   ligne se lirait de deux façons selon l'endroit d'où on l'ouvre. */
function ligneAmendement(a, uid) {
  const ligne = el("div", "rang-amdt");
  // **La ligne mène à la fiche de l'amendement, pas au site de
  // l'Assemblée.** Le lien sortant y est, dans la fiche : un seul geste, une
  // seule destination, et le texte de l'amendement s'ouvre sans quitter
  // l'application.
  const bouton = el("button", "vers-amdt");
  bouton.type = "button";
  const teinte = el("i");
  if (a.couleur) teinte.style.background = a.couleur;
  bouton.append(teinte, el("span", "num", "n° " + a.numero));
  // Un amendement du Gouvernement n'a pas de député pour auteur : sa ligne
  // dirait « n° 885 » et rien d'autre. La source nomme son type d'auteur,
  // et c'est ce qu'on affiche à la place.
  const qui = [a.nom, a.sigle].filter(Boolean).join(" · ")
              || (a.typeAuteur === "Député" ? "" : a.typeAuteur || "");
  if (qui) bouton.append(el("span", "qui", qui));
  bouton.append(el("span", "chevron", "›"));
  bouton.addEventListener("click", () => {
    location.hash = `#/amendement/${uid}/${a.uid}`;
  });
  ligne.append(bouton);
  // Où il a été adopté — en commission ou en séance. Il n'y a que dans la
  // comparaison du parcours entier que la question se pose : une étape
  // seule n'a qu'une réponse, déjà écrite au-dessus de la liste.
  if (a.quand) ligne.append(el("span", "quand-amdt", "Adopté " + a.quand));
  // Le repère est un bouton, posé **à côté** du lien et non dedans : un
  // bouton dans un lien n'est pas du HTML valable, et le toucher ouvrirait
  // le site de l'Assemblée au lieu de l'explication.
  if (estDebattu(a)) {
    const marque = etiquette("dispute", "", EXPLICATIONS.amendementDebattu,
                             `n° ${a.numero}`);
    marque.append(el("b", null, "!"),
                  document.createTextNode("Adopté de justesse, après un long échange"));
    ligne.append(marque);
  }
  // Les chiffres s'affichent dès qu'on en a un, repère ou pas : c'est ce
  // qui permet de vérifier le repère, et de voir ce qui lui a manqué.
  const chiffres = [];
  if (a.vote) chiffres.push(`${nb.format(a.vote.pour)} pour, `
                            + `${nb.format(a.vote.contre)} contre`);
  if (a.debat) chiffres.push(`${nb.format(a.debat.orateurs)} orateur`
                             + `${a.debat.orateurs > 1 ? "s" : ""}`);
  if (chiffres.length) ligne.append(el("span", "chiffres-amdt", chiffres.join(" · ")));
  return ligne;
}
