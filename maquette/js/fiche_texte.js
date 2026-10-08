/* L'onglet « Texte » : le texte déposé comparé à la version à jour, article par article. */

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

// Le texte demandé, gardé une fois lu : passer d'un bouton à l'autre ne doit
// pas retélécharger 2,8 Mo. La clé est le nom du fichier, pas le mode — deux
// des trois vues se dessinent à partir du même.
const VERSIONS_LUES = new Map();

async function versionLue(uid, nom) {
  const cle = uid + "/" + nom;
  if (!VERSIONS_LUES.has(cle)) {
    VERSIONS_LUES.set(cle, await lire(`versions/${uid}/${nom}.json`));
  }
  return VERSIONS_LUES.get(cle);
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

  const sous = el("p", "sous-texte");
  const zone = el("div");
  let boutons = [];

  const montrer = async (vue) => {
    for (const b2 of boutons) {
      b2.setAttribute("aria-pressed", String(b2.dataset.cle === vue.cle));
    }
    sous.textContent = vue.sous;
    zone.textContent = "";
    zone.append(el("p", "avertissement", "Chargement…"));
    const d = await versionLue(uid, vue.fichier);
    // Un autre bouton a pu être touché pendant le chargement : ne pas écraser
    // ce qu'on regarde maintenant par ce qu'on regardait avant.
    if (sous.textContent !== vue.sous) return;
    zone.textContent = "";
    zone.append(d ? articlesDeLaVersion(d, vue.mode, uid)
                  : el("p", "avertissement", "Texte indisponible."));
  };

  if (vues.length > 1) {
    // Les mêmes trois boutons côte à côte que pour un article de loi : un seul
    // geste à apprendre pour choisir ce qu'on regarde, partout dans la fiche.
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
    b.append(bascule);
  } else {
    b.append(el("p", "avertissement",
      "Une seule version de ce texte est publiée : il n'y a donc rien à "
      + "comparer, et le texte déposé est aussi le texte à jour."));
  }
  b.append(sous, zone);
  // La première vue est demandée à l'ouverture de l'onglet, pas à celle de la
  // fiche : une version pèse jusqu'à 2,8 Mo, et l'onglet n'est pas toujours
  // celui qu'on ouvre.
  return [b, () => montrer(vues[0])];
}

/* ---------- le résumé des débats ---------- *
 * **La seconde rubrique écrite par une IA**, après la description d'un texte.
 * Elle range les groupes par ce qu'ils ont voté et donne au plus quatre
 * arguments par groupe. Deux choses la tiennent :
 *
 *   — le classement pour / contre vient du **scrutin**, pas de la rédaction :
 *     une phrase d'orateur ne décide jamais d'un vote affiché. Mesuré le
 *     2026-09-02, l'UDR a voté *pour* les soins palliatifs pendant que son
 *     orateur disait « votera contre » — il parlait de l'autre texte du jour ;
 *   — les prises de parole complètes restent affichées en dessous, mot pour
 *     mot. Le résumé s'ajoute, il ne remplace rien.
 * ------------------------------------------------------------------ */

/* Les camps, dans cet ordre. « Partagé » n'est pas un demi-vote : c'est un
   groupe dont les voix se sont réparties sans majorité claire — le socle le
   calcule sur le décompte, jamais sur la position annoncée par la source, qui
   la contredit dans 3 % des cas. */
const CAMPS = {
  pour: "Ont voté pour",
  contre: "Ont voté contre",
  abstention: "Se sont abstenus",
  "partagé": "Se sont partagés",
  aucun_vote: "N'ont pas voté",
};

const ORIGINE_RESUME = {
  ia: {
    mot: "Résumé généré par une intelligence artificielle",
    court: "Généré par une IA",
    titre: "Ce résumé est généré par une IA",
    quoi: "Les arguments de ce résumé ont été écrits par une intelligence " +
      "artificielle à partir des prises de parole publiées plus bas. Elle " +
      "peut donc se tromper, ou choisir mal. Les prises de parole, elles, " +
      "sont recopiées du compte rendu de l'Assemblée, mot pour mot : elles " +
      "sont sous ce résumé, entières.\n\nCe qui n'est pas écrit par l'IA : " +
      "le classement « ont voté pour » et « ont voté contre » est relevé dans " +
      "le scrutin publié par l'Assemblée. Aucune phrase d'orateur ne décide " +
      "d'un vote affiché — un orateur peut annoncer un vote et son groupe en " +
      "émettre un autre, et cela s'est vu.",
  },
  humain: {
    mot: "Résumé écrit par une personne",
    court: "Écrit par une personne",
    titre: "Ce résumé est écrit par une personne",
    quoi: "Les arguments de ce résumé ont été rédigés pour cette application " +
      "à partir des prises de parole publiées plus bas, qui sont recopiées du " +
      "compte rendu de l'Assemblée, mot pour mot.\n\nLe classement « ont voté " +
      "pour » et « ont voté contre », lui, est relevé dans le scrutin publié " +
      "par l'Assemblée.",
  },
};
