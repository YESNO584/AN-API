/* Ce qui s'exécute au chargement : l'aiguillage des adresses, les mesures d'écran, les boutons du haut, la lecture du socle. Chargé en dernier. */

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
window.addEventListener("hashchange", router);

/* ---------- démarrage ---------- */
// L'en-tête se colle sous le bandeau : il lui faut sa hauteur, mesurée, car
// le texte du bandeau passe à deux lignes sur un écran étroit.
function mesurerLeBandeau() {
  const b = document.querySelector(".bandeau");
  if (b) document.documentElement.style
          .setProperty("--haut-bandeau", b.offsetHeight + "px");
}
mesurerLeBandeau();
window.addEventListener("resize", mesurerLeBandeau, { passive: true });

// Le bas de page collé sur une fiche recouvre autant de hauteur qu'il en fait.
// On la mesure — deux phrases tiennent sur deux lignes ou sur quatre selon la
// largeur — pour réserver dessous exactement ce qu'il faut.
function mesurerLePied() {
  const p = document.querySelector("footer");
  if (p) document.documentElement.style
          .setProperty("--haut-pied", p.offsetHeight + "px");
}
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

/* Ce que les deux boutons promettent change avec l'onglet : une étiquette qui
   dirait « Assemblée » dans l'onglet du Sénat tromperait un lecteur qui
   n'entend que ça. */
function nommerLesBoutons() {
  const senat = ONGLET === "senat";
  $("bouton-agenda").setAttribute("aria-label", senat
    ? "Les séances à venir au Sénat" : "Calendrier des séances et des votes");
  $("bouton-hemicycle").setAttribute("aria-label", senat
    ? "La composition du Sénat" : "La composition de l'Assemblée");
}
nommerLesBoutons();

$("bascule").addEventListener("click", () => {
  const boite = $("filtres");
  boite.hidden = !boite.hidden;
  $("bascule").setAttribute("aria-expanded", boite.hidden ? "false" : "true");
  if (!boite.hidden) dessinerFiltres();
});

let minuterie;
$("recherche").addEventListener("input", (e) => {
  clearTimeout(minuterie);
  minuterie = setTimeout(() => { filtres.mots = e.target.value; dessiner(); }, 180);
});

function lire(nom, obligatoire = false) {
  return fetch(`${SOCLE}/${nom}`).then((r) => {
    if (!r.ok) throw new Error(nom + " : réponse " + r.status);
    return r.json();
  }).catch((e) => { if (obligatoire) throw e; return null; });
}

async function charger() {
  $("lien-socle").href = new URL(SOCLE + "/textes.json", location.href).href;
  try {
    const [textes, promulguees, arretes, etat, groupes, travaux, etapes] =
      await Promise.all([
        lire("textes.json", true),
        lire("promulgues.json"),
        lire("arretes.json"),
        lire("etat.json"),
        lire("groupes.json"),
        lire("travaux.json"),
        // Les sujets du Sénat vivent ici, avec les comptes par étape.
        lire("etapes.json"),
      ]);
    // Trois fichiers, trois issues. Les lois promulguées ouvrent le fil — une
    // application qui s'appelle « Qui vote quoi » doit montrer celles
    // qui sont allées au bout. Les textes arrêtés le ferment.
    TEXTES = textes.textes.concat(
      (promulguees?.textes || []).map((t) => ({ ...t, etape: PROMULGUEE })),
      (arretes?.textes || []).map((t) => ({ ...t, etape: ARRETE })));
    // Le plus avancé d'abord — les lois promulguées ouvrent le fil, les textes
    // déposés et jamais examinés le ferment.
    TEXTES.sort((a, b) => b.etape - a.etape ||
                b.date_dernier_mouvement.localeCompare(a.date_dernier_mouvement));
    GROUPES = new Map((groupes?.groupes || []).map((g) => [g.sigle, g]));
    // Les travaux de l'Assemblée : le second onglet. S'ils manquent, l'onglet
    // reste, vide et honnête, plutôt que de disparaître sans explication.
    // L'onglet « Sénat » : les mêmes textes, mais seulement ceux qui y sont
    // passés, et rangés selon les étapes du Sénat. Deux textes sur trois n'y
    // sont jamais allés — ce n'est pas un trou, et l'onglet le dit.
    SENAT = TEXTES.filter((t) => t.senat);
    // Les sujets que le Sénat publie. L'application n'en avait aucun avant
    // lui : on filtrait par étape, par chambre, par type, jamais par « santé ».
    THEMES = (etapes?.themes) || [];
    TRAVAUX = travaux?.travaux || [];
    CATEGORIES_TRAVAUX = travaux?.categories || [];
    ETAT = etat || {};
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

charger();
