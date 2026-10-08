/* Ce qui s'exécute au chargement : l'aiguillage des adresses, les mesures d'écran, les boutons du haut, le voile, la lecture du socle. Chargé en dernier. */

function router() {
  if (location.hash === "#/calendrier") return ouvrirAgenda();
  if (location.hash === "#/hemicycle") return ouvrirHemicycle();
  const groupe = location.hash.match(/^#\/hemicycle\/(.+)$/);
  if (groupe) return ouvrirHemicycle(decodeURIComponent(groupe[1]));
  const article = location.hash.match(/^#\/change\/([\w-]+)\/(\w+)$/);
  if (article) return ouvrirArticle(article[1], article[2]);
  const change = location.hash.match(/^#\/change\/([\w-]+)$/);
  if (change) return ouvrirChangements(change[1]);
  const version = location.hash.match(/^#\/version\/([\w-]+)\/([\w-]+)$/);
  if (version) return ouvrirVersion(version[1], version[2]);
  const amendement = location.hash.match(/^#\/amendement\/([\w-]+)\/([\w-]+)$/);
  if (amendement) return ouvrirAmendement(amendement[1], amendement[2]);
  const disputes = location.hash.match(/^#\/disputes\/([\w-]+)$/);
  if (disputes) return ouvrirDisputes(disputes[1]);
  if (location.hash === "#/senat/composition") return ouvrirCompositionSenat();
  const grpSenat = location.hash.match(/^#\/senat\/composition\/([\w-]+)$/);
  if (grpSenat) return ouvrirCompositionSenat(decodeURIComponent(grpSenat[1]));
  if (location.hash === "#/senat/calendrier") return ouvrirCalendrierSenat();
  const texte = location.hash.match(/^#\/texte\/([\w-]+)$/);
  if (texte) return ouvrirFiche(texte[1]);
  fermerFiche();
}

let minuterie;

async function charger() {
  $("lien-socle").href = new URL(SOCLE + "/textes.json", location.href).href;
  try {
    const textes = await chargerLesDonnees();
    // La date des **données**, pas celle de la mise en ligne. Les deux ne
    // coïncident pas : une modification de la maquette republie le site avec
    // les données de la veille, la publication ne retéléchargeant les archives
    // que le matin. Afficher l'heure de publication ferait passer des données
    // d'hier pour celles du jour.
    const quand = (ETAT.dernierChargement || {}).fin
                  || ETAT.genereLe || textes.genereLe || "";
    $("maj").textContent = quand.slice(0, 10)
      ? dateLongue.format(enDate(quand.slice(0, 10))) : "inconnue";
    dessiner();
    router();
  } catch (erreur) {
    $("compte").textContent = "Données indisponibles";
    $("fil").append(el("div", "vide",
      "Impossible de lire les données du socle. " +
      "Vérifiez la connexion, ou que la publication a bien eu lieu.\n\n" + erreur.message));
  }
}

$("info-fermer").addEventListener("click", fermer);
$("voile").addEventListener("click", (e) => { if (e.target === $("voile")) fermer(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") fermer(); });
window.addEventListener("hashchange", router);
mesurerLeBandeau();
window.addEventListener("resize", mesurerLeBandeau, { passive: true });
window.addEventListener("resize", mesurerLePied, { passive: true });
// Une seule fois, sur le fil lui-même : les colonnes sont redessinées à
// chaque filtre, l'écouteur ne doit pas l'être avec elles.
surveillerLeTour($("fil"));
/* Les deux boutons du haut suivent l'onglet ouvert : dans « Sénat », ils
   mènent au calendrier et à la composition du Sénat. Même geste, même place,
   l'autre chambre. */
$("bouton-agenda").addEventListener("click", () => {
  location.hash = ONGLET === "senat" ? "#/senat/calendrier" : "#/calendrier";
});
$("bouton-hemicycle").addEventListener("click", () => {
  location.hash = ONGLET === "senat" ? "#/senat/composition" : "#/hemicycle";
});
nommerLesBoutons();
$("bascule").addEventListener("click", () => {
  const boite = $("filtres");
  boite.hidden = !boite.hidden;
  $("bascule").setAttribute("aria-expanded", boite.hidden ? "false" : "true");
  if (!boite.hidden) dessinerFiltres();
});
$("recherche").addEventListener("input", (e) => {
  clearTimeout(minuterie);
  minuterie = setTimeout(() => { filtres.mots = e.target.value; dessiner(); }, 180);
});
charger();
