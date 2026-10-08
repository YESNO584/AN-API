/* La fiche d'un amendement adopté : son auteur, ce qu'il fait, son vote, son débat, son lien. */

/* Son auteur : un député avec sa photo et son groupe, ou le type que la
   source nomme — « Gouvernement », « Commission ». */
function auteurDeLAmendement(a) {
  if (a.nom) {
    return personne({ civilite: a.civilite, prenom: a.prenom, nom: a.nom,
                      photo: a.photo, sigle: a.sigle, nom_groupe: a.nom_groupe,
                      couleur: a.couleur }, "Auteur de l'amendement");
  }
  if (a.type_auteur) {
    const b = bloc("Auteur de l'amendement", false, true);
    b.append(el("p", "disp", a.type_auteur));
    return b;
  }
  return null;
}

function blocDispositif(a) {
  // Ce que l'amendement fait, mot pour mot. **Rien n'est reconstitué** : la
  // coloration ne marque que ce que la source met elle-même entre guillemets.
  const quoi = bloc("Ce que l'amendement fait", false, true);
  quoi.append(el("p", "avertissement",
    "Un amendement n'est pas une version modifiée du texte : c'est une "
    + "instruction, reproduite ici mot pour mot. En vert ce qu'il ajoute, en "
    + "rouge barré ce qu'il retire — d'après sa propre formulation."));
  const disp = el("p", "disp");
  for (const m of a.morceaux || []) {
    if (m.role === "neutre") disp.append(document.createTextNode(m.texte));
    else disp.append(el("span", m.role, "« " + m.texte + " »"));
  }
  if (!(a.morceaux || []).length) disp.textContent = a.dispositif || "";
  quoi.append(disp);
  return quoi;
}

/* Le scrutin, groupe par groupe — le même dessin que partout ailleurs. */
function blocVoteAmendement(a, situe) {
  if (a.vote) {
    const v = bloc(`Le vote — ${nb.format(a.vote.pour)} pour, `
                   + `${nb.format(a.vote.contre)} contre`, false, true);
    v.append(groupesDuVote({ ...a.vote, objet: a.vote.objet || situe }));
    return v;
  } else {
    const v = bloc("Le vote", false, true);
    v.append(el("p", "avertissement",
      "Aucun scrutin public sur cet amendement. C'est le cas le plus "
      + "fréquent : 97 % des amendements adoptés le sont à main levée, sans "
      + "qu'aucun décompte de voix soit enregistré."));
    return v;
  }
}

/* Le débat : un compte, jamais les phrases. Les rapprocher d'un amendement
   demanderait de trancher des cas que la source ne tranche pas. */
function blocDebatAmendement(a) {
  if (!a.debat) return null;
  const d = bloc("Le débat en séance", false, true);
  d.append(el("p", "disp",
    `${nb.format(a.debat.orateurs)} personne`
    + `${a.debat.orateurs > 1 ? "s ont" : " a"} pris la parole sur cet `
    + `amendement, en ${nb.format(a.debat.paragraphes)} paragraphes de `
    + `compte rendu.`));
  d.append(el("p", "avertissement",
    "Le projet compte les orateurs, il ne recopie pas ce qu'ils ont dit : "
    + "rattacher une phrase à un amendement demanderait de trancher des cas "
    + "que la source ne tranche pas. Le compte rendu entier est sur le site "
    + "de l'Assemblée."));
  return d;
}

function lienVersLAssemblee(a) {
  const liens = el("div", "liens");
  const lien = el("a", "etiq lien", "Voir l'amendement sur assemblee-nationale.fr");
  lien.href = "https://www.assemblee-nationale.fr/dyn/17/amendements/" + a.uid;
  lien.target = "_blank"; lien.rel = "noopener";
  liens.append(lien);
  return liens;
}
