/* Ouvrir ce qu'une loi change et la fiche d'un article, charger la liste des articles à l'ouverture de l'onglet, changer de lecture. */

async function ouvrirChangements(uid) {
  const f = ouvrirEcran();
  const retour = boutonRetour("#/texte/" + uid, "Retour au texte");
  f.append(retour);
  f.append(el("p", "avertissement", "Chargement…"));

  let d;
  try {
    d = await lire(`changements/${uid}.json`, true);
  } catch (e) {
    f.textContent = "";
    f.append(retour, el("div", "vide", "Détail indisponible : " + e.message));
    return;
  }
  f.textContent = "";
  f.append(retour);

  const texte = TEXTES.find((x) => x.uid === uid);
  f.append(el("h2", "fiche-titre", texte ? texte.titre : "Ce que cette loi change"));
  const ajouts = d.articlesAjoutes || [];
  const sous = el("p", "fiche-sous",
    (d.loi ? "LOI n° " + d.loi + " — " : "")
    + (ajouts.length ? "ce qu'elle change au droit, et ce qu'elle y ajoute."
                     : "ce qu'elle change au droit."));
  f.append(sous);
  f.append(...contenuDesChangements(uid, d));
}

/* La liste des articles, demandée à l'ouverture de l'onglet « Articles »,
   pas à celle de la fiche. */
async function chargerLesChangements(uid, b, attente) {
  let d;
  try {
    d = await lire(`changements/${uid}.json`, true);
  } catch (e) {
    attente.replaceWith(el("div", "vide", "Détail indisponible : " + e.message));
    return;
  }
  attente.remove();
  b.append(...contenuDesChangements(uid, d));
}

async function ouvrirArticle(uid, identifiant) {
  const f = ouvrirEcran();
  const retour = boutonRetour("#/change/" + uid, "Tous les articles");
  f.append(retour);
  f.append(el("p", "avertissement", "Chargement…"));

  let a;
  try {
    a = await lire(`changements/${uid}/${identifiant}.json`, true);
  } catch (e) {
    f.textContent = "";
    f.append(retour, el("div", "vide", "Article indisponible : " + e.message));
    return;
  }
  dessinerArticle(f, retour, uid, a);
}

/* Changer de lecture d'un article : ce qui change, le texte en vigueur, le
   texte précédent. */
function choisirLeMode(cle, f, retour, uid, a) {
  MODE_TEXTE = cle;
  dessinerArticle(f, retour, uid, a);
  window.scrollTo(0, 0);
}
