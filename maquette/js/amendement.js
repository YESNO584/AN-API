/* La fiche d'un amendement adopté, et la liste des amendements adoptés de justesse d'un texte. */

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

/* ------------------------------------------------------------------ *
 * Le calendrier : les séances, les votes et les décisions, jour par jour
 *
 * Un fichier par mois, chargé quand on l'ouvre. Chaque événement mène à la
 * fiche de son texte — c'est ce qui en fait un calendrier utile plutôt qu'une
 * liste de dates.
 * ------------------------------------------------------------------ */

const GENRES = {
  seance: ["Séance publique", "Le texte est discuté devant tous les députés ou sénateurs."],
  commission: ["Commission", "Une commission examine le texte et l'amende avant la séance."],
  decision: ["Décision", "Le texte est adopté, rejeté ou renvoyé à ce moment-là."],
  vote: ["Scrutin public", "Un vote dont le détail, groupe par groupe, est enregistré."],
  promulgation: ["Promulgation", "Le Président signe : le texte devient une loi."],
};
const JOURS = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"];
const moisLong = new Intl.DateTimeFormat("fr-FR", { month: "long", year: "numeric" });
const _jourLong = new Intl.DateTimeFormat("fr-FR",
  { weekday: "long", day: "numeric", month: "long" });
// « lundi 1er juin », comme partout ailleurs.
const jourLong = { format: (d) => premier(_jourLong.format(d), d) };

let AGENDA = null;              // l'index des mois, chargé une fois
let MOIS_VU = null;             // « 2026-07 »
let JOUR_VU = null;             // « 2026-07-21 »
const MOIS_EN_CACHE = new Map();

const moisDe = (iso) => iso.slice(0, 7);
const aujourdhui = () => new Date().toISOString().slice(0, 10);
