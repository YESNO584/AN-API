/* Les onglets d'une fiche : la barre, la bande de panneaux qu'on fait glisser, le tour sans fin. */

/* ---------- les onglets de la fiche ---------- *
 * Les rubriques de fond — le vote, ce que la loi change, ce que les groupes
 * en ont dit, le parcours, les amendements — et une seule à l'écran. Empilées,
 * elles obligeaient à défiler à l'aveugle pour savoir ce qu'il y avait plus
 * bas : un texte affiche jusqu'à 150 amendements, et chacun tient sa propre
 * carte. Une rubrique sans contenu n'a pas d'onglet : un onglet vide ferait
 * chercher quelque chose qui n'existe pas.
 *
 * **On passe d'un onglet à l'autre en glissant du doigt**, comme d'une colonne
 * du fil à la suivante : les contenus sont posés côte à côte, la bande
 * s'accroche sur celui qu'on choisit, et le tour est sans fin — après le
 * dernier vient le premier. La barre d'onglets suit le geste et se laisse
 * glisser elle aussi quand les libellés débordent.
 *
 * Une rubrique peut demander ses données au premier affichage de son onglet —
 * jamais avant. L'onglet ouvert d'emblée est le seul dont la demande part avec
 * la fiche.
 * ------------------------------------------------------------------ */

// Le guetteur de hauteur du dernier jeu d'onglets. Une seule fiche est
// ouverte à la fois : le précédent n'a plus rien à surveiller.
let OEIL_ONGLETS = null;

/* Les onglets, leur bande de panneaux et ce qu'on en sait : `o` est l'état
   que les gestes ci-dessous se passent. */
function ajusterLaBande(o) {
  // La hauteur de la bande est celle du panneau affiché. Elle se recalcule
  // dès que son contenu bouge : une liste qui arrive, un dépliant qu'on ouvre.
  o.bande.style.height = o.zones[o.actif].offsetHeight + "px";
}

function montrerLOnglet(o, i) {
  o.actif = i;
  o.boutons.forEach((b, j) => b.setAttribute("aria-selected", j === i ? "true" : "false"));
  if (o.charges[i]) { o.charges[i](); o.charges[i] = null; }
  ajusterLaBande(o);
  // L'onglet allumé vient à l'écran quand la barre déborde : elle doit
  // toujours dire ce qu'on regarde.
  const bt = o.boutons[i], barre = o.barre;
  if (bt.offsetLeft < barre.scrollLeft
      || bt.offsetLeft + bt.offsetWidth > barre.scrollLeft + barre.clientWidth) {
    barre.scrollTo({ left: bt.offsetLeft - (barre.clientWidth - bt.offsetWidth) / 2,
                     behavior: "smooth" });
  }
}

function allerALOnglet(o, i) {
  o.bande.scrollTo({ left: o.zones[i].offsetLeft, behavior: "auto" });
  montrerLOnglet(o, i);
  // Toucher un onglet depuis le bas d'une longue liste laissait la page au
  // milieu du suivant. On remonte à la barre, et seulement si elle est
  // sortie par le haut — sans déroulé, comme pour les colonnes du fil.
  if (o.barre.getBoundingClientRect().top < 0) o.barre.scrollIntoView();
}

/* Le tour sans fin, repris du fil : le navigateur refusant de faire défiler
   au-delà des bords, une **copie du panneau d'en face** est posée de chaque
   côté. Dès que le glissement s'immobilise sur une copie, la bande saute
   sans animation sur le vrai panneau, à l'autre bout — le saut ne se voit
   pas, on tombe sur une image identique à celle qu'on regardait. */
function copiePourLeTour(source) {
  const c = source.cloneNode(true);
  c.classList.add("fantome");
  c.setAttribute("aria-hidden", "true");
  c.querySelectorAll("button, a, summary, input").forEach((n) => {
    n.tabIndex = -1;
    if ("disabled" in n) n.disabled = true;
  });
  return c;
}

function suivreLeGlissement(o) {
  const { bande, zones } = o;
  let minuteur = null;
  bande.addEventListener("scroll", () => {
    // Pendant le geste, l'onglet allumé suit le doigt : la barre dit toujours
    // ce qu'on regarde, et la bande prend la hauteur de ce qui arrive.
    const large = bande.clientWidth || 1;
    const rang = Math.round((bande.scrollLeft - zones[0].offsetLeft) / large);
    if (rang >= 0 && rang < zones.length && rang !== o.actif) montrerLOnglet(o, rang);
    clearTimeout(minuteur);
    // On attend l'immobilité : sauter pendant le geste le couperait net.
    minuteur = setTimeout(() => {
      if (zones.length < 2) return;
      const premiere = zones[0], derniere = zones[zones.length - 1];
      if (bande.scrollLeft < premiere.offsetLeft / 2) {
        bande.scrollTo({ left: derniere.offsetLeft, behavior: "auto" });
        montrerLOnglet(o, zones.length - 1);
      } else if (bande.scrollLeft > derniere.offsetLeft + derniere.offsetWidth / 2) {
        bande.scrollTo({ left: premiere.offsetLeft, behavior: "auto" });
        montrerLOnglet(o, 0);
      }
    }, 120);
  }, { passive: true });
}

function ongletsDeFiche(rubriques) {
  const barre = el("div", "onglets-fiche");
  barre.setAttribute("role", "tablist");
  const o = { barre, bande: el("div", "onglets-corps"),
              boutons: [], zones: [], charges: [], actif: 0 };

  rubriques.forEach(([libelle, contenu, charger], i) => {
    const bt = el("button", null, libelle);
    bt.type = "button";
    bt.setAttribute("role", "tab");
    bt.setAttribute("aria-selected", i === 0 ? "true" : "false");
    bt.addEventListener("click", () => allerALOnglet(o, i));
    barre.append(bt);
    o.boutons.push(bt);

    const zone = el("section", "panneau");
    zone.setAttribute("role", "tabpanel");
    zone.setAttribute("aria-label", libelle);
    zone.append(...[].concat(contenu));
    o.bande.append(zone);
    o.zones.push(zone);
    o.charges.push(charger || null);
  });

  if (o.zones.length > 1) {
    o.bande.prepend(copiePourLeTour(o.zones[o.zones.length - 1]));
    o.bande.append(copiePourLeTour(o.zones[0]));
  }
  suivreLeGlissement(o);

  // Les positions ne se mesurent qu'une fois la bande posée dans la page.
  requestAnimationFrame(() => {
    o.bande.scrollLeft = o.zones[0].offsetLeft;
    montrerLOnglet(o, 0);
    if (OEIL_ONGLETS) OEIL_ONGLETS.disconnect();
    if (window.ResizeObserver) {
      OEIL_ONGLETS = new ResizeObserver(() => ajusterLaBande(o));
      for (const z of o.zones) OEIL_ONGLETS.observe(z);
    }
  });

  return [barre, o.bande];
}
