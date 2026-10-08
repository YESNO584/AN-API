/* Le parcours d'un texte dans les deux chambres, étape par étape, votes compris — ceux du Sénat à leur date, jamais mêlés à ceux de l'Assemblée. */

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
