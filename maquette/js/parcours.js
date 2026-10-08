/* Le parcours d'un texte dans les deux chambres, étape par étape, votes compris — ceux du Sénat à leur date, jamais mêlés. */

function personne(p, role) {
  const bloc = el("div", "auteur");
  if (p.photo) {
    const img = el("img");
    img.src = p.photo;
    img.alt = "";
    img.loading = "lazy";
    // Toutes les photos ne sont pas en ligne : on remplace sans casser la mise
    // en page plutôt que d'afficher une image brisée.
    img.addEventListener("error", () => img.replaceWith(el("div", "sans-photo", "—")));
    bloc.append(img);
  } else {
    bloc.append(el("div", "sans-photo", "—"));
  }
  const qui = el("div", "qui");
  qui.append(el("div", "nom", [p.civilite, p.prenom, p.nom].filter(Boolean).join(" ")));
  if (role) qui.append(el("div", "role", role));
  if (p.sigle) {
    const g = el("div", "grp");
    const teinte = el("i");
    if (p.couleur) teinte.style.background = p.couleur;
    g.append(teinte);
    g.append(document.createTextNode(p.nom_groupe || p.sigle));
    qui.append(g);
  }
  bloc.append(qui);
  return bloc;
}

// Une rubrique de la fiche. Par défaut un dépliant ; `plat` la rend toujours
// ouverte, pour une rubrique posée dans un onglet — l'onglet a déjà fait le
// choix de ce qu'on regarde, et il n'y aurait rien à déplier de plus.
function bloc(titre, ouvert, plat) {
  if (plat) {
    const b = el("div", "bloc");
    b.append(el("h3", null, titre));
    return b;
  }
  const b = el("details", "bloc");
  if (ouvert) b.open = true;
  b.append(el("summary", null, titre));
  return b;
}

/* ---------- le parcours ---------- */

/* La même étiquette que dans le fil : même forme, mêmes couleurs. Une pastille
   propre au parcours donnerait deux vocabulaires visuels pour une seule idée. */
function pastilleChambre(chambre) {
  return etiquette("chambre-" + (chambre || "aucune"),
                   CHAMBRES[chambre][0], CHAMBRES[chambre]);
}

/* Ce que chaque champ publié veut dire. **La valeur affichée, elle, vient des
   données** : ce tableau ne donne que le nom du champ et son explication —
   aucune phrase n'y décrit un texte à la place de sa source. */
const CHAMPS_ETAPE = {
  organe: ["Qui s'est réuni",
    "La commission ou l'organe désigné par l'acte. Une chambre travaille d'abord " +
    "en commission — un groupe restreint de parlementaires spécialisés — avant que " +
    "le texte n'arrive devant tous les élus."],
  texteAssocie: ["Le document de cette étape",
    "Le document parlementaire attaché à l'acte, avec son numéro d'impression. " +
    "C'est sous ce numéro que le texte circule."],
  texteAdopte: ["Le texte qui en sort",
    "La nouvelle version du texte produite par cette étape. C'est elle qui servira " +
    "de base à l'étape suivante — pas la version précédente."],
  rapporteurs: ["Le ou les rapporteurs",
    "Le parlementaire chargé d'examiner le texte au nom de la commission et d'en " +
    "rendre compte. Son rapport oriente le débat."],
  provenance: ["D'où vient le document",
    "La qualification que l'Assemblée donne au document : texte déposé, texte " +
    "transmis par l'autre chambre…"],
  saisine: ["Qui a saisi le Conseil constitutionnel",
    "Le Conseil ne s'autosaisit pas d'une loi ordinaire : il faut que le Président " +
    "de la République, un président de chambre, ou soixante parlementaires le " +
    "saisissent."],
  motif: ["Sur quel fondement",
    "L'article de la Constitution invoqué pour cette saisine."],
  decision: ["Le numéro de la décision",
    "La décision rendue par le Conseil constitutionnel, sous son numéro officiel."],
  loi: ["Le numéro de la loi",
    "Une fois promulgué, le texte reçoit un numéro définitif — année et rang dans " +
    "l'année — sous lequel il sera cité désormais."],
  journalOfficiel: ["Le Journal officiel",
    "Le numéro du Journal officiel où la loi a été publiée. La publication est ce " +
    "qui la rend applicable."],
  dateJO: ["La date de publication",
    "Le jour où la loi a paru au Journal officiel."],
};

function valeurChamp(cle, v) {
  const zone = el("div", "val");
  if (cle === "texteAdopte" || cle === "texteAssocie") {
    zone.append(document.createTextNode(
      [v.type, v.numero ? "n° " + v.numero : null].filter(Boolean).join(" ") || v.ref));
    // La « formule » de l'Assemblée est un fragment de phrase : « , adoptée,
    // par le Sénat, visant à… ». On enlève la ponctuation de tête, rien d'autre.
    if (v.description) zone.append(el("small", null, v.description.replace(/^[\s,;]+/, "")));
    return zone;
  }
  zone.textContent = Array.isArray(v) ? v.join(", ") : String(v);
  return zone;
}

function champsEtape(details) {
  const zone = el("div", "champs");
  let vus = 0;
  for (const [cle, libelleEtQuoi] of Object.entries(CHAMPS_ETAPE)) {
    const v = details[cle];
    if (v == null || (Array.isArray(v) && !v.length)) continue;
    const ligne = el("div");
    const b = el("button", "etiq cle", libelleEtQuoi[0]);
    b.addEventListener("click", (ev) => {
      ev.preventDefault();
      expliquer(libelleEtQuoi[0], libelleEtQuoi[1], null);
    });
    ligne.append(b, valeurChamp(cle, v));
    zone.append(ligne);
    vus++;
  }
  if (!vus) {
    zone.append(el("p", "vide",
      "L'open data ne publie rien de plus sur cette étape que sa nature et sa date."));
  }
  return zone;
}

function ligneParcours(e) {
  const li = el("li");
  if (e.future) li.classList.add("avenir");
  const d = el("details");
  const tete = el("summary", "rang");
  tete.append(el("span", "j", dateCourte.format(enDate(e.date))));
  const q = el("div", "q");
  q.append(el("b", null, e.libelle || e.code));
  const ch = el("div", "ch");
  ch.append(pastilleChambre(e.chambre));
  for (const [mot, quoi] of [[e.lecture, EXPLICATIONS.lecture],
                             [e.precision, EXPLICATIONS.precision],
                             [e.conclusion, EXPLICATIONS.conclusion]]) {
    if (mot) ch.append(etiquette("", mot, quoi));
  }
  q.append(ch);
  tete.append(q);
  tete.append(el("span", "chevron", "▸"));
  d.append(tete);
  d.append(champsEtape(e.details || {}));
  li.append(d);
  return li;
}

// Le numéro que l'objet d'un scrutin nomme : « l'amendement n° 885 (rect.) du
// Gouvernement à l'article 3 du projet de loi… ». Le premier nommé seulement —
// un objet qui ajoute « et les amendements identiques suivants » ne dit pas
// lesquels.
const NUMERO_D_AMENDEMENT = /(l['’]amendement|le sous-amendement)\s+n°\s*(\d+(?:\s*\(rect[^)]*\))?)/i;

function ligneVoteParcours(v) {
  const li = el("li");
  const d = el("details");
  const tete = el("summary", "rang");
  tete.append(el("span", "j", dateCourte.format(enDate(v.date))));
  const q = el("div", "q");
  // « Vote sur l'amendement n° 885 » plutôt que « Vote sur un amendement » :
  // une fiche en compte jusqu'à 290, et sans le numéro elles se ressemblent
  // toutes. Le numéro vient de l'objet du scrutin, mot pour mot.
  const nomme = v.portee === "amendement"
    ? (v.objet || "").match(NUMERO_D_AMENDEMENT) : null;
  // Avec un numéro, le libellé devient précis — « Vote sur l'amendement
  // n° 885 » — et l'article indéfini de `PORTEES` n'a plus lieu d'être.
  q.append(el("b", null, nomme
    ? "Vote sur " + nomme[1].toLowerCase() + " n° " + nomme[2].replace(/\s+/g, " ")
    : (PORTEES[v.portee] || ["Vote"])[0]));
  const ch = el("div", "ch");
  // La même pastille que dans l'onglet « Texte », aux mêmes deux conditions.
  // Le compte des orateurs est publié sur le scrutin lui-même, rattaché par
  // le socle — la page ne rapproche rien.
  if (estDebattu({ vote: { ecart: ecartDuVote(v) }, debat: v.debat })) {
    const marque = etiquette("dispute", "", EXPLICATIONS.amendementDebattu,
                             nomme ? "n° " + nomme[2] : v.objet);
    marque.append(el("b", null, "!"));
    ch.append(marque);
  }
  ch.append(etiquette(v.sort === "adopté" ? "promulguee" : "arrete",
                      v.sort === "adopté" ? "Adopté" : "Rejeté",
                      EXPLICATIONS.conclusion,
                      `${v.pour} pour · ${v.contre} contre · ${v.abstentions} abstentions`));
  ch.append(etiquette("", `${v.pour} / ${v.contre}`, EXPLICATIONS.vote,
                      `${v.pour} pour, ${v.contre} contre`));
  q.append(ch);
  tete.append(q);
  tete.append(el("span", "chevron", "▸"));
  d.append(tete);
  const corps = el("div", "champs");
  const objet = el("div");
  objet.append(el("span", "cle", "Sur quoi"), el("div", "val", v.objet));
  corps.append(objet);
  const bouton = el("button", "charger", "Voir le détail par groupe");
  bouton.addEventListener("click", (ev) => { ev.preventDefault(); detailVoteConnu(v); });
  corps.append(bouton);
  d.append(corps);
  li.append(d);
  return li;
}

/* Étapes et votes dans un seul fil, par date. Les étapes d'un même jour
   gardent l'ordre du fichier source ; les votes de ce jour-là viennent
   ensuite, parce que **l'open data ne dit pas à quel moment de la journée un
   scrutin a eu lieu** — son champ `referenceLegislative` est vide dans les
   8 434 scrutins de la législature (mesuré le 2026-08-31). */
function filDuParcours(d) {
  const items = [];
  (d.parcours || []).forEach((e, i) => items.push({ date: e.date, rang: [0, i], e }));
  (d.votes || []).forEach((v, i) => items.push({ date: v.date, rang: [1, i], v }));
  // Les scrutins du Sénat, à leur date, **à côté de ceux de l'Assemblée et
  // jamais mêlés à eux** : chaque ligne dit sa chambre, et rien n'additionne
  // ni ne compare les deux. Les chiffres viennent de l'open data du Sénat, le
  // lien avec le texte de ses pages de scrutins publics.
  (d.votesSenat || []).forEach((v, i) => items.push({ date: v.date, rang: [2, i], s: v }));
  items.sort((a, b) => a.date.localeCompare(b.date) ||
                       a.rang[0] - b.rang[0] || a.rang[1] - b.rang[1]);
  return items;
}

/* Une ligne de scrutin du Sénat dans le parcours. Elle ne réemploie pas celle
   de l'Assemblée : les deux ne portent pas les mêmes chiffres — le Sénat ne
   publie pas les abstentions au niveau du scrutin — et les faire se ressembler
   au point de s'additionner serait le piège à éviter. */
function ligneVoteSenat(v) {
  const li = el("li", "vote-senat");
  const l = el("div", "lignes");
  l.append(etiquette("chambre-senat", "Sénat", CHAMBRES.senat,
                     dateCourte.format(enDate(v.date))));
  const exprimes = (v.pour || 0) + (v.contre || 0);
  const adopte = exprimes && v.pour > v.contre;
  l.append(etiquette(adopte ? "promulguee" : "arrete",
                     adopte ? "Adopté" : "Rejeté", EXPLICATIONS.voteSenat,
                     v.objet || null));
  l.append(etiquette("", `${nb.format(v.pour || 0)} / ${nb.format(v.contre || 0)}`,
                     EXPLICATIONS.voteSenat, "pour / contre"));
  li.append(l);
  li.append(el("p", "objet-vote", v.objet || "Scrutin public au Sénat"));
  if (v.groupes && v.groupes.length) {
    const bouton = el("button", "charger", "Qui a voté quoi");
    bouton.addEventListener("click", () => {
      bouton.remove();
      const t = el("div", "groupes-senat");
      for (const g of v.groupes) {
        const ligne = el("div", "grp-senat");
        ligne.append(el("span", "qui", g.nom || g.sigle));
        const chiffres = [];
        if (g.pour) chiffres.push(`${g.pour} pour`);
        if (g.contre) chiffres.push(`${g.contre} contre`);
        if (g.abstentions) chiffres.push(`${g.abstentions} abst.`);
        ligne.append(el("span", "chiffres-amdt", chiffres.join(" · ") || "—"));
        t.append(ligne);
      }
      li.append(t);
    });
    li.append(bouton);
  }
  return li;
}

const PORTEES = {
  ensemble: ["Vote sur le texte entier",
    "La chambre s'est prononcée sur l'ensemble du texte. C'est ce vote qui décide " +
    "si le texte poursuit son chemin."],
  article: ["Vote sur un article",
    "La chambre s'est prononcée sur un seul article, pas sur l'ensemble."],
  amendement: ["Vote sur un amendement",
    "La chambre s'est prononcée sur une modification proposée au texte."],
  motion: ["Vote sur une motion",
    "Un vote de procédure : rejeter le texte avant de l'examiner, ou censurer le Gouvernement."],
  autre: ["Autre vote", "Un vote qui ne porte ni sur le texte, ni sur un article, ni sur un amendement."],
};
const extraction_portee = (p) => (PORTEES[p] || ["Vote"])[0];

function detailVoteConnu(v) {
  expliquer(...(PORTEES[v.portee] || ["Vote", ""]),
            `${v.sort} · ${v.pour} pour, ${v.contre} contre, ${v.abstentions} abstentions`);
  $("info-texte").after(groupesDuVote(v));
}

/* Qui a voté quoi, groupe par groupe : l'objet du scrutin, la légende, puis
 * une barre par groupe, **rangés comme dans l'hémicycle** — un ordre mesuré
 * sur les numéros de siège, pas décidé. Écrit une fois et posé à deux
 * endroits : l'onglet « Vote » de la fiche, où il s'affiche d'emblée, et le
 * panneau d'explication ouvert depuis une ligne du parcours.
 * ------------------------------------------------------------------ */
function groupesDuVote(v) {
  const zone = el("div", "groupes");
  zone.append(el("p", "objet", v.objet));
  const legende = el("div", "legende");
  for (const [cle, mot] of [["pour", "pour"], ["contre", "contre"], ["abstention", "abstention"]]) {
    const item = el("span", null);
    item.append(el("i", cle));
    item.append(document.createTextNode(mot));
    legende.append(item);
  }
  zone.append(legende);
  for (const g of v.groupes || []) {
    const total = (g.pour || 0) + (g.contre || 0) + (g.abstentions || 0);
    const ligne = el("div", "groupe");
    const teinte = el("i", "teinte");
    if (g.couleur) teinte.style.background = g.couleur;
    ligne.append(teinte);
    ligne.append(el("span", "sigle", g.sigle));
    const barre = el("span", "barre");
    for (const [cle, n] of [["pour", g.pour], ["contre", g.contre], ["abstention", g.abstentions]]) {
      if (!n) continue;
      const part = el("i", cle);
      part.style.flexGrow = String(n);
      barre.append(part);
    }
    if (!total) barre.append(el("i", "vide"));
    ligne.append(barre);
    ligne.append(el("span", "detail", total ? `${g.pour}/${g.contre}/${g.abstentions}` : "n'a pas voté"));
    zone.append(ligne);
  }
  return zone;
}

/* ---------- l'onglet « Vote » ---------- *
 * Le vote sur l'ensemble du texte : celui qui décide. Il était posé au-dessus
 * des onglets, replié, et il fallait deux gestes pour savoir qui avait voté
 * quoi. Il ouvre maintenant la fiche, **le détail par groupe déjà déplié** —
 * c'est la question qu'on vient poser à un texte voté.
 *
 * Les votes sur des amendements ou des articles restent dans le parcours, à
 * leur date : un vote de détail ne se lit que dans son moment.
 * ------------------------------------------------------------------ */
function blocVote(v) {
  const b = bloc(`${(PORTEES[v.portee] || ["Vote"])[0]} — `
                 + dateLongue.format(enDate(v.date)), false, true);
  const l = el("div", "lignes");
  l.append(etiquette(v.sort === "adopté" ? "promulguee" : "arrete",
                     v.sort === "adopté" ? "Adopté" : "Rejeté",
                     EXPLICATIONS.conclusion,
                     `${v.pour} pour · ${v.contre} contre · ${v.abstentions} abstentions`));
  l.append(etiquette("", `${v.pour} / ${v.contre}`, EXPLICATIONS.vote,
                     `${v.pour} pour, ${v.contre} contre`));
  b.append(l);
  b.append(groupesDuVote(v));
  return b;
}
