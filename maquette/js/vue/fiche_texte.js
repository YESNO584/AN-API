/* L'onglet « Texte » : le texte déposé comparé à la version à jour, article par article, et les trois vues qu'on en propose. */

// L'icône de l'origine : une étincelle pour l'IA, une silhouette pour une
// personne. Dessinée ici plutôt qu'écrite en emoji, dont le rendu change d'un
// téléphone à l'autre.

function articlesDeLaVersion(d, mode, uid) {
  const zone = el("div");
  const tous = (d.articles || []).flatMap((a) => a.morceaux || []);
  if (mode === "diff" && tous.length) {
    // Un fichier qui porte des étapes est la comparaison du parcours entier :
    // dire « par la commission » y serait faux, puisque la commission et la
    // séance y ont chacune mis la main.
    const par = (d.etapes || []).length ? "depuis le dépôt du texte"
              : /BTC\d+$/.test(d.ref) ? "par la commission"
              : /BTA\d+$/.test(d.ref) ? "en séance"
              : "depuis la version précédente";
    zone.append(legendeDiff(tous, par));
  }
  for (const a of d.articles || []) {
    const tete = el("div", "art-titre");
    tete.append(el("h3", null, a.titre));
    const mots = { modifie: "Modifié", nouveau: "Nouveau", retire: "Retiré",
                   identique: "Inchangé", initial: null };
    if (mode === "diff" && mots[a.quoi]) {
      tete.append(el("span", "quoi " + a.quoi, mots[a.quoi]));
    }
    // Un article sans texte n'est pas un bogue d'affichage : la source dit
    // « (Supprimé) » et n'en imprime plus rien. Sans cette mention, le titre
    // reste seul au-dessus d'un cadre vide, ce qui se lit comme une panne.
    if (a.etat && !(a.texte || "").trim()) {
      tete.append(el("span", "quoi", "La source dit : " + a.etat));
    }
    zone.append(tete);
    // Les amendements adoptés sur cet article, dans la seule vue qui montre
    // ce qui a changé : les deux autres montrent un texte, pas une
    // transformation, et une liste d'amendements n'y voudrait rien dire.
    if (mode === "diff" && A_CHANGE.has(a.quoi)) {
      zone.append(carteAmendementsDeLArticle(a.amendements || [], uid));
    }
    zone.append(texteCompare(a.morceaux, mode, a.texte));
  }
  if (mode === "diff") {
    zone.append(el("p", "avertissement",
      "Les amendements sont rapprochés par le numéro d'article : la page dit "
      + "lesquels ont été adoptés sur cet article, jamais quel mot vient de "
      + "quel amendement — il faudrait pour cela interpréter l'instruction de "
      + "l'amendement, et le texte affiché ne serait plus celui de la source."
      + ((d.etapes || []).length
         ? " Ici le rapprochement porte sur tout le parcours, ce qui suppose "
           + "qu'un numéro d'article désigne le même article du dépôt à "
           + "aujourd'hui. Chaque amendement dit donc où il a été adopté."
         : "")));
  }
  return zone;
}

/* Les vues qu'un texte propose : la version déposée, et — dès qu'il en a deux —
   ce qui a changé depuis le dépôt et la version à jour. Chaque vue dit quelle
   version elle montre et de quand : sans cela, trois boutons courts
   laisseraient croire qu'on lit toujours le même document. */
function vuesDuTexte(versions) {
  const initiale = versions[0];
  const derniere = versions[versions.length - 1];
  const quand = (v) => dateLongue.format(enDate(v.date));

  // Chaque vue dit quelle version elle montre et de quand : sans cela, trois
  // boutons courts laisseraient croire qu'on lit toujours le même document.
  const vues = [
    { cle: "depose", bouton: "Version déposée", fichier: initiale.ref,
      mode: "apres",
      sous: initiale.nom + ", " + quand(initiale)
            + " — le texte tel qu'il a été déposé" },
  ];
  // Une seule version : il n'y a ni « dernière » ni comparaison à montrer, et
  // donc pas de choix à proposer.
  if (versions.length > 1) {
    vues.push(
      // **La comparaison va du texte déposé à la version à jour**, et non
      // d'une étape à la suivante. Les trois boutons promettent cela, et
      // c'est ce qu'on veut savoir : ce que le texte déposé est devenu. Une
      // seule étape aurait montré, pour une loi arrivée au bout, la
      // commission mixte paritaire — 4 amendements sur la loi Ripost, quand
      // le texte en a vu 245 adoptés depuis son dépôt.
      //
      // Le socle la publie dans son propre fichier, dès qu'un texte a deux
      // versions ; ce qu'une étape précise a changé reste dans le fichier de
      // sa version, et s'ouvre depuis le parcours.
      { cle: "change", bouton: "Modifications", fichier: "depuis-le-depot",
        mode: "diff",
        sous: "Du " + initiale.nom.toLowerCase() + " du " + quand(initiale)
              + " au " + derniere.nom.toLowerCase() + " du " + quand(derniere)
              + " — tout ce qui a changé en chemin" },
      // Espace insécable : sans elle, le bouton casse en « Version à / jour ».
      // Même fichier que « Modifications », et pour une raison de fond : le
      // dernier document **ne réimprime pas** les articles déjà accordés, il
      // écrit « (Conforme) ». Le texte à jour de ces articles est celui de la
      // version qui les imprime, et c'est le socle qui va le chercher.
      { cle: "ajour", bouton: "Version \u00e0\u00a0jour",
        fichier: "depuis-le-depot", mode: "apres",
        sous: derniere.nom + ", " + quand(derniere)
              + " — le texte tel qu'il se lit aujourd'hui, sans les différences" });
  }
  return vues;
}

/* Les mêmes trois boutons côte à côte que pour un article de loi : un seul
   geste à apprendre pour choisir ce qu'on regarde, partout dans la fiche. */
function basculeDesVues(vues, boutons, montrer) {
  const bascule = el("div", "bascule-texte");
  for (const vue of vues) {
    const bt = el("button", null, vue.bouton);
    bt.type = "button";
    bt.dataset.cle = vue.cle;
    bt.setAttribute("aria-pressed", String(vue === vues[0]));
    bt.addEventListener("click", () => montrer(vue));
    bascule.append(bt);
    boutons.push(bt);
  }
  return bascule;
}

function blocTexte(uid, versions, plat) {
  const b = bloc("Le texte", false, plat);
  if (!versions.length) {
    b.append(el("p", "avertissement",
      "Le texte de ce projet ou de cette proposition n'est pas publié ici. "
      + "Le socle lit les documents de l'Assemblée nationale ; un texte déposé "
      + "au Sénat a ses versions sur le site du Sénat, qui ne les sert pas de "
      + "la même façon. Le parcours donne le numéro de chaque document."));
    return [b, null];
  }
  const vues = vuesDuTexte(versions);

  const o = { uid, sous: el("p", "sous-texte"), zone: el("div"), boutons: [] };
  const montrer = (vue) => montrerLaVue(o, vue);

  if (vues.length > 1) {
    // Les mêmes trois boutons côte à côte que pour un article de loi : un seul
    // geste à apprendre pour choisir ce qu'on regarde, partout dans la fiche.
    b.append(basculeDesVues(vues, o.boutons, montrer));
  } else {
    b.append(el("p", "avertissement",
      "Une seule version de ce texte est publiée : il n'y a donc rien à "
      + "comparer, et le texte déposé est aussi le texte à jour."));
  }
  b.append(o.sous, o.zone);
  // La première vue est demandée à l'ouverture de l'onglet, pas à celle de la
  // fiche : une version pèse jusqu'à 2,8 Mo, et l'onglet n'est pas toujours
  // celui qu'on ouvre.
  return [b, () => montrer(vues[0])];
}
