/* Ce qui se dit d'un texte : les amendements de l'onglet, les prises de parole mot pour mot, et le résumé écrit hors ligne. */

function carteAmendement(a) {
  const c = el("article", "amdt");
  const tete = el("div", "tete");
  tete.append(el("span", "num", a.numero || "—"));
  if (a.article) tete.append(el("span", null, a.article));
  if (a.sort) {
    tete.append(el("span", "sort " + (SORTS_AMDT[a.sort] || ""), a.sort));
  }
  if (a.sigle) {
    const g = el("span", "grp");
    const teinte = el("i");
    if (a.couleur) teinte.style.background = a.couleur;
    g.append(teinte);
    g.append(document.createTextNode(a.sigle));
    tete.append(g);
  }
  if (a.nom) tete.append(el("span", null, [a.prenom, a.nom].filter(Boolean).join(" ")));
  c.append(tete);

  const disp = el("p", "disp");
  for (const m of a.morceaux || []) {
    if (m.role === "neutre") disp.append(document.createTextNode(m.texte));
    else {
      const marque = el("span", m.role, "« " + m.texte + " »");
      disp.append(marque);
    }
  }
  c.append(disp);
  if (a.expose) {
    c.append(el("p", "expose", a.expose + (a.exposeTronque ? "" : "")));
  }
  return c;
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

/* ---------- ce que les groupes en ont dit ---------- */

/* Une prise de parole, telle que le compte rendu de séance la publie. **Rien
   n'est résumé ni reformulé** : le texte affiché est celui de la source, et
   le repliement est une affaire de hauteur d'écran, pas de contenu — le
   paragraphe entier est dans la page dès le premier affichage. */
function carteParole(p) {
  const c = el("article", "parole");
  if (p.couleur) c.style.borderLeftColor = p.couleur;

  const tete = el("div", "tete");
  tete.append(el("span", "qui", p.nom || "—"));
  if (p.sigle) {
    const g = el("span", "grp");
    const teinte = el("i");
    if (p.couleur) teinte.style.background = p.couleur;
    g.append(teinte);
    g.append(document.createTextNode(p.sigle));
    tete.append(g);
  }
  if (p.qualite) tete.append(el("span", null, p.qualite));
  tete.append(el("span", "quand",
                 `${dateCourte.format(enDate(p.date))} · ${p.section}`));
  c.append(tete);

  const dit = el("p", "dit replie", p.texte);
  c.append(dit);
  // Le bouton n'apparaît que si le texte dépasse vraiment : sur une parole
  // courte, « Lire la suite » ne mènerait nulle part.
  const plus = el("button", "plus", "Lire la suite");
  c.append(plus);
  requestAnimationFrame(() => {
    if (dit.scrollHeight <= dit.clientHeight + 2) plus.remove();
  });
  plus.addEventListener("click", () => {
    const replie = dit.classList.toggle("replie");
    plus.textContent = replie ? "Lire la suite" : "Replier";
  });
  return c;
}

/* ---------- l'onglet « Texte » ---------- *
 * Le contenu réel d'un projet ou d'une proposition de loi, que la fiche ne
 * montrait nulle part : il n'existait qu'au fond du parcours, une version à la
 * fois. Trois choses ici, et pas une de plus :
 *
 *   — le texte **déposé**, celui qu'on a voulu faire voter ;
 *   — ce que la **dernière version** a changé, différences comprises ;
 *   — cette dernière version **à jour**, sans les différences, telle qu'elle
 *     se lit aujourd'hui.
 *
 * Chaque partie se charge à la demande : une version pèse jusqu'à 2,8 Mo
 * (mesuré le 2026-09-19 sur le projet de loi de finances pour 2026), et
 * personne n'ouvre les trois à la fois. Quand le socle n'a lu aucune
 * version — les textes déposés au Sénat, qui publie ses documents ailleurs —
 * l'onglet le dit au lieu d'afficher un cadre vide.
 * ------------------------------------------------------------------ */

/* Les articles sur lesquels une liste d'amendements a un sens : ceux qui ont
   bougé. Un article inchangé n'a pas d'amendement adopté par définition, et
   lui afficher « la source ne relie ce changement à aucun amendement »
   nommerait un changement qui n'a pas eu lieu. Un article initial non plus :
   la version déposée ne vient d'aucun amendement. */
const A_CHANGE = new Set(["modifie", "nouveau", "retire"]);

/* Un groupe et ses arguments, sous sa couleur. */
function carteDuGroupe(g) {
  const carte = el("div", "groupe-dit");
  const tete = el("div", "qui");
  const teinte = el("i");
  const connu = GROUPES.get(g.sigle);
  if (connu?.couleur) teinte.style.background = connu.couleur;
  tete.append(teinte, el("b", null, g.sigle));
  if (connu?.nom) tete.append(el("span", null, connu.nom));
  carte.append(tete);
  const liste = el("ul");
  for (const a of g.arguments) liste.append(el("li", null, a));
  carte.append(liste);
  return carte;
}

function carteDOrateur(o) {
  const carte = el("div", "groupe-dit");
  const tete = el("div", "qui");
  tete.append(el("b", null, o.nom));
  carte.append(tete);
  const liste = el("ul");
  for (const a of o.arguments) liste.append(el("li", null, a));
  carte.append(liste);
  return carte;
}

/* Les camps dans cet ordre, puis les groupes que le scrutin ne nomme pas. */
function campsDuResume(resume) {
  const zones = [];
  const camps = [["pour", []], ["contre", []], ["abstention", []],
                 ["partagé", []], ["aucun_vote", []], [null, []]];
  for (const g of resume.groupes) {
    (camps.find(([nom]) => nom === (g.position || null)) || camps[5])[1].push(g);
  }
  for (const [nom, groupes] of camps) {
    if (!groupes.length) continue;
    const zone = el("div", "camp " + (nom ? nom.replace("é", "e") : "sans-vote"));
    // Sans position et sans scrutin, il n'y a rien à annoncer qu'une parole.
    // Sans position mais avec un scrutin, le groupe n'y figure pas : le dire
    // ainsi, plutôt que de le ranger parmi ceux qui n'ont pas voté.
    zone.append(el("h5", null, nom ? CAMPS[nom]
      : (resume.vote ? "Groupes absents de ce scrutin" : "Ce qui a été dit")));
    for (const g of groupes) zone.append(carteDuGroupe(g));
    zones.push(zone);
  }
  return zones;
}

/* Les orateurs que la source n'a rattachés à aucun groupe : un ministre, un
   non-inscrit. **Ils viennent après les camps, jamais dedans** — un ministre
   n'est pas député, il ne vote pas, il n'a donc pas de camp. Les afficher
   sous un sigle inventé ferait dire à un groupe ce qu'il n'a pas dit. */
function blocDesOrateurs(orateurs) {
  const zone = el("div", "camp orateurs");
  zone.append(el("h5", null, "Dit aussi en séance"));
  // La mention une fois pour toutes, sous le titre : répétée sur chaque
  // carte, elle tenait sur la ligne d'un nom court et passait à la ligne
  // sur un nom long, ce qui donnait deux mises en page pour une même chose.
  zone.append(el("p", "pourquoi-orateurs",
    "Le compte rendu ne rattache ces orateurs à aucun groupe : ce sont des "
    + "membres du gouvernement ou des députés sans groupe. Ils ne votent "
    + "donc pas dans les camps ci-dessus."));
  for (const o of orateurs) zone.append(carteDOrateur(o));
  return zone;
}

function blocResumeDebats(resume) {
  const boite = el("div", "description resume-debats");
  const origine = ORIGINE_RESUME[resume.origine] || ORIGINE_RESUME.ia;

  if (resume.vote) {
    const quand = resume.vote.date
      ? dateLongue.format(enDate(resume.vote.date)) : null;
    const ligne = el("p", "sur-quel-vote");
    ligne.append(document.createTextNode("Groupes rangés d'après le scrutin"
      + (quand ? " du " + quand : "") + " sur l'ensemble du texte"));
    if (resume.vote.sort) ligne.append(el("b", null, " — " + resume.vote.sort));
    boite.append(ligne);
  } else {
    boite.append(el("p", "sur-quel-vote",
      "Aucun scrutin public sur l'ensemble de ce texte : les groupes sont "
      + "rangés comme dans l'hémicycle, de la gauche à la droite."));
  }

  for (const zone of campsDuResume(resume)) boite.append(zone);

  if ((resume.orateurs || []).length) boite.append(blocDesOrateurs(resume.orateurs));

  boite.append(boutonOrigine(resume.origine, origine, resume.le, resume.modele, "écrit"));
  return boite;
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

/* ---------- la description du texte ---------- *
 * Écrite, et non recopiée : c'est la seule rubrique de l'application dans ce
 * cas. Une phrase d'accroche, puis une puce par mesure concrète — un pavé de
 * six lignes se saute, une liste se parcourt.
 *
 * Elle porte son origine à l'écran, en toutes lettres — une icône,
 * un mot, et l'explication complète au toucher. Le `title` sert l'ordinateur,
 * où le survol existe ; le bouton sert le téléphone, où il n'existe pas. Les
 * deux disent la même chose : sans le bouton, la mention serait invisible sur
 * la moitié des écrans.
 * ------------------------------------------------------------------ */

// Combien de mesures s'affichent avant qu'il faille les demander.
const VISIBLES = 3;

const ORIGINES = {
  ia: {
    mot: "Description générée par une intelligence artificielle",
    court: "Générée par une IA",
    titre: "Cette description est générée par une IA",
    quoi: "Elle ne vient pas de l'Assemblée nationale : le contexte, la phrase " +
      "d'accroche et les mesures ont été écrits par une intelligence " +
      "artificielle à partir du titre du texte, de ce que la " +
      "loi change au droit et de ce qui a été dit en séance — jamais d'autre " +
      "chose. Elle peut donc se tromper ou vieillir. Tout le reste " +
      "de la fiche — le titre, le parcours, les votes, les prises de parole, le " +
      "texte des articles — est recopié de la source, mot pour mot.",
  },
  humain: {
    mot: "Description écrite par une personne",
    court: "Écrite par une personne",
    titre: "Cette description est écrite par une personne",
    quoi: "Elle ne vient pas de l'Assemblée nationale : c'est une présentation " +
      "rédigée pour cette application. Tout le reste de la fiche — le titre, le " +
      "parcours, les votes, les prises de parole, le texte des articles — est " +
      "recopié de la source, mot pour mot.",
  },
};

// L'icône de l'origine : une étincelle pour l'IA, une silhouette pour une
// personne. Dessinée ici plutôt qu'écrite en emoji, dont le rendu change d'un
// téléphone à l'autre.
