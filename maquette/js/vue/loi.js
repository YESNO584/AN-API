/* Ce qu'une loi promulguée change au droit : la liste des articles, et la fiche d'un article avec ses trois lectures. */

/* ---------- l'onglet « Articles » ---------- *
 * Ce que la loi change au droit, en entier dans l'onglet. Avant, l'onglet ne
 * portait qu'un lien vers un écran à part : un aller-retour pour une liste
 * qui tient là où on la cherche. L'écran, lui, reste — la carte du fil y mène
 * toujours, et une adresse partagée continue de l'ouvrir.
 *
 * La liste est demandée à l'ouverture de l'onglet, pas à celle de la fiche.
 * Elle **ne porte aucun texte d'article** — c'est la raison d'être de la
 * coupure en deux fichiers côté socle — et le texte d'un article n'arrive que
 * si on ouvre cet article.
 * ------------------------------------------------------------------ */
function blocChangements(uid, t) {
  const b = bloc("Ce que cette loi change", false, true);
  const c = t.change;
  const ajouts = (c && c.ajouts) || 0;

  // Rien à charger : la loi ne touche à aucun article et n'en écrit aucun. Le
  // dire, avec la raison quand la source la porte.
  if (!c || (!c.total && !ajouts)) {
    const raison = POURQUOI_SANS_CHANGEMENT[t.type];
    b.append(el("p", "sans-change", "Ne modifie aucun article de loi existante"
      + (raison ? " — " + raison + "." : ".")));
    return [b, null];
  }
  // Une loi peut n'amender aucun texte d'avant et pourtant écrire du droit :
  // c'est le cas des lois de finances, dont presque toute la matière tient
  // dans leurs propres articles.
  if (!c.total) {
    b.append(el("p", "sans-change",
      "Ne modifie aucun article de loi existante — tout son droit tient dans "
      + "ses propres articles."));
  }

  const attente = el("p", "avertissement", "Chargement de la liste des articles…");
  b.append(attente);
  return [b, () => chargerLesChangements(uid, b, attente)];
}

/* La liste elle-même : les compteurs, les articles groupés par code, les
 * retouches, et ce que la loi ajoute. Écrite une fois et posée à deux
 * endroits — l'onglet « Articles » de la fiche et cet écran, atteint depuis
 * la carte du fil. Deux copies auraient divergé au premier changement.
 * ------------------------------------------------------------------ */
/* Le résumé : combien d'articles modifiés, créés, abrogés. Un compte, pas
   une appréciation. La quatrième tuile ne s'affiche que si la loi a écrit
   ses propres articles — annoncer un zéro pour toutes les autres lois
   ferait chercher un chiffre qui n'a rien à dire. */
function tuilesDuResume(d, ajouts) {
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
  return resume;
}

/* Les articles d'un code que la loi change, repliés ou non. */
function groupeDArticles(uid, groupe, ouvert) {
  const boite = el("details", "code-groupe");
  boite.open = ouvert;
  const titre = el("summary");
  const zone = el("div");
  zone.append(el("b", null, groupe.ou));
  zone.append(el("i", null,
    `${nb.format(groupe.articles.length)} article${groupe.articles.length > 1 ? "s" : ""}`));
  titre.append(zone);
  boite.append(titre);
  for (const a of groupe.articles) boite.append(ligneArticle(uid, a));
  return boite;
}

/* Les articles retouchés sans changement de fond : hors du compte, mais pas
   cachés. Les compter comme modifiés ferait dire à l'application qu'une loi
   a changé quelque chose là où elle n'a rien changé. */
function blocRetouches(uid, retouches) {
  const boite = el("details", "retouches");
  const titre = el("summary");
  titre.append(el("b", null,
    `${nb.format(retouches.length)} article${retouches.length > 1 ? "s" : ""} retouché`
    + `${retouches.length > 1 ? "s" : ""}`));
  titre.append(document.createTextNode(" sans changement de fond — "
    + "seule la ponctuation ou les espaces ont bougé."));
  boite.append(titre);
  for (const a of retouches) boite.append(ligneArticle(uid, a, true));
  return boite;
}

/* Ce que la loi **ajoute** : ses propres articles. Une liste à part, parce
   qu'ils n'ont pas d'avant — il n'y a rien à superposer, seulement un texte
   à lire. Les mêler aux articles changés obligerait à afficher une « part
   de texte changé » qui ne veut rien dire pour un article neuf. */
function blocAjouts(uid, d, ajouts) {
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
  return boite;
}

function contenuDesChangements(uid, d) {
  const f = [];
  const ajouts = d.articlesAjoutes || [];

  f.push(tuilesDuResume(d, ajouts));

  for (const groupe of d.groupes || []) {
    f.push(groupeDArticles(uid, groupe, d.groupes.length <= 3));
  }

  const retouches = d.articlesRetouches || [];
  if (retouches.length) f.push(blocRetouches(uid, retouches));

  if (ajouts.length) f.push(blocAjouts(uid, d, ajouts));

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
    // `saut` : le morceau ouvre un alinéa (textes de loi en navette, voir
    // `textes.avec_les_alineas`) — la feuille garde les sauts de ligne.
    if (!m.colle && !debut) corps.append(document.createTextNode(m.saut ? "\n" : " "));
    const classe = mode === "diff" && m.forme ? "forme" : null;
    corps.append(el(balise, classe, m.texte));
    debut = false;
  }
  return corps;
}

/* Ce que l'article est devenu, et quand. */
function sousTitreDArticle(a) {
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
  return el("p", "fiche-sous", (a.ou || "") + " — " + verbe + quand);
}

/* Ce qu'il faut dire d'un article qui n'a pas d'avant — ou dont la source
   n'a pas encore saisi le texte. Rien, sinon. */
function notaDuNeuf(a, neuf) {
  if (a.enAttente) {
    return el("p", "nota",
      "La source a publié cet article sans encore en saisir le texte. La "
      + "phrase ci-dessous est la sienne, en attendant : ce n'est pas le texte "
      + "de la loi. Il arrivera dans une prochaine mise à jour du droit "
      + "consolidé.");
  } else if (neuf) {
    return el("p", "nota", a.avant === "manquant"
      ? "La rédaction précédente de cet article n'a pas été retrouvée dans les "
        + "archives lues : le texte ci-dessous est celui en vigueur, sans "
        + "comparaison possible."
      : a.quoi === "AJOUTE"
      ? "Cet article est l'un de ceux que la loi a écrits. Il n'a pas de "
        + "rédaction précédente : il n'existait pas avant elle."
      : "La loi a créé cet article : il n'a pas de rédaction précédente à lui "
        + "superposer.");
  }
  return null;
}

/* Les trois façons de lire l'article : ce qui change, le texte en vigueur,
   le texte précédent. */
function basculeDuMode(f, retour, uid, a) {
  const bascule = el("div", "bascule-texte");
  const noms = a.quoi === "ABROGE"
    ? [["diff", "Ce qui change"], ["apres", "Dernier texte"], ["avant", "Texte précédent"]]
    : [["diff", "Ce qui change"], ["apres", "Texte en vigueur"], ["avant", "Texte précédent"]];
  for (const [cle, nom] of noms) {
    const b = el("button", null, nom);
    b.setAttribute("aria-pressed", String(MODE_TEXTE === cle));
    b.addEventListener("click", () => choisirLeMode(cle, f, retour, uid, a));
    bascule.append(b);
  }
  return bascule;
}

function dessinerArticle(f, retour, uid, a) {
  f.textContent = "";
  f.append(retour);
  f.append(el("h2", "fiche-titre", a.numero ? "Article " + a.numero
                                            : a.intitule || "Article sans numéro"));
  f.append(sousTitreDArticle(a));
  // Le titre ci-dessus est alors le début du texte, pas un intitulé : le dire,
  // pour qu'on ne le prenne pas pour un nom officiel.
  if (!a.numero) {
    f.append(el("p", "nota",
      "La source ne donne aucun numéro à cet article — c'est le cas des états "
      + "et annexes des lois de finances. Le titre ci-dessus est le début de "
      + "son texte, recopié tel quel."));
  }

  const neuf = a.commun === null;
  const nota = notaDuNeuf(a, neuf);
  if (nota) f.append(nota);
  if (!neuf) f.append(basculeDuMode(f, retour, uid, a));

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
