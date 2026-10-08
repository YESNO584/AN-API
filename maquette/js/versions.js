/* Les versions d'un texte et ce que chaque étape en a fait, amendements adoptés compris. */

function chiffresDeVersion(r) {
  if (!r) return "";
  if (r.initiaux) return `${nb.format(r.initiaux)} article${r.initiaux > 1 ? "s" : ""}`;
  const bouts = [];
  // « 3 articles modifiés » plutôt que « 3 modifiés » : le premier morceau
  // porte le mot, les suivants s'y rattachent.
  if (r.modifies) bouts.push(`${nb.format(r.modifies)} article${r.modifies > 1 ? "s" : ""} `
                             + `modifié${r.modifies > 1 ? "s" : ""}`);
  if (r.nouveaux) bouts.push(`${nb.format(r.nouveaux)} `
                             + (bouts.length ? "" : `article${r.nouveaux > 1 ? "s" : ""} `)
                             + `nouveau${r.nouveaux > 1 ? "x" : ""}`);
  if (r.retires) bouts.push(`${nb.format(r.retires)} `
                            + (bouts.length ? "" : `article${r.retires > 1 ? "s" : ""} `)
                            + `retiré${r.retires > 1 ? "s" : ""}`);
  // Une version qui ne change rien est un fait, pas un vide : la commission
  // peut adopter le texte sans y toucher.
  return bouts.length ? bouts.join(", ")
                      : `aucun changement sur ${nb.format(r.total)} article${r.total > 1 ? "s" : ""}`;
}

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

/* Un amendement « débattu » : adopté de justesse, après un long échange.
 *
 * Les deux seuils sont ici, et pas dans le socle, parce que c'est un choix
 * d'affichage : le socle publie les chiffres bruts — le scrutin et le nombre
 * d'orateurs — et ne tranche rien.
 *
 * **Le repère ne dit pas « controversé », et c'est voulu.** Mesuré le
 * 2026-09-20 sur les 967 amendements dont on connaît à la fois le vote et le
 * débat : le volume de débat et le serré du vote sont indépendants
 * (corrélation de rang −0,07). Un amendement voté 54 contre 54 a eu 48
 * paragraphes de débat, un autre voté 50 contre 50 en a eu 12. Le repère dit
 * donc ce qu'il compte, et rien de plus.
 *
 * Avec ces seuils, 4 amendements sur les 183 mesurables de la législature le
 * portent — dont celui qui permet de suspendre le permis de conduire d'un
 * usager de stupéfiants, adopté 39 contre 37 après 15 orateurs. */
const ECART_DEBATTU = 0.10;
const ORATEURS_DEBATTU = 8;

const estDebattu = (a) => Boolean(
  a.vote && a.debat && a.vote.ecart != null && a.vote.ecart < ECART_DEBATTU
  && a.debat.orateurs >= ORATEURS_DEBATTU);

// L'écart d'un scrutin, en part des suffrages exprimés : un 39 contre 37 et un
// 390 contre 370 se lisent pareil. Le socle le calcule déjà pour un amendement
// rattaché à un article ; le parcours, lui, part du scrutin brut.
function ecartDuVote(v) {
  const exprimes = (v.pour || 0) + (v.contre || 0);
  return exprimes ? Math.abs(v.pour - v.contre) / exprimes : null;
}

/* L'ordre d'affichage : ce qu'on sait le plus, d'abord. Les amendements dont
   on ne sait rien gardent l'ordre de la source — un tri stable ne les
   mélange pas entre eux. */
function rangAmendement(a) {
  if (estDebattu(a)) return 0;
  if (a.vote && a.debat) return 1;
  if (a.vote || a.debat) return 2;
  return 3;
}

function amendementsClasses(liste) {
  return liste
    .map((a, i) => [a, i])
    .sort(([a, ia], [b, ib]) =>
      rangAmendement(a) - rangAmendement(b)
      // À rang égal, le vote le plus serré passe devant ; à défaut de vote,
      // le débat le plus fourni.
      || ((a.vote ? a.vote.ecart : 2) - (b.vote ? b.vote.ecart : 2))
      || ((b.debat ? b.debat.orateurs : 0) - (a.debat ? a.debat.orateurs : 0))
      || ia - ib)
    .map(([a]) => a);
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

async function ouvrirVersion(uid, ref) {
  const f = ouvrirEcran();
  const retour = boutonRetour("#/texte/" + uid, "Retour au parcours");
  f.append(retour);
  f.append(el("p", "avertissement", "Chargement du texte…"));

  let d;
  try {
    d = await lire(`versions/${uid}/${ref}.json`, true);
  } catch (e) {
    f.textContent = "";
    f.append(retour, el("div", "vide", "Texte indisponible : " + e.message));
    return;
  }
  f.textContent = "";
  f.append(retour);
  f.append(el("h2", "fiche-titre", d.nom));
  f.append(el("p", "fiche-sous", d.precedent
    ? `${dateLongue.format(enDate(d.date))} — comparé au ${d.precedent.nom.toLowerCase()} `
      + `du ${dateLongue.format(enDate(d.precedent.date))}.`
    : `${dateLongue.format(enDate(d.date))} — le texte tel qu'il a été déposé. `
      + `Rien ne le précède : il n'y a rien à comparer.`));

  const tous = (d.articles || []).flatMap((a) => a.morceaux || []);
  // Qui a changé le texte : la commission pour un texte de commission, la
  // séance pour un texte adopté. C'est la forme du document qui le dit.
  const par = /BTC\d+$/.test(d.ref) ? "par la commission"
            : /BTA\d+$/.test(d.ref) ? "en séance"
            : "depuis la version précédente";
  if (tous.length) f.append(legendeDiff(tous, par));

  for (const a of d.articles || []) {
    const tete = el("div", "art-titre");
    tete.append(el("h3", null, a.titre));
    const mots = { modifie: "Modifié", nouveau: "Nouveau", retire: "Retiré",
                   identique: "Inchangé", initial: null };
    if (mots[a.quoi]) tete.append(el("span", "quoi " + a.quoi, mots[a.quoi]));
    // L'état que la source elle-même imprime dans le texte — « (Supprimé) »,
    // « (Non modifié) ». Ce n'est pas notre calcul, c'est sa mention.
    if (a.etat && a.etat !== a.quoi) {
      tete.append(el("span", "quoi", "La source dit : " + a.etat));
    }
    f.append(tete);
    if (A_CHANGE.has(a.quoi)) {
      f.append(carteAmendementsDeLArticle(a.amendements || [], uid));
    }
    f.append(texteCompare(a.morceaux, "diff", a.texte));
  }

  f.append(el("p", "avertissement",
    "Les amendements sont rapprochés par le numéro d'article : la page dit "
    + "lesquels ont été adoptés sur cet article, jamais quel mot vient de quel "
    + "amendement — il faudrait pour cela interpréter l'instruction de "
    + "l'amendement, et le texte affiché ne serait plus celui de la source."));
}

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
