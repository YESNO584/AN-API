/* Ouvrir une fiche et ce qui s'y charge à la demande : les rubriques, les amendements, les paroles, une vue du texte, le détail d'un vote, un amendement, une version, les amendements disputés. */

async function ouvrirFiche(uid) {
  const [f, retour] = preparerLaFiche();

  let d;
  try {
    d = await lire(`textes/${uid}.json`, true);
  } catch (e) {
    f.append(el("div", "vide", "Fiche indisponible : " + e.message));
    return;
  }
  f.textContent = "";
  f.append(retour);

  const loi = laLoiDeLaFiche(uid, d);
  if (loi) {
    const vigueur = laVigueur(loi);
    if (vigueur) f.append(vigueur);
  }

  f.append(el("h2", "fiche-titre", d.titre));
  f.append(etiquettesDeLaFiche(uid, d));

  // La description du texte, avant les sources. **C'est la seule exception à
  // la règle « rien n'est écrit par une IA »**, décidée pour cette rubrique et
  // pour elle seule : le reste de la fiche est recopié de la source ou calculé.
  // Elle ne s'affiche que si le socle en publie une — pas de cadre vide.
  if (d.description && d.description.accroche) f.append(blocDescription(d.description));

  const sources = sourcesDeLaFiche(d);
  if (sources) f.append(sources);

  if (d.auteur) f.append(personne(d.auteur, "Auteur du texte"));
  if (d.cosignatairesTotal) f.append(blocCosignataires(d));

  f.append(...ongletsDeFiche(await rubriquesDeLaFiche(uid, d, loi)));
}

/* Les rubriques de fond, en onglets. Chacune garde son titre exact, avec
   ses comptes : l'onglet dit laquelle on regarde, le titre dit ce qu'elle
   contient. */
async function rubriquesDeLaFiche(uid, d, loi) {
  const rubriques = [];

  // Le vote qui décide : celui sur l'ensemble du texte, et il ouvre la fiche.
  // Le plus récent, car un texte peut être voté dans les deux chambres. Peu de
  // textes en ont un — 71 sur 1 990 — et ceux-là commencent donc par leurs
  // articles ou leur parcours, sans onglet vide.
  const finaux = (d.votes || []).filter((v) => v.portee === "ensemble");
  if (finaux.length) {
    rubriques.push(["Vote", blocVote(finaux.reduce((a, b) => (a.date >= b.date ? a : b)))]);
  }

  // Ce que la loi change au droit, en entier : la liste des articles s'affiche
  // ici même, et se demande à l'ouverture de l'onglet.
  if (loi) rubriques.push(["Articles", ...blocChangements(uid, loi)]);

  // Le texte lui-même, juste après le vote — sauf pour une loi promulguée, où
  // il passe **après les débats, juste avant le parcours** : ce qui compte
  // alors est ce que la loi change au droit, pas le brouillon qu'elle était.
  const versions = d.versions || [];
  const ongletTexte = ["Texte", ...blocTexte(uid, versions, true)];
  if (d.statut !== "promulgue") rubriques.push(ongletTexte);

  const debats = await rubriqueDebats(uid, d);
  if (debats) rubriques.push(debats);

  // Pour une loi promulguée, l'onglet « Texte » se pose ici, juste avant le
  // parcours.
  if (d.statut === "promulgue") rubriques.push(ongletTexte);

  rubriques.push(rubriqueParcours(uid, d));

  const amendements = await rubriqueAmendements(uid);
  if (amendements) rubriques.push(amendements);
  return rubriques;
}

/* Ce qui a été dit en séance. Juste après les articles, et juste après le
   vote qui le précède à l'écran : c'est l'argumentaire du texte entier, pas
   le détail d'une étape. */
async function rubriqueDebats(uid, d) {
  const nbParoles = (TEXTES.find((t) => t.uid === uid) || {}).paroles || 0;
  if (nbParoles) return ["Débats", await blocParoles(uid, nbParoles, true, d.resumeDebats)];
  if (!ETAT.debatsIndisponibles) return null;
  // Ne pas laisser croire que personne n'a parlé du texte alors que c'est
  // la source qui a manqué.
  const b = bloc("Ce que les groupes en ont dit", false, true);
  b.append(el("p", "avertissement",
    "Les comptes rendus de séance n'ont pas pu être récupérés ce matin : leur "
    + "archive de 55,8 Mo n'est pas arrivée entière. Le reste de la fiche est "
    + "à jour. La récupération est retentée chaque matin."));
  return ["Débats", b];
}

async function rubriqueAmendements(uid) {
  const nbAmdt = (TEXTES.find((t) => t.uid === uid) || {}).amendements || 0;
  if (nbAmdt) return ["Amendements", await blocAmendements(uid, nbAmdt, true)];
  if (!ETAT.amendementsIndisponibles) return null;
  // Ne pas laisser croire qu'un texte n'a pas d'amendements alors que
  // c'est la source qui a manqué. L'archive pèse 297 Mo et n'arrive pas
  // toujours ; le reste des données, lui, est à jour.
  const b = bloc("Amendements", false, true);
  b.append(el("p", "avertissement",
    "Les amendements n'ont pas pu être récupérés ce matin : leur archive de "
    + "297 Mo n'est pas arrivée entière. Le reste de la fiche est à jour. "
    + "La récupération est retentée chaque matin."));
  return ["Amendements", b];
}

async function blocAmendements(uid, total, plat) {
  const b = bloc(`Amendements — ${nb.format(total)}`, false, plat);
  const veille = avisDeVeille(ETAT.amendementsVusLe, "Ces amendements", "297 Mo");
  if (veille) b.append(veille);
  b.append(el("p", "avertissement",
    "Un amendement n'est pas une version modifiée du texte : c'est une instruction, " +
    "reproduite ici mot pour mot. Le texte original des articles n'est pas publié, " +
    "donc rien n'est reconstitué. En vert, ce que l'amendement ajoute ; en rouge " +
    "barré, ce qu'il retire ou remplace — d'après sa propre formulation."));
  const bouton = el("button", "charger", `Charger les amendements`);
  b.append(bouton);
  bouton.addEventListener("click", async () => {
    bouton.textContent = "Chargement…";
    try {
      const d = await lire(`amendements/${uid}.json`, true);
      bouton.remove();
      if (d.publies < d.total) {
        b.append(el("p", "avertissement",
          `${nb.format(d.publies)} amendements affichés sur ${nb.format(d.total)}. ` +
          `Les amendements adoptés viennent en premier.`));
      }
      for (const a of d.amendements) b.append(carteAmendement(a));
    } catch (e) {
      bouton.textContent = "Amendements indisponibles : " + e.message;
    }
  });
  return b;
}

async function blocParoles(uid, total, plat, resume) {
  const b = bloc(`Ce que les groupes en ont dit — ${nb.format(total)} `
                 + `prise${total > 1 ? "s" : ""} de parole`, false, plat);
  // Le résumé d'abord, les paroles entières ensuite : l'un ne remplace pas
  // l'autre, et l'ordre dit lequel fait foi.
  if (resume) b.append(blocResumeDebats(resume));
  const veille = avisDeVeille(ETAT.debatsVusLe,
                              "Ces prises de parole", "55,8 Mo");
  if (veille) b.append(veille);
  b.append(el("p", "avertissement",
    "Les prises de parole en séance, recopiées du compte rendu de l'Assemblée, " +
    "mot pour mot. Elles viennent de la discussion générale et des explications " +
    "de vote — les moments où l'Assemblée donne la parole à un orateur par " +
    "groupe sur le texte entier. Rien n'est résumé, et rien ne dit ici comment " +
    "le groupe a finalement voté : le vote est plus haut, la parole est ici."));
  const bouton = el("button", "charger", "Charger les prises de parole");
  b.append(bouton);
  bouton.addEventListener("click", async () => {
    bouton.textContent = "Chargement…";
    try {
      const d = await lire(`paroles/${uid}.json`, true);
      bouton.remove();
      if (d.groupes.length) {
        const chips = el("div", "chips");
        for (const g of d.groupes) {
          const bt = el("button", null);
          const teinte = el("i");
          teinte.style.background = g.couleur;
          bt.append(teinte);
          bt.append(document.createTextNode(`${g.sigle} · ${g.paroles}`));
          bt.setAttribute("aria-pressed", "false");
          bt.addEventListener("click", () => {
            const actif = bt.getAttribute("aria-pressed") === "true";
            for (const x of chips.children) x.setAttribute("aria-pressed", "false");
            bt.setAttribute("aria-pressed", actif ? "false" : "true");
            for (const carte of b.querySelectorAll(".parole")) {
              carte.hidden = !actif && carte.dataset.sigle !== g.sigle;
            }
          });
          chips.append(bt);
        }
        b.append(chips);
      }
      for (const p of d.paroles) {
        const carte = carteParole(p);
        if (p.sigle) carte.dataset.sigle = p.sigle;
        b.append(carte);
      }
    } catch (e) {
      bouton.textContent = "Prises de parole indisponibles : " + e.message;
    }
  });
  return b;
}

/* Une vue de l'onglet « Texte » : son bouton s'allume, sa version se charge
   — une fois pour toutes — et ses articles se dessinent. `o` porte ce que la
   vue a besoin de retrouver : le texte, les boutons, le sous-titre, la zone. */
async function montrerLaVue(o, vue) {
  for (const b2 of o.boutons) {
    b2.setAttribute("aria-pressed", String(b2.dataset.cle === vue.cle));
  }
  o.sous.textContent = vue.sous;
  o.zone.textContent = "";
  o.zone.append(el("p", "avertissement", "Chargement…"));
  const d = await versionLue(o.uid, vue.fichier);
  // Un autre bouton a pu être touché pendant le chargement : ne pas écraser
  // ce qu'on regarde maintenant par ce qu'on regardait avant.
  if (o.sous.textContent !== vue.sous) return;
  o.zone.textContent = "";
  o.zone.append(d ? articlesDeLaVersion(d, vue.mode, o.uid)
                  : el("p", "avertissement", "Texte indisponible."));
}

async function detailVotes(t) {
  const e = t.voteEnsemble;
  const [titre, quoi] = e ? EXPLICATIONS.voteEnsemble : EXPLICATIONS.votesAmendements;
  expliquer(titre, quoi, e
    ? `${e.sort} le ${dateLongue.format(enDate(e.date))}`
    : `${nb.format(t.votes)} votes, aucun sur le texte entier`);

  const zone = el("div", "groupes");
  zone.append(el("p", "attente", "Chargement du détail par groupe…"));
  $("info-texte").after(zone);

  try {
    const detail = await fetch(`${SOCLE}/textes/${t.uid}.json`).then((r) => {
      if (!r.ok) throw new Error("réponse " + r.status);
      return r.json();
    });
    const votes = detail.votes || [];
    const principal = votes.find((v) => v.portee === "ensemble") || votes[0];
    zone.textContent = "";
    if (!principal) { zone.append(el("p", "attente", "Aucun détail publié.")); return; }

    zone.append(el("p", "objet", principal.objet));
    const rappel = el("p", "convention");
    rappel.textContent = "Groupes rangés comme dans l'hémicycle, de la gauche à la droite.";
    zone.append(rappel);

    zone.append(legendeDesVotes());
    for (const g of principal.groupes) zone.append(ligneDuGroupeAuVote(g));
    if (votes.length > 1) {
      zone.append(el("p", "attente",
        `Ce texte compte ${nb.format(votes.length)} votes enregistrés en tout.`));
    }
  } catch (erreur) {
    zone.textContent = "";
    zone.append(el("p", "attente", "Détail indisponible : " + erreur.message));
  }
}

function ouvrirDisputes(uid) {
  const f = ouvrirEcran();
  f.append(boutonRetour("#/texte/" + uid, "Retour au texte"));

  const t = TEXTES.find((x) => x.uid === uid) || {};
  const disputes = amendementsDisputes(t);
  f.append(el("h2", "fiche-titre", "Adoptés de justesse, après un long échange"));
  if (t.titre) f.append(el("p", "fiche-sous", t.titre));

  if (!disputes.length) {
    // On n'y arrive normalement pas : le repère n'existe que s'il y en a. Mais
    // une adresse se partage, et les données changent chaque matin.
    f.append(el("div", "vide",
      "Aucun amendement de ce texte ne porte ce repère aujourd'hui."));
    return;
  }

  const b = bloc(`${nb.format(disputes.length)} amendement`
                 + `${disputes.length > 1 ? "s" : ""}`, false, true);
  b.append(el("p", "avertissement", EXPLICATIONS.amendementDebattu[1]));
  const boite = el("div", "amdts");
  // Le vote le plus serré en tête, puis le débat le plus fourni : deux
  // conditions séparées, donc deux clés de tri, dans l'ordre où on les lit.
  for (const a of disputes.slice().sort(
        (x, y) => x.vote.ecart - y.vote.ecart
                  || y.debat.orateurs - x.debat.orateurs)) {
    const ligne = ligneAmendement(a, uid);
    // Sur quel article il agit : ici, la liste traverse tout le texte, la
    // question se pose donc à chaque ligne.
    if (a.article) {
      ligne.insertBefore(el("span", "quand-amdt", a.article),
                         ligne.querySelector(".etiq.dispute"));
    }
    boite.append(ligne);
  }
  b.append(boite);
  f.append(b);
}

async function ouvrirAmendement(uid, amdt) {
  const f = ouvrirEcran();
  const retour = boutonRetour("#/texte/" + uid, "Retour au texte");
  f.append(retour, el("p", "avertissement", "Chargement de l'amendement…"));

  let a;
  try {
    a = await lire(`amendements/${uid}/${amdt}.json`, true);
  } catch (e) {
    f.textContent = "";
    f.append(retour, el("div", "vide", "Amendement indisponible : " + e.message));
    return;
  }
  f.textContent = "";
  f.append(retour);
  f.append(el("h2", "fiche-titre", "Amendement n° " + (a.numero || "—")));
  const situe = [a.article, a.sort,
                 a.date_depot ? "déposé le " + dateLongue.format(enDate(a.date_depot)) : ""]
    .filter(Boolean).join(" · ");
  f.append(el("p", "fiche-sous", situe));

  const auteur = auteurDeLAmendement(a);
  if (auteur) f.append(auteur);

  if (estDebattu(a)) {
    const l = el("div", "lignes");
    const marque = etiquette("dispute", "", EXPLICATIONS.amendementDebattu,
                             "n° " + a.numero);
    marque.append(el("b", null, "!"),
                  document.createTextNode("Adopté de justesse, après un long échange"));
    l.append(marque);
    f.append(l);
  }

  f.append(blocDispositif(a));

  if (a.expose) {
    const e = bloc("Ce que son auteur en dit", false, true);
    e.append(el("p", "expose", a.expose));
    f.append(e);
  }

  f.append(blocVoteAmendement(a, situe));

  const debat = blocDebatAmendement(a);
  if (debat) f.append(debat);

  f.append(lienVersLAssemblee(a));
}

async function ouvrirVersion(uid, ref) {
  const f = ouvrirEcran();
  const retour = boutonRetour("#/texte/" + uid, "Retour au parcours");
  f.append(retour);
  f.append(el("p", "avertissement", "Chargement du texte…"));

  let d;
  try {
    d = await lire(`versions/${uid}/${ref}.json`, true);
  } catch (e) {
    f.textContent = "";
    f.append(retour, el("div", "vide", "Texte indisponible : " + e.message));
    return;
  }
  f.textContent = "";
  f.append(retour);
  f.append(el("h2", "fiche-titre", d.nom));
  f.append(el("p", "fiche-sous", d.precedent
    ? `${dateLongue.format(enDate(d.date))} — comparé au ${d.precedent.nom.toLowerCase()} `
      + `du ${dateLongue.format(enDate(d.precedent.date))}.`
    : `${dateLongue.format(enDate(d.date))} — le texte tel qu'il a été déposé. `
      + `Rien ne le précède : il n'y a rien à comparer.`));

  const tous = (d.articles || []).flatMap((a) => a.morceaux || []);
  // Qui a changé le texte : la commission pour un texte de commission, la
  // séance pour un texte adopté. C'est la forme du document qui le dit.
  const par = /BTC\d+$/.test(d.ref) ? "par la commission"
            : /BTA\d+$/.test(d.ref) ? "en séance"
            : "depuis la version précédente";
  if (tous.length) f.append(legendeDiff(tous, par));

  for (const a of d.articles || []) {
    const tete = el("div", "art-titre");
    tete.append(el("h3", null, a.titre));
    const mots = { modifie: "Modifié", nouveau: "Nouveau", retire: "Retiré",
                   identique: "Inchangé", initial: null };
    if (mots[a.quoi]) tete.append(el("span", "quoi " + a.quoi, mots[a.quoi]));
    // L'état que la source elle-même imprime dans le texte — « (Supprimé) »,
    // « (Non modifié) ». Ce n'est pas notre calcul, c'est sa mention.
    if (a.etat && a.etat !== a.quoi) {
      tete.append(el("span", "quoi", "La source dit : " + a.etat));
    }
    f.append(tete);
    if (A_CHANGE.has(a.quoi)) {
      f.append(carteAmendementsDeLArticle(a.amendements || [], uid));
    }
    f.append(texteCompare(a.morceaux, "diff", a.texte));
  }

  f.append(el("p", "avertissement",
    "Les amendements sont rapprochés par le numéro d'article : la page dit "
    + "lesquels ont été adoptés sur cet article, jamais quel mot vient de quel "
    + "amendement — il faudrait pour cela interpréter l'instruction de "
    + "l'amendement, et le texte affiché ne serait plus celui de la source."));
}
