/* Le fil : le compteur, les colonnes et leurs copies du tour sans fin, les onglets du bas, la frise. */

/* Le compteur dit ce qu'il compte, et chaque onglet compte autre chose. */
function compteDe(liste) {
  const z = $("compte");
  z.innerHTML = "";
  z.append(el("b", null, nb.format(liste.length)));
  const total = VUES[ONGLET].total();
  const sur = liste.length !== total ? ` sur ${nb.format(total)}` : "";

  if (ONGLET === "senat") {
    // Ce que l'onglet ne compte pas vaut ce qu'il compte : deux textes sur
    // trois ne sont jamais allés au Sénat.
    const pl = liste.length > 1 ? "s" : "";
    z.append(document.createTextNode(
      ` texte${pl} passé${pl} au Sénat${sur || ` sur ${nb.format(TEXTES.length)}`}`));
    return;
  }
  if (ONGLET === "travaux") {
    z.append(document.createTextNode(
      ` dossier${liste.length > 1 ? "s" : ""}${sur}`
      + " de l'Assemblée qui n'aboutissent à aucune loi"));
    return;
  }
  // « 22 textes en cours d'examen » serait faux pour 22 textes non adoptés :
  // le compteur ne nomme une issue que s'il n'y en a qu'une.
  const issues = new Set(liste.map(statutDe));
  const finies = liste.filter((t) => t.etape === PROMULGUEE).length;
  let suite = (liste.length > 1 ? " textes" : " texte") + sur;
  if (issues.size === 1) {
    const seule = [...issues][0];
    if (seule === "promulgue") suite += liste.length > 1 ? ", devenus des lois" : ", devenu une loi";
    else if (seule === "en_cours") suite += ", en cours d'examen";
    else suite += ", " + (ISSUES[seule] || ["arrêtés"])[0].toLowerCase() + "s";
  } else if (finies) {
    suite += `, dont ${nb.format(finies)} devenus des lois`;
  }
  z.append(document.createTextNode(suite));
}

/* Un fil vide a deux causes, et il faut les distinguer : les filtres n'ont
   rien laissé passer, ou l'onglet n'a rien reçu du socle. Dire « enlevez un
   filtre » quand il n'y en a aucun enverrait chercher ce qui n'existe pas. */
function filVide() {
  if (combienActifs() || filtres.mots.trim()) {
    const quoi = ONGLET === "travaux" ? "dossier" : "texte";
    return `Aucun ${quoi} ne correspond. Essayez d'enlever un filtre.`;
  }
  if (ONGLET === "senat") {
    return "Aucun texte au Sénat. La publication du jour ne porte pas encore "
         + "ses étapes.";
  }
  if (ONGLET === "travaux") return "Aucun travail à afficher.";
  return "Aucun texte à afficher.";
}

const vraiesColonnes = () => $("fil").querySelectorAll(".colonne:not(.fantome)");

function fleche(signe, ou, rang) {
  const b = el("button", "fleche", signe);
  b.setAttribute("aria-label", "Catégorie " + ou);
  b.addEventListener("click", () => versColonne(rang));
  return b;
}

// Ce que dit le sous-titre d'une colonne : « étape 3 sur 6 », ou la phrase qui
// explique la catégorie. Les travaux n'ont pas d'étapes — ils n'en traversent
// aucune — donc rien à numéroter.
function rangDeLaColonne(cle) {
  if (ONGLET !== "textes") return "";
  if (cle === PROMULGUEE) return "parcours terminé";
  if (cle === ARRETE) return "plus examinés";
  return `étape ${cle} sur 6`;
}

function colonne(cle, textes, rang) {
  const col = el("section", "colonne");
  col.dataset.etape = String(cle);
  const e = categorieDite(cle);
  const fini = ONGLET === "textes" && cle === PROMULGUEE;
  const arret = ONGLET === "textes" && cle === ARRETE;
  const situation = rangDeLaColonne(cle);

  const tete = el("div", "tete-colonne");
  const titre = el("div", "titre-etape");
  if (fini) titre.classList.add("fini");
  if (arret) titre.classList.add("arret");
  titre.append(fleche("‹", "précédente", rang - 1));
  const nom = el("button", "nom", e.nom);
  nom.addEventListener("click", () => expliquer(
    e.nom, e.quoi, situation ? situation[0].toUpperCase() + situation.slice(1) : ""));
  titre.append(nom);
  titre.append(fleche("›", "suivante", rang + 1));
  tete.append(titre);
  const quoi = ONGLET === "textes" ? "texte" : "dossier";
  tete.append(el("div", "sous-etape",
    (situation ? situation + " · " : "")
    + `${nb.format(textes.length)} ${quoi}${textes.length > 1 ? "s" : ""}`));
  col.append(tete);

  let montres = 0;
  const paquetSuivant = () => {
    const ancienBouton = col.querySelector(".plus");
    if (ancienBouton) ancienBouton.remove();
    for (const t of textes.slice(montres, montres + PAR_PAQUET)) col.append(carteDe(t));
    montres = Math.min(montres + PAR_PAQUET, textes.length);
    const reste = textes.length - montres;
    if (reste > 0) {
      const bouton = el("button", "plus",
        `Afficher ${nb.format(Math.min(reste, PAR_PAQUET))} de plus (${nb.format(reste)} restants)`);
      bouton.addEventListener("click", paquetSuivant);
      col.append(bouton);
    }
  };
  paquetSuivant();
  return col;
}

/* Le tour sans fin, sans dupliquer les données.
 *
 * Le navigateur refuse de faire défiler au-delà des bords : arrivé à la
 * dernière catégorie, un glissement de plus ne produit rien. On pose donc de
 * chaque côté une **copie de la colonne d'en face**, prise sur ce qui est
 * déjà affiché — 25 cartes, pas les 1 729 du dépôt. Dès que le défilement
 * s'immobilise sur une copie, on saute sans animation sur la vraie colonne,
 * à l'autre bout. Le lecteur voit une catégorie continue ; il ne voit pas le
 * saut, parce qu'il tombe sur une image identique à ce qu'il regardait.
 */
function poserLesCopies(fil) {
  const colonnes = [...vraiesColonnes()];
  if (colonnes.length < 2) return;
  const copier = (source) => {
    const c = source.cloneNode(true);
    c.classList.add("fantome");
    c.setAttribute("aria-hidden", "true");
    c.querySelectorAll("button").forEach((b) => { b.disabled = true; b.tabIndex = -1; });
    return c;
  };
  fil.prepend(copier(colonnes[colonnes.length - 1]));
  fil.append(copier(colonnes[0]));
}

/* ---------- la frise du bas ---------- *
 * Sept traits : les six étapes du parcours, puis la promulgation, en vert.
 * Ils disent où l'on est et servent à s'y rendre. « Arrêté en chemin » n'a
 * pas de trait — ce n'est pas une étape mais une sortie de route ; la barre
 * le dit en toutes lettres, et on y va en faisant glisser le fil, comme
 * avant. Toucher un trait ou glisser mène au même endroit.
 * ------------------------------------------------------------------ */

// Les deux onglets, sous la frise. Ils restent visibles même quand le fil est
// vide : c'est par eux qu'on repart.
function dessinerOnglets(barre) {
  const onglets = el("div", "onglets");
  for (const [cle, v] of Object.entries(VUES)) {
    const b = el("button", null, v.nom);
    b.setAttribute("aria-selected", String(cle === ONGLET));
    b.append(el("span", "n", nb.format(v.total())));
    b.addEventListener("click", () => changerDOnglet(cle));
    onglets.append(b);
  }
  barre.append(onglets);
}

/* Le trait d'une catégorie sur la frise : passée, en cours, ou vide — et où
   il mène. */
function traitDeLaFrise(categorie, cle, fini, arret, rangDe) {
  const n = vue().cleDe(categorie);
  const estFin = ONGLET === "textes" && n === PROMULGUEE;
  const estArret = ONGLET === "textes" && n === ARRETE;
  // « Passée » n'a de sens que pour un parcours. Les travaux ne se
  // traversent pas : aucune de leurs catégories n'est derrière une autre.
  // Une colonne est « derrière » celle qu'on regarde. Pour les textes, le
  // rang est un numéro d'étape ; pour le Sénat, c'est la place dans l'ordre
  // des colonnes. Les travaux, eux, ne se traversent pas.
  const passee = vue().parcours && !arret && !estArret
                 && (ONGLET === "textes"
                     ? (fini ? !estFin : n < cle)
                     : rangDansLOrdre(n) < rangDansLOrdre(cle));
  const ici = n === cle;
  const b = el("button", [estFin ? "fini" : "", estArret ? "arret" : "",
                          passee ? "faite" : "", ici ? "ici" : ""]
                         .filter(Boolean).join(" "));
  b.setAttribute("aria-label", categorie.nom);
  if (ici) b.setAttribute("aria-current", "step");
  const rang = rangDe(n);
  const vide = rang === -1;
  // Une catégorie vide garde son trait : la frise doit garder la même forme
  // d'un jour à l'autre, sinon elle cesse d'être un repère. Elle ne mène
  // nulle part, mais elle dit ce qu'elle est.
  b.classList.toggle("absent", vide);
  b.append(el("i"));
  b.addEventListener("click", () => vide
    ? expliquer(categorie.nom, categorie.quoi, "Rien dans cette catégorie en ce moment")
    : versColonne(rang));
  return b;
}

function aideDeLaFrise(e, situation) {
  const aide = el("button", "aide", "ⓘ");
  aide.setAttribute("aria-label", "Ce que veut dire cette catégorie");
  aide.addEventListener("click", () => expliquer(
    EXPLICATIONS[ONGLET === "textes" ? "frise"
                 : ONGLET === "senat" ? "friseSenat" : "travaux"][0],
    EXPLICATIONS[ONGLET === "textes" ? "frise"
                 : ONGLET === "senat" ? "friseSenat" : "travaux"][1]
    + "\n\n" + e.nom + " : " + (e.quoi || ""),
    situation ? situation[0].toUpperCase() + situation.slice(1) : ""));
  return aide;
}

function dessinerFriseBas(cle) {
  const barre = $("frise-bas");
  // La frise décrit le fil. Elle ne doit pas réapparaître par-dessus une
  // fiche : le défilement du fil déclenche un événement **après** que la
  // fiche s'est ouverte, et la barre revenait alors toute seule.
  if (!$("fiche").hidden) { barre.hidden = true; return; }
  barre.hidden = false;
  barre.textContent = "";
  if (!CATEGORIES.length) { dessinerOnglets(barre); return; }

  const fini = ONGLET === "textes" && cle === PROMULGUEE;
  const arret = ONGLET === "textes" && cle === ARRETE;
  const rangDe = (c) => CATEGORIES.findIndex(([x]) => x === c);

  const traits = el("div", "traits");
  for (const categorie of vue().ordre()) {
    traits.append(traitDeLaFrise(categorie, cle, fini, arret, rangDe));
  }
  barre.append(traits);

  const e = categorieDite(cle);
  const situation = rangDeLaColonne(cle);
  const dit = el("div", "dit");
  dit.append(el("b", fini ? "fini" : arret ? "arret" : null, e.nom || ""));
  if (situation) dit.append(document.createTextNode(situation));
  dit.append(aideDeLaFrise(e, situation));
  barre.append(dit);
  dessinerOnglets(barre);
}
