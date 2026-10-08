/* Les gestes du fil : changer d'onglet, redessiner, aller à une colonne, suivre le défilement et la frise, poser ou effacer un filtre. */

/* ---------- affichage ---------- */
/* Changer d'onglet **garde** les filtres et la recherche : ils valent
   maintenant dans les trois onglets, et chacun n'applique que les siens. Le
   panneau se referme, parce qu'il ne montre plus les mêmes groupes. */

function changerDOnglet(cle) {
  if (cle === ONGLET) return;
  ONGLET = cle;
  nommerLesBoutons();
  if (!$("filtres").hidden) {
    $("filtres").hidden = true;
    $("bascule").setAttribute("aria-expanded", "false");
  }
  dessiner();
}

/* Les trois onglets se dessinent pareil : la même liste filtrée, le même
   compteur, le même badge, les mêmes colonnes. Seul ce que chacun déclare dans
   `VUES` les sépare. */
function dessiner(garderPosition = false) {
  const y = garderPosition ? window.scrollY : 0;
  const liste = VUES[ONGLET].liste();
  compteDe(liste);

  const b = $("bascule");
  b.textContent = "Filtres";
  const actifs = combienActifs();
  if (actifs) b.append(el("span", "n", String(actifs)));
  if (!$("filtres").hidden) dessinerFiltres();

  const fil = $("fil");
  fil.textContent = "";
  if (!liste.length) {
    fil.append(el("div", "vide", filVide()));
    CATEGORIES = [];
    // La barre du bas reste : c'est par ses onglets qu'on repart.
    dessinerFriseBas(null);
    return;
  }

  dessinerColonnes(liste);
  window.scrollTo(0, garderPosition ? y : 0);
}

function dessinerColonnes(liste) {
  const fil = $("fil");
  const categories = parCategorie(liste);
  CATEGORIES = categories;
  categories.forEach(([etape, textes], rang) =>
    fil.append(colonne(etape, textes, rang)));
  poserLesCopies(fil);
  const cible = vraiesColonnes()[colonneDOuverture(categories)];
  if (cible) fil.scrollLeft = cible.offsetLeft;
  CATEGORIE_VUE = null;
  suivreLaFrise(false);
}

// Le tour est sans fin : après la dernière catégorie vient la première.
function versColonne(rang, glisser = true) {
  const fil = $("fil");
  const colonnes = vraiesColonnes();
  if (!colonnes.length) return;
  const n = colonnes.length;
  const cible = colonnes[((rang % n) + n) % n];
  // `offsetLeft` est mesuré depuis le fil, qui est positionné (CSS
  // `position: relative`) — donc directement utilisable comme défilement.
  fil.scrollTo({ left: cible.offsetLeft, behavior: glisser ? "smooth" : "auto" });
}

function surveillerLeTour(fil) {
  let minuteur = null;
  fil.addEventListener("scroll", () => {
    clearTimeout(minuteur);
    // On attend l'immobilité : sauter pendant le geste le couperait net.
    suivreLaFrise();
    minuteur = setTimeout(() => {
      const colonnes = [...vraiesColonnes()];
      if (colonnes.length < 2) return;
      const premiere = colonnes[0], derniere = colonnes[colonnes.length - 1];
      if (fil.scrollLeft < premiere.offsetLeft / 2) {
        fil.scrollTo({ left: derniere.offsetLeft, behavior: "auto" });
      } else if (fil.scrollLeft > derniere.offsetLeft + derniere.offsetWidth / 2) {
        fil.scrollTo({ left: premiere.offsetLeft, behavior: "auto" });
      }
    }, 120);
  }, { passive: true });
}

// La colonne réellement sous les yeux — celle dont le bord gauche est le plus
// proche du défilement. Les copies du tour sans fin comptent pour la vraie
// colonne qu'elles représentent, sinon la frise clignoterait au passage.
function categorieVisible() {
  const fil = $("fil");
  const colonnes = [...vraiesColonnes()];
  if (!colonnes.length) return null;
  let proche = colonnes[0], ecart = Infinity;
  for (const c of colonnes) {
    const d = Math.abs(c.offsetLeft - fil.scrollLeft);
    if (d < ecart) { ecart = d; proche = c; }
  }
  // La clé d'une colonne est un numéro d'étape dans l'onglet des textes, un
  // nom de catégorie dans celui des travaux. La convertir en nombre dans les
  // deux cas donnait NaN pour les travaux, et la frise gardait l'étape
  // précédente au lieu de suivre.
  const cle = proche.dataset.etape;
  return ONGLET === "textes" ? Number(cle) : cle;
}

function suivreLaFrise(remonter = true) {
  const etape = categorieVisible();
  if (etape === null || (typeof etape === "number" && Number.isNaN(etape))) return;
  if (etape !== CATEGORIE_VUE) {
    // Changer d'étape en étant descendu dans la liste déposait le lecteur au
    // milieu de la nouvelle colonne. Sans animation : sur un changement de
    // colonne, un déroulé donne l'impression que la page part toute seule.
    if (remonter && CATEGORIE_VUE !== null && window.scrollY > 0) {
      window.scrollTo({ top: 0, behavior: "auto" });
    }
    CATEGORIE_VUE = etape;
  }
  dessinerFriseBas(etape);
}

function bascule(ensemble, valeur) {
  ensemble.has(valeur) ? ensemble.delete(valeur) : ensemble.add(valeur);
  dessiner();
}

/* « Tout » veut dire tout, y compris les filtres des autres onglets : ils
   restent posés quand on change d'onglet, et ce bouton est le seul endroit
   d'où les défaire. */
function effacerLesFiltres() {
  filtres.etapes.clear(); filtres.etapesSenat.clear();
  filtres.chambres.clear(); filtres.types.clear(); filtres.themes.clear();
  filtres.activite = null; filtres.programme = false; filtres.vote = null;
  filtres.etat = null; filtres.mots = "";
  $("recherche").value = ""; dessiner();
}
