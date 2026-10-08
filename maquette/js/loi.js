/* Ce qu'une loi promulguée change au droit : la liste des articles, et la fiche d'un article avec ses trois lectures. */

async function ouvrirChangements(uid) {
  const f = ouvrirEcran();
  const retour = boutonRetour("#/texte/" + uid, "Retour au texte");
  f.append(retour);
  f.append(el("p", "avertissement", "Chargement…"));

  let d;
  try {
    d = await lire(`changements/${uid}.json`, true);
  } catch (e) {
    f.textContent = "";
    f.append(retour, el("div", "vide", "Détail indisponible : " + e.message));
    return;
  }
  f.textContent = "";
  f.append(retour);

  const texte = TEXTES.find((x) => x.uid === uid);
  f.append(el("h2", "fiche-titre", texte ? texte.titre : "Ce que cette loi change"));
  const ajouts = d.articlesAjoutes || [];
  const sous = el("p", "fiche-sous",
    (d.loi ? "LOI n° " + d.loi + " — " : "")
    + (ajouts.length ? "ce qu'elle change au droit, et ce qu'elle y ajoute."
                     : "ce qu'elle change au droit."));
  f.append(sous);
  f.append(...contenuDesChangements(uid, d));
}

/* La liste elle-même : les compteurs, les articles groupés par code, les
 * retouches, et ce que la loi ajoute. Écrite une fois et posée à deux
 * endroits — l'onglet « Articles » de la fiche et cet écran, atteint depuis
 * la carte du fil. Deux copies auraient divergé au premier changement.
 * ------------------------------------------------------------------ */
function contenuDesChangements(uid, d) {
  const f = [];
  const ajouts = d.articlesAjoutes || [];

  // Le résumé : combien d'articles modifiés, créés, abrogés. Un compte, pas
  // une appréciation. La quatrième tuile ne s'affiche que si la loi a écrit
  // ses propres articles — annoncer un zéro pour toutes les autres lois
  // ferait chercher un chiffre qui n'a rien à dire.
  const actions = d.actions || {};
  const resume = el("div", "resume-change");
  // Les trois premières restent même à zéro : un « 0 abrogés » se lit, et la
  // rangée garde la même forme d'une loi à l'autre. Mais une loi qui n'amende
  // rien n'a aucune raison d'afficher trois zéros — elle n'a que ses propres
  // articles à montrer.
  const tuiles = (d.groupes || []).length
    ? [["MODIFIE", "modifiés", actions.MODIFIE || 0],
       ["CREE", "créés", actions.CREE || 0],
       ["ABROGE", "abrogés", actions.ABROGE || 0]]
    : [];
  if (ajouts.length) tuiles.push(["AJOUTE", "nouveaux", ajouts.length]);
  for (const [cle, nom, valeur] of tuiles) {
    const tuile = el("div", "tuile " + cle);
    tuile.append(el("b", null, nb.format(valeur)), el("span", null, nom));
    resume.append(tuile);
  }
  f.push(resume);

  for (const groupe of d.groupes || []) {
    const boite = el("details", "code-groupe");
    boite.open = (d.groupes.length <= 3);
    const titre = el("summary");
    const zone = el("div");
    zone.append(el("b", null, groupe.ou));
    zone.append(el("i", null,
      `${nb.format(groupe.articles.length)} article${groupe.articles.length > 1 ? "s" : ""}`));
    titre.append(zone);
    boite.append(titre);
    for (const a of groupe.articles) boite.append(ligneArticle(uid, a));
    f.push(boite);
  }

  // Les articles retouchés sans changement de fond : hors du compte, mais pas
  // cachés. Les compter comme modifiés ferait dire à l'application qu'une loi
  // a changé quelque chose là où elle n'a rien changé.
  const retouches = d.articlesRetouches || [];
  if (retouches.length) {
    const boite = el("details", "retouches");
    const titre = el("summary");
    titre.append(el("b", null,
      `${nb.format(retouches.length)} article${retouches.length > 1 ? "s" : ""} retouché`
      + `${retouches.length > 1 ? "s" : ""}`));
    titre.append(document.createTextNode(" sans changement de fond — "
      + "seule la ponctuation ou les espaces ont bougé."));
    boite.append(titre);
    for (const a of retouches) boite.append(ligneArticle(uid, a, true));
    f.push(boite);
  }

  // Ce que la loi **ajoute** : ses propres articles. Une liste à part, parce
  // qu'ils n'ont pas d'avant — il n'y a rien à superposer, seulement un texte
  // à lire. Les mêler aux articles changés obligerait à afficher une « part
  // de texte changé » qui ne veut rien dire pour un article neuf.
  if (ajouts.length) {
    const boite = el("details", "code-groupe");
    // Le même seuil que les groupes d'articles changés, pour la même raison :
    // sur un texte qui touche à vingt codes, tout déplier noie l'écran ; sur
    // une loi de finances, qui n'en change que deux, replier ses propres
    // articles reviendrait à cacher toute sa matière.
    boite.open = (d.groupes || []).length <= 3;
    const titre = el("summary");
    const zone = el("div");
    zone.append(el("b", null, "Ce que cette loi ajoute"));
    zone.append(el("i", null,
      `${nb.format(ajouts.length)} article${ajouts.length > 1 ? "s" : ""} `
      + `qu'elle a écrit${ajouts.length > 1 ? "s" : ""}`));
    titre.append(zone);
    boite.append(titre);
    for (const a of ajouts) boite.append(ligneArticle(uid, a));
    f.push(boite);
  }

  f.push(el("p", "avertissement",
    "Les articles que la loi se contente de citer ne sont pas comptés ici : "
    + "elle n'y touche pas."
    + (ajouts.length ? " Et les articles par lesquels elle ne fait qu'en "
                     + "modifier d'autres non plus : leur contenu est déjà "
                     + "montré, sous forme des articles qu'ils changent." : "")));
  return f;
}

function ligneArticle(uid, a, retouche = false) {
  const b = el("button", "art");
  b.append(el("span", "quoi " + a.quoi, a.action));
  const nom = el("div", "nom");
  // Les états et annexes des lois de finances n'ont pas de numéro dans la
  // source : « Article » suivi de rien ne dit rien. On montre alors le début
  // de leur texte, tel qu'il est écrit.
  nom.append(el("b", null, a.numero ? "Article " + a.numero
                                    : a.intitule || "Article sans numéro"));
  // « 19 % du texte a changé » se lit ; « 81 % commun » demande un effort.
  // Pour un article retouché, ce pourcentage serait trompeur : il annoncerait
  // qu'une part du texte a changé alors que seule la typographie a bougé. On
  // met le code à la place — c'est ce qui manque quand la liste est à plat.
  nom.append(el("span", null,
    retouche ? a.ou
    // La source publie parfois l'article avant d'en avoir saisi le texte.
    // Annoncer « 4 mots, texte nouveau » ferait passer sa phrase d'attente
    // pour de la loi.
    : a.enAttente ? "texte pas encore publié par la source"
    : a.commun !== null ? `${100 - a.commun} % du texte a changé`
    : a.avant === "manquant" ? "rédaction précédente non retrouvée"
    : `${nb.format(a.mots)} mot${a.mots > 1 ? "s" : ""}, texte nouveau`));
  if (a.commun !== null && !retouche) {
    const jauge = el("div", "jauge");
    const barre = el("i");
    barre.style.width = Math.max(2, 100 - a.commun) + "%";
    jauge.append(barre);
    nom.append(jauge);
  }
  b.append(nom, el("span", "chevron", "›"));
  b.addEventListener("click", () => {
    location.hash = `#/change/${uid}/${a.id}`;
  });
  return b;
}

// Comment le texte est montré : les différences, le texte en vigueur seul, ou
// celui d'avant seul. Le choix se garde d'un article à l'autre.
let MODE_TEXTE = "diff";

async function ouvrirArticle(uid, identifiant) {
  const f = ouvrirEcran();
  const retour = boutonRetour("#/change/" + uid, "Tous les articles");
  f.append(retour);
  f.append(el("p", "avertissement", "Chargement…"));

  let a;
  try {
    a = await lire(`changements/${uid}/${identifiant}.json`, true);
  } catch (e) {
    f.textContent = "";
    f.append(retour, el("div", "vide", "Article indisponible : " + e.message));
    return;
  }
  dessinerArticle(f, retour, uid, a);
}

/* Les deux façons de montrer une comparaison — la légende et le texte
 * coloré — servent à deux écrans : un article de loi modifié par une loi
 * promulguée, et une version d'un texte modifiée par la commission ou la
 * séance. C'est le même calcul (`difflib`, mot à mot, la ponctuation au
 * caractère) et le même dessin ; seule change la phrase qui nomme l'auteur du
 * changement.
 * ------------------------------------------------------------------ */
function legendeDiff(morceaux, par) {
  const legende = el("div", "legende-diff");
  const entree = (balise, classe, mot, suite) => {
    const s = el("span");
    s.append(el(balise, classe, mot), document.createTextNode(" " + suite));
    return s;
  };
  // Chaque entrée n'apparaît que si le texte en contient : une légende qui
  // annonce une couleur absente fait chercher pour rien. Un article
  // simplement retouché n'a ni retrait ni ajout de fond.
  const ya = (role, forme) => (morceaux || [])
    .some((m) => m.role === role && Boolean(m.forme) === forme);
  if (ya("retire", false)) legende.append(entree("s", null, "retiré", par));
  if (ya("ajoute", false)) legende.append(entree("u", null, "ajouté", par));
  if (ya("ajoute", true)) legende.append(entree("u", "forme", "ponctuation", "ajoutée"));
  if (ya("retire", true)) legende.append(entree("s", "forme", "ponctuation", "retirée"));
  return legende;
}

function texteCompare(morceaux, mode, texte) {
  const corps = el("div", "texte-loi");
  // Un texte sans comparaison — la version déposée, un article nouveau — n'a
  // pas de morceaux : il s'affiche tel quel.
  if (!(morceaux || []).length) {
    corps.textContent = texte || "";
    return corps;
  }
  let debut = true;
  for (const m of morceaux) {
    if (mode === "avant" && m.role === "ajoute") continue;
    if (mode === "apres" && m.role === "retire") continue;
    const balise = mode === "diff" && m.role === "retire" ? "del"
                 : mode === "diff" && m.role === "ajoute" ? "ins" : "span";
    // Une retouche de forme est découpée au caractère : « I- », l'espace
    // ajoutée, « Sont ». Ces morceaux se collent au précédent — sinon on
    // insérerait des espaces au milieu des mots.
    if (!m.colle && !debut) corps.append(document.createTextNode(" "));
    const classe = mode === "diff" && m.forme ? "forme" : null;
    corps.append(el(balise, classe, m.texte));
    debut = false;
  }
  return corps;
}

function dessinerArticle(f, retour, uid, a) {
  f.textContent = "";
  f.append(retour);
  f.append(el("h2", "fiche-titre", a.numero ? "Article " + a.numero
                                            : a.intitule || "Article sans numéro"));
  // Une abrogation ne met rien en vigueur : elle met fin à une rédaction. Dire
  // « rédaction en vigueur le… » pour un article abrogé serait le contraire de
  // ce qui s'est passé.
  const verbe = a.quoi === "ABROGE" ? "abrogé"
              : a.quoi === "CREE" ? "créé"
              // Un article que la loi a écrit pour elle-même : il n'est pas
              // « en vigueur » à la place d'un autre, il est nouveau.
              : a.quoi === "AJOUTE" ? "article de cette loi, en vigueur"
              : "rédaction en vigueur";
  // Sans date, ce n'est pas qu'on l'ignore : la loi renvoie à un décret qui
  // n'est pas paru. Le dire vaut mieux que de se taire.
  const quand = a.effet ? " le " + dateLongue.format(enDate(a.effet))
                        : " à une date non encore fixée";
  f.append(el("p", "fiche-sous", (a.ou || "") + " — " + verbe + quand));
  // Le titre ci-dessus est alors le début du texte, pas un intitulé : le dire,
  // pour qu'on ne le prenne pas pour un nom officiel.
  if (!a.numero) {
    f.append(el("p", "nota",
      "La source ne donne aucun numéro à cet article — c'est le cas des états "
      + "et annexes des lois de finances. Le titre ci-dessus est le début de "
      + "son texte, recopié tel quel."));
  }

  const neuf = a.commun === null;
  if (a.enAttente) {
    f.append(el("p", "nota",
      "La source a publié cet article sans encore en saisir le texte. La "
      + "phrase ci-dessous est la sienne, en attendant : ce n'est pas le texte "
      + "de la loi. Il arrivera dans une prochaine mise à jour du droit "
      + "consolidé."));
  } else if (neuf) {
    f.append(el("p", "nota", a.avant === "manquant"
      ? "La rédaction précédente de cet article n'a pas été retrouvée dans les "
        + "archives lues : le texte ci-dessous est celui en vigueur, sans "
        + "comparaison possible."
      : a.quoi === "AJOUTE"
      ? "Cet article est l'un de ceux que la loi a écrits. Il n'a pas de "
        + "rédaction précédente : il n'existait pas avant elle."
      : "La loi a créé cet article : il n'a pas de rédaction précédente à lui "
        + "superposer."));
  }
  if (!neuf) {
    const bascule = el("div", "bascule-texte");
    const noms = a.quoi === "ABROGE"
      ? [["diff", "Ce qui change"], ["apres", "Dernier texte"], ["avant", "Texte précédent"]]
      : [["diff", "Ce qui change"], ["apres", "Texte en vigueur"], ["avant", "Texte précédent"]];
    for (const [cle, nom] of noms) {
      const b = el("button", null, nom);
      b.setAttribute("aria-pressed", String(MODE_TEXTE === cle));
      b.addEventListener("click", () => {
        MODE_TEXTE = cle;
        dessinerArticle(f, retour, uid, a);
        window.scrollTo(0, 0);
      });
      bascule.append(b);
    }
    f.append(bascule);
  }

  const mode = neuf ? "apres" : MODE_TEXTE;
  if (mode === "diff") f.append(legendeDiff(a.morceaux, "par la loi"));
  f.append(texteCompare(a.morceaux, mode));

  // Les conditions d'entrée en vigueur, quand le texte officiel en porte. Ce
  // n'est pas de l'article, c'est ce que le législateur a écrit à côté.
  if (a.nota) f.append(el("p", "nota", a.nota));

  const source = el("a", "lien-source");
  source.href = a.source;
  source.target = "_blank"; source.rel = "noopener";
  source.append(el("b", null, "Lire l'article sur Légifrance ›"),
                el("span", null, "Le texte officiel, sur le site du service public."));
  f.append(source);
}

/* ------------------------------------------------------------------ *
 * Les versions successives d'un texte
 *
 * Un texte de loi n'est pas figé : il est déposé, puis la commission le
 * réécrit, puis la séance le réécrit encore. L'Assemblée publie chacune de
 * ces versions ; l'écran les montre **superposées**, comme les rédactions
 * d'un article de loi — ce qui a été retiré en rouge barré, ce qui a été
 * ajouté en vert.
 *
 * À côté de chaque article changé, **les amendements adoptés sur cet
 * article** : leur numéro, leur auteur, son groupe. Le rapprochement se fait
 * par le numéro d'article, jamais par le texte — dire quel mot vient de quel
 * amendement demanderait d'interpréter l'instruction de l'amendement, donc de
 * fabriquer du texte de loi. Mesuré le 2026-09-18 : 420 amendements adoptés
 * sur 470 tombent sur un article qui a réellement changé, 2 sur un article
 * resté identique — le rapprochement est presque toujours juste, et souvent
 * incomplet. **Un article sans amendement le dit.**
 * ------------------------------------------------------------------ */

// Ce que le compte d'une version annonce, sous son nom, dans le parcours.
