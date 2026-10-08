/* Les gestes des onglets d'une fiche : montrer un onglet, y aller, suivre le glissement du doigt. */

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
