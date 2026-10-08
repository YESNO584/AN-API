/* Une carte du fil — texte, travail — et ses étiquettes : groupe, vote, loi, repère des amendements disputés, ce que la loi change. */

/* ---------- une carte ---------- */
/* Le groupe de l'auteur, en couleur. Un point coloré plutôt qu'une pastille
   pleine : la couleur d'un groupe n'est qu'une convention d'affichage — voir
   `groupes.json` — et la donner en fond la ferait passer pour une donnée. */

function etiquetteGroupe(t) {
  const b = el("button", "etiq grp");
  const point = el("i");
  point.style.background = t.auteur_couleur;
  b.append(point, document.createTextNode(t.auteur_sigle));
  b.addEventListener("click", (ev) => {
    ev.preventDefault();
    ev.stopPropagation();
    expliquer("Le groupe politique de l'auteur",
      "Le groupe auquel appartient le parlementaire qui a déposé le texte. Les " +
      "couleurs sont une convention d'affichage : l'open data n'en publie aucune. " +
      "Un texte déposé par le Gouvernement ou par un sénateur n'a pas de groupe " +
      "à l'Assemblée, et n'affiche donc rien ici. C'est le groupe du " +
      "parlementaire aujourd'hui : s'il en a changé depuis le dépôt, la source " +
      "ne garde pas celui d'alors.",
      t.auteur_groupe || t.auteur_sigle);
  });
  return b;
}

/* Le repère du texte entier : il dit qu'au moins un amendement y a été adopté
   de justesse après un long échange, et il mène à la liste de ces
   amendements-là. Un lien, et non un bouton d'explication : l'explication est
   sur l'écran qu'il ouvre, au-dessus de la liste qu'elle décrit.

   **Son absence ne dit rien**, et c'est pour ça qu'il n'a pas de contraire à
   l'écran : 97 % des amendements adoptés le sont à main levée, sans qu'aucun
   décompte de voix existe. */
function repereDisputes(t) {
  const disputes = amendementsDisputes(t);
  if (!disputes.length) return null;
  const a = el("a", "etiq dispute");
  a.href = "#/disputes/" + t.uid;
  a.append(el("b", null, "!"), document.createTextNode(
    `${nb.format(disputes.length)} amendement${disputes.length > 1 ? "s" : ""} `
    + `adopté${disputes.length > 1 ? "s" : ""} de justesse`));
  return a;
}

function bandeauVote(t) {
  const b = el("button", "vote");
  const e = t.voteEnsemble;

  if (e) {
    b.classList.add(e.sort === "adopté" ? "adopte" : "rejete");
    b.append(el("span", "verdict", e.sort === "adopté" ? "Adopté" : "Rejeté"));
    b.append(el("span", "chiffres",
      `${nb.format(e.pour)} pour · ${nb.format(e.contre)} contre · ${nb.format(e.abstentions)} abst.`));
    b.append(el("span", "quand", dateCourte.format(enDate(e.date))));
  } else {
    b.classList.add("partiel");
    b.append(el("span", "verdict", nb.format(t.votes) +
      (t.votes > 1 ? " votes enregistrés" : " vote enregistré")));
    b.append(el("span", "chiffres", "sur des amendements ou des articles"));
  }
  b.append(el("span", "loupe", "ⓘ"));
  b.addEventListener("click", () => detailVotes(t));
  return b;
}

function legendeDesVotes() {
  const legende = el("div", "legende");
  for (const [cle, mot] of [["pour", "pour"], ["contre", "contre"],
                            ["abstention", "abstention"]]) {
    const item = el("span", null);
    item.append(el("i", cle));
    item.append(document.createTextNode(mot));
    legende.append(item);
  }
  return legende;
}

/* Un groupe au scrutin : sa pastille, son sigle, sa barre pour / contre /
   abstention, et son décompte. */
function ligneDuGroupeAuVote(g) {
  const total = (g.pour || 0) + (g.contre || 0) + (g.abstentions || 0);
  const ligne = el("div", "groupe");
  const connu = GROUPES.get(g.sigle);
  const teinte = g.couleur || connu?.couleur;
  const pastille = el("i", "teinte");
  if (teinte) pastille.style.background = teinte;
  ligne.append(pastille);
  const sigle = el("button", "sigle", g.sigle);
  sigle.addEventListener("click", () => expliquer(
    connu?.nom || g.nom || g.sigle,
    connu || g.nom
      ? "Un groupe politique de l'Assemblée nationale. Sa place dans la liste " +
        "est celle qu'il occupe dans l'hémicycle, calculée sur les numéros de " +
        "siège de ses députés. Sa couleur, elle, est une convention " +
        "d'affichage : l'open data n'en publie aucune."
      : "L'Assemblée ne nomme plus ce groupe — le plus souvent parce qu'il " +
        "n'existe plus. Seuls les groupes actuels figurent dans ses données.",
    `${g.pour} pour · ${g.contre} contre · ${g.abstentions} abstentions`));
  ligne.append(sigle);
  const barre = el("span", "barre");
  for (const [cle, n] of [["pour", g.pour], ["contre", g.contre],
                          ["abstention", g.abstentions]]) {
    if (!n) continue;
    const part = el("i", cle);
    part.style.flexGrow = String(n);
    part.title = `${n} ${cle}`;
    barre.append(part);
  }
  if (!total) barre.append(el("i", "vide"));
  ligne.append(barre);
  ligne.append(el("span", "detail",
    total ? `${g.pour}/${g.contre}/${g.abstentions}` : "n'a pas voté"));
  return ligne;
}

/* Les étiquettes de la carte : la chambre, la nature, le groupe de l'auteur,
   le sujet, la lecture, le dernier acte, la date — et ce qui est prévu. */
function etiquettesDeLaCarte(t) {
  const l = el("div", "lignes");
  const ch = t.chambre || null;
  l.append(etiquette("chambre-" + (ch || "aucune"), CHAMBRES[ch][0], CHAMBRES[ch]));
  l.append(etiquette("", typeCourt(t.type), TYPES[t.type] || [typeCourt(t.type), ""]));
  if (t.auteur_sigle) l.append(etiquetteGroupe(t));
  // Le sujet, classé par le Sénat — le seul des deux à en publier un. Un seul
  // s'affiche : un texte en porte deux en médiane, et la carte ne doit pas
  // devenir une liste de mots-clés.
  for (const sujet of (t.themes || []).slice(0, 1)) {
    l.append(etiquette("sujet", sujet, EXPLICATIONS.theme,
                       (t.themes || []).join(" · ")));
  }
  if (t.lecture) l.append(etiquette("", t.lecture, EXPLICATIONS.lecture));
  if (t.dernier_acte) l.append(etiquette("", t.dernier_acte, EXPLICATIONS.acte));
  if (t.conclusion) l.append(etiquette("", t.conclusion, EXPLICATIONS.conclusion));

  const age = jours(t.date_dernier_mouvement);
  const quand = dateCourte.format(enDate(t.date_dernier_mouvement));
  if (age > 365) {
    const ans = Math.floor(age / 365);
    l.append(etiquette("dormant", `à l'arrêt depuis ${ans} an${ans > 1 ? "s" : ""}`,
                       EXPLICATIONS.dormant, quand));
  } else {
    l.append(etiquette("", quand, EXPLICATIONS.date));
  }
  if (t.prochaine_date) {
    l.append(etiquette("prochaine",
      "prévu le " + dateCourte.format(enDate(t.prochaine_date)),
      EXPLICATIONS.prochaine, t.prochaine_quoi + ", le " + dateLongue.format(enDate(t.prochaine_date))));
  }
  // Ce texte porte-t-il un amendement adopté de justesse après un long
  // échange ? La question se pose devant la carte, pas seulement une fois le
  // texte ouvert — et le repère y mène directement.
  const dispute = repereDisputes(t);
  if (dispute) l.append(dispute);
  return l;
}

/* Comment le texte a fini, quand il a fini : l'issue d'un texte arrêté, ou le
   numéro de la loi promulguée. */
function lignesDIssue(t) {
  const lignes = [];
  if (t.etape === ARRETE && ISSUES[t.statut]) {
    const issue = el("div", "lignes");
    issue.append(etiquette("arrete", ISSUES[t.statut][0], ISSUES[t.statut],
      t.etat_senat && t.statut !== "rejete" ? "le Sénat écrit « " + t.etat_senat + " »" : null));
    lignes.push(issue);
  }

  if (t.etape === PROMULGUEE && t.loiNumero) {
    const loi = el("div", "lignes");
    loi.append(etiquette("promulguee", "loi n° " + t.loiNumero,
      ["Le numéro de la loi",
       "Une fois promulguée, la loi reçoit un numéro officiel et une date. " +
       "C'est sous ce numéro qu'on la retrouve au Journal officiel et qu'on la cite."],
      t.loiDate ? "publiée le " + dateLongue.format(enDate(t.loiDate)) : null));
    if (t.loiUrlJO) {
      const jo = el("a", "etiq lien", "texte officiel");
      jo.href = t.loiUrlJO; jo.target = "_blank"; jo.rel = "noopener";
      loi.append(jo);
    }
    lignes.push(loi);
  }
  return lignes;
}

function carte(t) {
  const c = el("article", "carte");

  const h = el("h2");
  const a = el("a", null, t.titre);
  a.href = "#/texte/" + t.uid;
  h.append(a);
  c.append(h);

  c.append(etiquettesDeLaCarte(t));

  // Dans l'onglet « Sénat », la carte doit dire où le texte en est **là-bas**.
  // Les étiquettes du dessus décrivent le parcours vu de l'Assemblée : sans
  // cette ligne, la colonne dirait « Décidé » et la carte parlerait d'autre
  // chose.
  if (ONGLET === "senat" && t.senat) c.append(ligneSenat(t.senat));

  c.append(...lignesDIssue(t));

  if (t.voteEnsemble || t.votes) c.append(bandeauVote(t));

  // Ce que la loi change au droit : quand elle s'applique, et combien
  // d'articles elle touche. Sur la carte, parce que c'est la question qu'on
  // se pose en premier devant une loi promulguée.
  if (t.etape === PROMULGUEE) c.append(...ceQueLaLoiChange(t));

  // Pas de frise ici : tous les textes d'une colonne sont à la même étape.
  // Elle est en bas de l'écran, une bonne fois — voir `frise-bas`.
  return c;
}

/* Ce que le Sénat a fait du texte, et quand. **Sa lecture s'affiche ici et
   non en colonne** : première, deuxième et nouvelle lecture partagent les
   mêmes étapes, et en faire quinze colonnes presque toutes vides n'aurait
   rien dit de plus. La conclusion est le mot de la source, repris tel quel. */
function ligneSenat(e) {
  const l = el("div", "lignes senat-ligne");
  // **L'étape n'est pas répétée ici** : la colonne la porte déjà, et toutes
  // les cartes d'une colonne sont à la même. Ce qui mérite la place, c'est ce
  // qui change d'une carte à l'autre.
  if (e.lecture) {
    l.append(etiquette("chambre-senat", "Sénat · " + e.lecture,
                       EXPLICATIONS.lectureSenat, e.libelle || null));
  }
  if (e.conclusion) {
    l.append(etiquette("", e.conclusion, EXPLICATIONS.conclusionSenat,
                       "Le mot du Sénat, repris tel quel"));
  }
  if (e.date) {
    l.append(etiquette("", "au Sénat le " + dateCourte.format(enDate(e.date)),
                       EXPLICATIONS.dateSenat));
  }
  return l;
}

// « l'article » ou « les 12 articles ». L'accord se fait ici, une fois : les
// libellés écrivaient « les 1 article », qui se lit comme une faute.
function combienDArticles(n) {
  return n === 1 ? "l'article" : `les ${nb.format(n)} articles`;
}

// Le bouton qui mène au détail. Son libellé dit les deux choses séparément :
// ce que la loi change dans le droit d'avant, et ce qu'elle y ajoute. Les
// additionner ferait un chiffre que rien à l'écran ne recoupe.
function boutonChange(t, change, ajouts) {
  const libelle = change && ajouts
    ? `Voir ${combienDArticles(change)} qu'elle change et `
      + `${combienDArticles(ajouts)} qu'elle ajoute ›`
    : change ? `Voir ${combienDArticles(change)} que cette loi change ›`
    : `Voir ${combienDArticles(ajouts)} que cette loi ajoute ›`;
  const bouton = el("button", "lien-change", libelle);
  bouton.addEventListener("click", (e) => {
    e.stopPropagation();
    location.hash = "#/change/" + t.uid;
  });
  return bouton;
}

// Quand la loi s'applique. Séparé du reste parce que les deux morceaux n'ont
// pas la même place sur la fiche : celui-ci est l'état du texte, et il se lit
// sous son titre ; le détail des articles vit dans son onglet.
function laVigueur(t) {
  if (ETAT.droitConsolideIndisponible) return null;
  const c = t.change;
  // Une loi qui ne modifie aucun article d'une loi d'avant n'a pas de date
  // d'entrée en vigueur à montrer : la source ne les publie que là.
  if (!c || !c.total) return null;

  const dates = c.dates || [];
  const aujourdhui = new Date().toISOString().slice(0, 10);
  const aVenir = dates.filter((d) => d.date > aujourdhui);
  const dates_connues = dates.reduce((n, d) => n + d.articles, 0);
  const sansDate = c.total - dates_connues;
  const boite = el("div", "vigueur" + (aVenir.length ? " attente" : ""));
  const zone = el("div");
  if (!aVenir.length) {
    const derniere = dates.length ? dates[dates.length - 1].date : null;
    zone.append(el("b", null, derniere
      ? "S'applique depuis le " + dateLongue.format(enDate(derniere))
      : "S'applique"));
  } else if (aVenir.length === dates.length) {
    zone.append(el("b", null, "Ne s'applique pas encore"));
    zone.append(document.createTextNode(
      "Entrée en vigueur le " + dateLongue.format(enDate(aVenir[0].date)) + "."));
  } else {
    const restants = aVenir.reduce((n, d) => n + d.articles, 0);
    zone.append(el("b", null, "Ne s'applique pas encore en entier"));
    zone.append(document.createTextNode(
      `${nb.format(restants)} article${restants > 1 ? "s" : ""} sur `
      + `${nb.format(c.total)} entre${restants > 1 ? "nt" : ""} en vigueur le `
      + dateLongue.format(enDate(aVenir[0].date)) + "."));
  }
  if (sansDate > 0) {
    zone.append(el("div", null,
      `${nb.format(sansDate)} article${sansDate > 1 ? "s" : ""} `
      + `attend${sansDate > 1 ? "ent" : ""} un décret pour s'appliquer.`));
  }
  boite.append(zone);
  boite.addEventListener("click", () => expliquer(
    EXPLICATIONS.vigueur[0], EXPLICATIONS.vigueur[1],
    dates.map((d) => `${nb.format(d.articles)} article${d.articles > 1 ? "s" : ""} `
                     + `le ${dateLongue.format(enDate(d.date))}`).join("\n")));
  return boite;
}

// Ce que la loi change au droit : la phrase quand elle ne change rien, et le
// bouton vers le détail. C'est le contenu de l'onglet « Articles » de la fiche.
function leChangement(t) {
  if (ETAT.droitConsolideIndisponible) return [];
  const c = t.change;
  const ajouts = (c && c.ajouts) || 0;
  if (!c || (!c.total && !ajouts)) {
    const raison = POURQUOI_SANS_CHANGEMENT[t.type];
    return [el("p", "sans-change",
      "Ne modifie aucun article de loi existante"
      + (raison ? " — " + raison + "." : "."))];
  }
  // Une loi peut n'amender aucun texte d'avant et pourtant écrire du droit :
  // c'est le cas des lois de finances, dont presque toute la matière tient
  // dans leurs propres articles. Le dire, plutôt que d'afficher « ne modifie
  // rien » et s'arrêter là.
  if (!c.total) {
    return [el("p", "sans-change",
      "Ne modifie aucun article de loi existante — tout son droit tient dans "
      + "ses propres articles."),
      boutonChange(t, 0, ajouts)];
  }
  return [boutonChange(t, c.total, ajouts)];
}

// Sur la carte du fil, les deux morceaux restent l'un sous l'autre : une carte
// n'a ni titre à part ni onglets.
function ceQueLaLoiChange(t) {
  const v = laVigueur(t);
  return (v ? [v] : []).concat(leChangement(t));
}

/* ---------- la carte d'un travail de l'Assemblée ---------- *
 * Plus sobre que celle d'un texte : ces dossiers n'ont ni parcours, ni vote
 * sur l'ensemble, ni promulgation. Ils ont un titre, une date et une issue.
 * ------------------------------------------------------------------ */
function carteTravail(t) {
  const c = el("article", "carte");
  const h = el("h2");
  const lien = t.url_an || t.url_senat;
  if (lien) {
    const a = el("a", null, t.titre);
    a.href = lien; a.target = "_blank"; a.rel = "noopener";
    h.append(a);
  } else {
    h.append(document.createTextNode(t.titre));
  }
  c.append(h);

  const l = el("div", "lignes");
  const ch = t.chambre || null;
  l.append(etiquette("chambre-" + (ch || "aucune"), CHAMBRES[ch][0], CHAMBRES[ch]));
  if (t.lecture) l.append(etiquette("", t.lecture, EXPLICATIONS.lecture));
  if (t.dernier_acte) l.append(etiquette("", t.dernier_acte, EXPLICATIONS.acte));
  if (t.conclusion) l.append(etiquette("", t.conclusion, EXPLICATIONS.conclusion));
  if (t.date_dernier_mouvement) {
    l.append(etiquette("", dateCourte.format(enDate(t.date_dernier_mouvement)),
                       EXPLICATIONS.date));
  }
  c.append(l);
  return c;
}

/* La carte d'un élément, selon l'onglet : un travail n'a pas la même carte
   qu'un texte. */
function carteDe(t) {
  return ONGLET === "travaux" ? carteTravail(t) : carte(t);
}
