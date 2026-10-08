/* Ouvrir l'hémicycle, la composition du Sénat et les deux calendriers ; changer de mois, choisir le dessin. */

/* Un seul écran, deux états : tous les groupes, ou un seul groupe ouvert avec
   ses députés en dessous. C'est l'adresse qui porte l'état — `#/hemicycle` ou
   `#/hemicycle/<sigle>` — de sorte que le retour du téléphone referme le
   groupe au lieu de quitter l'hémicycle. */
async function ouvrirHemicycle(sigle = null) {
  const f = ouvrirEcran();
  f.append(boutonRetour("", "Retour au fil"));
  f.append(el("h2", "fiche-titre", "L'Assemblée nationale"));

  // Les groupes sans député sont écartés par la publication ; l'ordre vient
  // d'elle aussi. Le tri est ici par sûreté, pas pour recalculer quoi que ce soit.
  const groupes = [...GROUPES.values()]
    .filter((g) => g.effectif > 0)
    .sort((a, b) => a.rang - b.rang);
  if (!groupes.length) {
    f.append(el("div", "vide",
      "Composition indisponible : la publication du jour ne porte pas encore "
      + "l'effectif des groupes."));
    return;
  }
  const choisi = groupes.find((g) => g.sigle === sigle) || null;
  const total = groupes.reduce((n, g) => n + g.effectif, 0);

  const [sous, totalHF] = sousTitreDeLAssemblee(total, groupes);
  f.append(sous);

  const zone = el("div", "hemicycle");
  f.append(zone);
  const boutons = basculeDuDessin(zone, (siege, bts) => choisirLeDessin(
    siege, bts, () => poserLeDessin(zone, groupes, total, choisi, sigle, PAR_SIEGE)));
  poserLeDessin(zone, groupes, total, choisi, sigle, PAR_SIEGE);

  // La liste : tous les groupes, ou le seul qui est ouvert.
  const liste = el("div", "hemi-liste");
  f.append(liste);
  for (const g of (choisi ? [choisi] : groupes)) {
    // Le compte femmes / hommes arrive avec le fichier du groupe : la ligne
    // s'affiche sans attendre, et se complète. Un fichier qui manque ne laisse
    // pas un chiffre faux, il ne laisse rien.
    const hf = el("span", "hf");
    liste.append(ligneDeGroupe(g, choisi, g.sigle, g.nom || "", " dép.", "#/hemicycle", hf));
    membresDuGroupe(g).then((membres) => {
      if (!membres) return;
      const { femmes, hommes } = femmesEtHommes(membres);
      hf.textContent = `${nb.format(femmes)} F / ${nb.format(hommes)} H`;
    });
  }

  completerLesTotaux(groupes, boutons, totalHF,
                     () => poserLeDessin(zone, groupes, total, choisi, sigle, true));

  if (!choisi) return;
  await deputesDuGroupe(f, choisi);
}

/* Les députés du groupe ouvert, juste sous sa ligne. */
async function deputesDuGroupe(f, choisi) {
  const attente = el("p", "avertissement", "Chargement…");
  f.append(attente);
  const membres = await membresDuGroupe(choisi);
  attente.remove();
  if (!membres || !membres.length) {
    f.append(el("div", "vide",
      "La liste des députés de ce groupe n'est pas encore publiée. "
      + "Elle arrive avec la publication du matin."));
    return;
  }
  const detail = el("p", "fiche-sous",
    `${nb.format(membres.length)} députés, classés par nom. `);
  const aideNoms = el("button", "aide", "ⓘ");
  aideNoms.setAttribute("aria-label", "D'où viennent ces noms");
  aideNoms.addEventListener("click",
    () => expliquer(...EXPLICATIONS.deputes, choisi.sigle));
  detail.append(aideNoms);
  f.append(detail);

  const lignes = el("div", "deputes");
  for (const x of membres) lignes.append(ligneDepute(x));
  f.append(lignes);
}

/* Le total de l'Assemblée : la somme des douze groupes, pas un chiffre à
   part. Si un seul fichier manque, la phrase ne dit rien plutôt que de
   donner un total incomplet pour le total. */
function completerLesTotaux(groupes, boutons, totalHF, redessiner) {
  Promise.all(groupes.map(membresDuGroupe)).then((tous) => {
    if (tous.some((x) => !x)) return;
    boutons[1].disabled = false;
    if (PAR_SIEGE) redessiner();
    const somme = tous.flat();
    const { femmes, hommes } = femmesEtHommes(somme);
    if (femmes + hommes === somme.length) {
      totalHF.textContent = `${nb.format(femmes)} F / ${nb.format(hommes)} H. `;
    }
  });
}

/* Passer du dessin par groupe au dessin par siège, ou l'inverse. */
function choisirLeDessin(siege, boutons, redessiner) {
  if (PAR_SIEGE === siege) return;
  PAR_SIEGE = siege;
  boutons.forEach((x, i) => x.setAttribute("aria-pressed",
    String(PAR_SIEGE === (i === 1))));
  redessiner();
}

async function ouvrirCompositionSenat(sigle = null) {
  const f = ouvrirEcran();
  f.append(boutonRetour("", "Retour au fil"));
  f.append(el("h2", "fiche-titre", "Le Sénat"));
  f.append(el("p", "avertissement", "Chargement…"));

  const d = await lire("senat/composition.json");
  f.textContent = "";
  f.append(boutonRetour("", "Retour au fil"));
  f.append(el("h2", "fiche-titre", "Le Sénat"));
  if (!d || !(d.groupes || []).length) {
    f.append(el("div", "vide",
      "La composition du Sénat n'est pas publiée aujourd'hui. Les données du "
      + "Sénat sont une source facultative : le reste du site est à jour."));
    return;
  }

  const groupes = d.groupes.filter((g) => g.effectif > 0);
  const choisi = groupes.find((g) => g.sigle === sigle) || null;
  // Le dessin montre les sénateurs **qui ont un groupe**. Les 179 qui n'en ont
  // pas encore ne sont pas des non-inscrits : les faire figurer en gris les
  // donnerait pour tels.
  const places = groupes.reduce((n, g) => n + g.effectif, 0);

  f.append(sousTitreDuSenat(d, groupes));

  const veille = avisDuSenat();
  if (veille) f.append(veille);

  const zone = el("div", "hemicycle");
  f.append(zone);
  dessinDuSenat(zone, d, groupes, places, choisi, sigle);

  const liste = el("div", "hemi-liste");
  f.append(liste);
  for (const g of (choisi ? [choisi] : groupes)) {
    liste.append(ligneDeGroupe(g, choisi, g.nom || g.sigle, g.nomComplet || "",
                               " sén.", "#/senat/composition"));
  }

  f.append(el("p", "avertissement",
    "L'ordre des groupes est mesuré sur leur façon de voter, et non sur leurs "
    + "sièges : la numérotation du Sénat tourne rang par rang, et le groupe y "
    + "change 152 fois quand on suit les numéros. Il sépare nettement la "
    + "gauche, le centre et la droite ; à l'intérieur de ces blocs il ne "
    + "départage pas, et le sens — quel bout est la gauche — est une "
    + "convention assumée. Les couleurs, elles, sont celles du Sénat."));

  if (!choisi) return;

  senateursDuGroupe(f, d, choisi);

}

async function ouvrirAgenda() {
  const f = ouvrirEcran();
  const retour = boutonRetour("", "Retour au fil");
  f.append(retour);
  f.append(el("h2", "fiche-titre", "Calendrier"));

  if (!AGENDA) AGENDA = await lire("calendrier.json");
  if (!AGENDA || !(AGENDA.mois || []).length) {
    f.append(el("div", "vide", "Calendrier indisponible."));
    return;
  }
  f.append(el("p", "fiche-sous",
    `${nb.format(AGENDA.total)} séances, votes et décisions, de `
    + moisLong.format(enDate(AGENDA.mois[0].mois + "-01")) + " à "
    + moisLong.format(enDate(AGENDA.mois[AGENDA.mois.length - 1].mois + "-01")) + "."));

  // On ouvre sur le mois en cours s'il porte quelque chose, sinon sur le
  // dernier mois qui en porte : un calendrier vide au premier regard ne dit
  // pas où aller.
  if (!MOIS_VU) {
    const connus = AGENDA.mois.map((m) => m.mois);
    MOIS_VU = connus.includes(moisDe(aujourdhui()))
      ? moisDe(aujourdhui()) : connus[connus.length - 1];
  }
  const zone = el("div");
  f.append(zone);
  await dessinerMois(zone, CALENDRIER_AN);
}

/* **La même grille que celle de l'Assemblée**, remplie des séances à venir au
   Sénat. Il n'y en a que quelques-unes, et c'est normal : le Sénat ne publie
   une séance qu'une fois inscrite à son ordre du jour. Le mois s'ouvre donc
   sur celui qui en porte, pas sur le mois en cours s'il est vide. */
async function ouvrirCalendrierSenat() {
  const f = ouvrirEcran();
  f.append(boutonRetour("", "Retour au fil"));
  f.append(el("h2", "fiche-titre", "Les séances à venir au Sénat"));
  f.append(el("p", "avertissement", "Chargement…"));

  const d = await lire("senat/calendrier.json");
  f.textContent = "";
  f.append(boutonRetour("", "Retour au fil"));
  f.append(el("h2", "fiche-titre", "Les séances à venir au Sénat"));
  const jours = (d && d.jours) || [];
  if (!jours.length) {
    f.append(el("div", "vide",
      "Aucune séance annoncée. Le Sénat ne publie une séance qu'une fois "
      + "inscrite à son ordre du jour, et le calendrier se vide pendant les "
      + "vacances parlementaires."));
    return;
  }

  // Un événement par texte inscrit, à plat : c'est la forme que la grille
  // attend, et elle n'a pas à connaître celle du fichier du Sénat.
  const evenements = [];
  for (const j of jours) {
    for (const t of j.textes) evenements.push({ ...t, date: j.date });
  }
  const mois = [...new Set(evenements.map((e) => moisDe(e.date)))].sort();

  f.append(el("p", "fiche-sous",
    `${nb.format(evenements.length)} séance${evenements.length > 1 ? "s" : ""} `
    + `annoncée${evenements.length > 1 ? "s" : ""}, sur `
    + `${nb.format(jours.length)} jour${jours.length > 1 ? "s" : ""}.`));
  const veille = avisDuSenat();
  if (veille) f.append(veille);

  const source = {
    mois: () => mois,
    charger: (m) => evenements.filter((e) => moisDe(e.date) === m),
    ligne: (e) => ligneSeanceSenat(e),
    vide: "Aucune séance ce mois-ci. Le Sénat ne publie une séance qu'une "
        + "fois inscrite à son ordre du jour.",
  };

  // Le mois en cours s'il porte quelque chose, sinon le premier qui en porte :
  // une grille vide au premier regard ne dit pas où aller.
  MOIS_VU = mois.includes(moisDe(aujourdhui())) ? moisDe(aujourdhui()) : mois[0];
  JOUR_VU = null;
  const zone = el("div");
  f.append(zone);
  await dessinerMois(zone, source);
}

async function dessinerMois(zone, source) {
  const evenements = await source.charger(MOIS_VU);
  const connus = source.mois();
  zone.textContent = "";

  zone.append(barreDesMois(zone, source, connus));

  const parJour = new Map();
  for (const e of evenements) {
    if (!parJour.has(e.date)) parJour.set(e.date, []);
    parJour.get(e.date).push(e);
  }

  // Le jour choisi se décide **avant** de dessiner la grille : sinon la case
  // du jour ne serait pas marquée, la grille ayant été construite avant de
  // savoir lequel montrer.
  //
  // **Et il doit porter quelque chose dans *ce* calendrier.** Les deux
  // chambres partagent `JOUR_VU` : passer du calendrier du Sénat à celui de
  // l'Assemblée gardait un jour chargé au Sénat et vide à l'Assemblée, qui
  // rendait une liste vide sous une grille pleine.
  if (evenements.length
      && (!JOUR_VU || moisDe(JOUR_VU) !== MOIS_VU || !parJour.has(JOUR_VU))) {
    // Aujourd'hui s'il porte quelque chose, sinon le premier jour du mois qui
    // en porte.
    JOUR_VU = parJour.has(aujourdhui()) ? aujourdhui() : [...parJour.keys()].sort()[0];
  }
  zone.append(grilleDuMois(parJour, zone, source));

  if (!evenements.length) {
    zone.append(el("div", "vide", source.vide));
    return;
  }
  zone.append(listeDuJour(parJour.get(JOUR_VU) || [], source));
}

/* Le mois d'avant ou d'après : le jour choisi ne vaut plus, la grille se
   redessine. */
async function allerAuMoisVoisin(zone, source, pas) {
  MOIS_VU = moisVoisin(MOIS_VU, pas);
  JOUR_VU = null;
  await dessinerMois(zone, source);
}
