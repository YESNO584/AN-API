/* Ouvrir et refermer un écran à part — fiche, article, amendement, Sénat. */

function ouvrirEcran() {
  const f = $("fiche");
  f.textContent = "";
  f.hidden = false;
  document.body.classList.add("fiche-ouverte");
  mesurerLePied();
  $("fil").hidden = true;
  $("filtres").hidden = true;
  $("frise-bas").hidden = true;
  $("bascule").setAttribute("aria-expanded", "false");
  $("compte").hidden = true;
  document.querySelector(".barre").hidden = true;
  window.scrollTo(0, 0);
  return f;
}

function boutonRetour(vers, libelle) {
  const b = el("button", "retour", "‹ " + libelle);
  b.addEventListener("click", () => { location.hash = vers; });
  return b;
}

function fermerFiche() {
  document.body.classList.remove("fiche-ouverte");
  $("frise-bas").hidden = false;
  $("fiche").hidden = true;
  $("fiche").textContent = "";
  $("fil").hidden = false;
  $("compte").hidden = false;
  // La recherche et les filtres valent dans les trois onglets : la barre
  // revient quel que soit celui d'où l'on vient.
  document.querySelector(".barre").hidden = false;
}
