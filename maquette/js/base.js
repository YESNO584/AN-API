/* Le vocabulaire et les aides que tout le reste emploie : les étapes des deux chambres, les explications au toucher, les formats de date, la recherche sans accent, les vues et ce qu'elles déclarent. */

// D'où viennent les données.
//
// Par défaut : à côté de la page. La maquette est publiée au même endroit
// que les fichiers du socle, donc une adresse relative marche partout — en
// ligne, en local, ou depuis un dossier copié ailleurs.
//
// `?socle=http://…` vise un autre socle : utile pour essayer une
// modification avant de la publier, ou pour ouvrir la page depuis un fichier
// (`file://`), où il n'y a rien à côté d'elle.
const SOCLE = new URLSearchParams(location.search).get("socle")
           || (location.protocol === "file:" ? "https://yesno584.github.io/AN-API" : ".");
const PAR_PAQUET = 25;

/* ------------------------------------------------------------------ *
 * Les explications. C'est le cœur de cette maquette : chaque élément
 * affiché doit pouvoir dire, en français simple, ce qu'il est.
 * ------------------------------------------------------------------ */
const PROMULGUEE = 7;
const ARRETE = 0;

// Comment nommer l'issue d'un texte. **Aucune de ces phrases ne dit qu'un
// texte est fini pour de bon** : les sources ne le disent pas, la page non
// plus. Un texte rejeté ou non adopté peut être redéposé.
const ISSUES = {
  rejete: ["Rejeté",
    "La dernière décision connue sur ce texte est un rejet. Cela ne veut pas dire " +
    "qu'il ne reviendra jamais : un texte rejeté peut être redéposé, et la source " +
    "ne se prononce pas là-dessus."],
  non_adopte: ["Non adopté",
    "Le Sénat indique que ce texte n'a pas été adopté. C'est son propre mot. Un " +
    "texte non adopté peut être redéposé ; rien dans les données ne dit s'il le sera."],
  caduc: ["Caduc",
    "Le Sénat indique que ce texte est caduc : il n'a pas abouti avant la fin de la " +
    "période où il pouvait être examiné. Pour repartir, il devrait être déposé à nouveau."],
  retire: ["Retiré",
    "Le texte a été retiré par celui qui l'avait déposé. Ce n'est ni un rejet ni un " +
    "échec de vote : son auteur a choisi de l'enlever."],
};

/* Les étapes **propres au Sénat**. Elles ne correspondent pas une à une à
   celles de l'Assemblée, et on ne les aligne pas : les deux chambres ne
   découpent pas le parcours pareil, et les faire correspondre inventerait un
   découpage que personne ne publie. Les règles de lecture, elles, vivent dans
   `socle/extraction.py` — ici c'est la formulation à l'écran. */
const ETAPES_SENAT = [
  { cle: "depot", nom: "Déposé au Sénat", quoi:
    "Le texte vient d'arriver au Sénat, en navette depuis l'Assemblée ou déposé " +
    "là directement. Personne ne l'y a encore examiné." },
  { cle: "commission", nom: "Renvoyé en commission", quoi:
    "Une commission du Sénat en est saisie. C'est de très loin le cas le plus " +
    "fréquent : la plupart des textes attendent là, parfois des années." },
  { cle: "rapport", nom: "Rapport déposé", quoi:
    "La commission a rendu son rapport et sa propre version du texte. La séance " +
    "publique peut être inscrite à l'ordre du jour." },
  { cle: "seance", nom: "En séance publique", quoi:
    "Le Sénat en débat en séance. Cette étape est brève : elle s'achève le jour " +
    "même par une décision, et c'est pourquoi la colonne est presque toujours vide." },
  { cle: "decision", nom: "Décidé", quoi:
    "Le Sénat s'est prononcé — adopté, modifié ou rejeté. Ce qui arrive ensuite " +
    "ne lui appartient plus : la navette, la commission mixte paritaire et la " +
    "promulgation se jouent ailleurs. La carte dit où le texte en est arrivé." },
];

const ETAPES = [
  { n: ARRETE, nom: "Arrêté en chemin", quoi:
    "Ces textes ne sont plus examinés : rejetés, non adoptés, retirés par leur " +
    "auteur, ou devenus caducs. Chacun porte le mot de sa source. Rien n'interdit " +
    "qu'un texte semblable soit redéposé plus tard." },
  { n: PROMULGUEE, nom: "Promulguée", quoi:
    "Le parcours est terminé : le texte est devenu une loi. Il a été signé par " +
    "le Président de la République et publié au Journal officiel. C'est à partir " +
    "de ce moment-là qu'il s'applique." },
  { n: 1, nom: "Dépôt", quoi:
    "Le texte vient d'être déposé au Parlement et confié à une commission, mais " +
    "personne ne l'a encore examiné. C'est le cas de la grande majorité des textes : " +
    "la plupart n'iront jamais plus loin." },
  { n: 2, nom: "Commission", quoi:
    "Une commission — un groupe restreint de parlementaires spécialisés — étudie le " +
    "texte, le modifie, et rédige sa propre version avant le débat public." },
  { n: 3, nom: "Séance publique", quoi:
    "Le texte est débattu dans l'hémicycle, devant tous les parlementaires. Ils le " +
    "modifient encore, puis votent sur l'ensemble." },
  { n: 4, nom: "Navette", quoi:
    "Le texte a été adopté par une chambre et envoyé à l'autre, qui reprend tout " +
    "depuis le début. Si elle le modifie, il repart à la première. Cet aller-retour " +
    "peut se répéter plusieurs fois — d'où le nom de « navette »." },
  { n: 5, nom: "Sortie de navette", quoi:
    "Les deux chambres n'arrivent pas à se mettre d'accord. Sept députés et sept " +
    "sénateurs se réunissent pour tenter un compromis (la « commission mixte " +
    "paritaire »). En cas d'échec, le Gouvernement peut donner le dernier mot à " +
    "l'Assemblée nationale." },
  { n: 6, nom: "Après le vote", quoi:
    "Le texte est voté. Avant de devenir une loi applicable, il peut être soumis au " +
    "Conseil constitutionnel, qui vérifie qu'il respecte la Constitution. Ensuite " +
    "seulement, le Président le promulgue." },
];

const TYPES = {
  "Proposition de loi ordinaire": ["Proposition de loi",
    "Un texte écrit et déposé par des parlementaires eux-mêmes, et non par le " +
    "Gouvernement. Elles sont très nombreuses, et peu aboutissent."],
  "Projet de loi ordinaire": ["Projet de loi",
    "Un texte déposé par le Gouvernement. Il a beaucoup plus de chances d'aboutir " +
    "qu'une proposition, parce que c'est le Gouvernement qui décide de l'ordre du jour."],
  "Projet ou proposition de loi constitutionnelle": ["Loi constitutionnelle",
    "Un texte qui modifie la Constitution elle-même. La procédure est plus exigeante : " +
    "il faut un vote identique des deux chambres, puis un référendum ou un vote du " +
    "Parlement réuni en Congrès."],
  "Projet ou proposition de loi organique": ["Loi organique",
    "Un texte qui précise le fonctionnement des institutions prévues par la " +
    "Constitution. Il se situe entre la Constitution et une loi ordinaire, et le " +
    "Conseil constitutionnel doit obligatoirement le contrôler."],
  "Projet de ratification des traités et conventions": ["Ratification d'un traité",
    "Un texte par lequel la France approuve officiellement un accord signé avec " +
    "d'autres pays ou des organisations internationales."],
  "Projet de loi de finances de l'année": ["Budget de l'État",
    "Le texte qui fixe les recettes et les dépenses de l'État pour l'année. Son " +
    "examen suit un calendrier contraint à l'automne."],
  "Projet de loi de finances rectificative": ["Budget rectifié",
    "Un texte qui corrige en cours d'année le budget déjà voté."],
  "Projet de loi de financement de la sécurité sociale": ["Budget de la Sécurité sociale",
    "Le texte qui fixe chaque année les recettes et les dépenses de la Sécurité sociale."],
  "Projet de loi relative aux résultats de la gestion et portant approbation des comptes":
    ["Approbation des comptes",
     "Le texte par lequel le Parlement constate comment le budget de l'année écoulée " +
     "a réellement été exécuté."],
  "Proposition de loi présentée en application de l'article 11 de la Constitution":
    ["Proposition d'initiative partagée",
     "Une proposition portée par des parlementaires et soutenue par des citoyens, " +
     "selon une procédure rare prévue par l'article 11 de la Constitution."],
};

const CHAMBRES = {
  assemblee: ["Assemblée nationale",
    "Les 577 députés, élus directement par les citoyens pour cinq ans. En cas de " +
    "désaccord persistant avec le Sénat, c'est elle qui a le dernier mot."],
  senat: ["Sénat",
    "Les 348 sénateurs, élus non par les citoyens directement mais par les élus " +
    "locaux. Le Sénat examine tous les textes, mais ne peut pas imposer sa position " +
    "à l'Assemblée."],
  null: ["Les deux chambres",
    "L'étape en cours réunit des députés et des sénateurs — c'est le cas d'une " +
    "commission mixte paritaire — ou se déroule hors du Parlement, comme un " +
    "contrôle du Conseil constitutionnel."],
};

const EXPLICATIONS = {
  lecture: ["De quelle lecture il s'agit",
    "Un même texte peut être examiné plusieurs fois par la même chambre. On appelle " +
    "chaque passage une « lecture » : première lecture, deuxième lecture, et ainsi de " +
    "suite jusqu'à l'accord."],
  acte: ["Ce qui vient de se passer",
    "Le dernier événement enregistré pour ce texte : un dépôt, la nomination d'un " +
    "rapporteur, une réunion de commission, un débat en séance, un vote…"],
  date: ["La date du dernier mouvement",
    "Le jour du dernier événement connu. Si elle est ancienne, le texte est à " +
    "l'arrêt — ce qui est le sort de la plupart d'entre eux."],
  dormant: ["Un texte à l'arrêt",
    "Rien ne s'est passé sur ce texte depuis longtemps. Ce n'est pas un rejet : il " +
    "n'a simplement jamais été inscrit à l'ordre du jour, et ne le sera probablement " +
    "jamais."],
  precision: ["Ce qui distingue cette étape d'une autre du même jour",
    "Une chambre peut siéger plusieurs fois dans la journée : une commission le " +
    "matin puis l'après-midi, une première puis une deuxième séance publique. " +
    "Sans cette mention, les deux lignes seraient identiques et passeraient pour " +
    "une erreur."],
  conclusion: ["Le résultat du vote",
    "Ce que la chambre a décidé à l'issue de son examen : adopté, rejeté, ou adopté " +
    "avec des modifications qui obligent le texte à repartir vers l'autre chambre."],
  vote: ["Un vote enregistré",
    "Un « scrutin public » : chaque parlementaire vote nominativement et le " +
    "détail est publié. C'est rare — la plupart des textes sont adoptés à main " +
    "levée, sans que le vote de chacun soit enregistré. Sur les textes en cours, " +
    "moins d'un sur vingt en a un."],
  voteEnsemble: ["Le vote sur le texte entier",
    "La chambre s'est prononcée sur l'ensemble du texte. C'est ce vote-là qui " +
    "décide si le texte poursuit son chemin ou s'arrête. Touchez-le pour voir " +
    "comment chaque groupe politique a voté."],
  votesAmendements: ["Des votes sur des détails",
    "Ces votes portent sur des amendements ou des articles, pas sur le texte " +
    "entier. Un texte débattu peut en compter des centaines. Ils disent comment " +
    "le texte a été façonné, pas s'il a été adopté."],
  aucunVote: ["Aucun vote public à venir n'est annoncé",
    "L'Assemblée ne publie pas ses votes à l'avance : un vote n'apparaît dans " +
    "les données qu'une fois qu'il a eu lieu. Ce qui est connu à l'avance, ce " +
    "sont seulement les séances déjà programmées."],
  prochaine: ["Une séance déjà programmée",
    "Le Parlement a inscrit ce texte à son calendrier. C'est la seule information " +
    "tournée vers l'avenir : tout le reste décrit ce qui a déjà eu lieu."],
  frise: ["Le parcours du texte",
    "Les six étapes qu'un texte doit franchir pour devenir une loi. Le trait coloré " +
    "montre où il en est ; les traits plus sombres, les étapes déjà passées."],
  theme: ["Le sujet d'un texte",
    "Le classement est celui du Sénat, repris tel quel : c'est le seul des " +
    "deux à en publier un. Un texte en porte deux en moyenne, et la carte " +
    "n'en montre que le premier — toucher cette étiquette les donne tous. " +
    "Deux textes sur trois n'ont aucun sujet : ils ne sont jamais allés au " +
    "Sénat."],
  lectureSenat: ["La lecture au Sénat",
    "Un texte peut repasser plusieurs fois devant la même chambre : première " +
    "lecture, deuxième lecture, puis nouvelle lecture après une commission " +
    "mixte paritaire. Chaque lecture recommence les mêmes étapes."],
  conclusionSenat: ["Ce que le Sénat a décidé",
    "Le mot est celui de la source, repris tel quel : adopté, modifié, " +
    "rejeté. Il dit ce que le Sénat a fait du texte à cette étape, et rien " +
    "de ce qui lui est arrivé ensuite."],
  dateSenat: ["La date de la dernière étape au Sénat",
    "Elle ne dit rien de ce qui se passe à l'Assemblée au même moment : les " +
    "deux chambres avancent chacune de son côté, et la fiche du texte montre " +
    "le parcours entier."],
  voteSenat: ["Un scrutin public au Sénat",
    "Le Sénat vote, lui aussi, et publie qui a voté quoi. Ces chiffres sont " +
    "les siens : ils ne s'additionnent pas à ceux de l'Assemblée et ne se " +
    "comparent pas à eux — les deux chambres ne votent ni sur le même texte, " +
    "ni au même moment, ni avec le même nombre de sièges. Le rattachement du " +
    "scrutin à ce texte vient du Sénat lui-même, qui le publie sur ses pages " +
    "de scrutins publics."],
  compositionSenat: ["L'ordre des groupes du Sénat",
    "Il est mesuré, mais pas comme à l'Assemblée. Là-bas, les numéros de " +
    "sièges rangent les groupes de la gauche à la droite. Au Sénat, ils ne le " +
    "font pas : la numérotation tourne rang par rang. Le Sénat publie pourtant " +
    "le siège de chacun — et en le suivant, le groupe change 152 fois, contre " +
    "9 à l'Assemblée : un groupe occupe des sièges d'un bout à l'autre de la " +
    "salle. L'ordre affiché est donc mesuré sur autre chose : la façon dont " +
    "les groupes votent, sur les scrutins où ils se séparent. Il distingue " +
    "nettement la gauche, le centre et la droite. Il ne départage pas les " +
    "groupes d'un même bloc, et le sens — quel bout est la gauche — est une " +
    "convention assumée. Les couleurs, elles, ne sont pas de nous : ce sont " +
    "celles que le Sénat donne à ses groupes."],
  friseSenat: ["Le parcours au Sénat",
    "Ces colonnes sont les étapes que le Sénat nomme lui-même, et elles ne " +
    "correspondent pas une à une à celles de l'Assemblée : les deux chambres " +
    "ne découpent pas le parcours pareil, et les aligner inventerait un " +
    "découpage que personne ne publie. Un texte est dans la colonne de sa " +
    "dernière étape au Sénat. Ce qui lui arrive ensuite — la navette, la " +
    "commission mixte paritaire, la promulgation — se joue ailleurs, et c'est " +
    "la carte qui le dit."],
  travaux: ["Les travaux de l'Assemblée",
    "Ces dossiers n'aboutissent à aucune loi : ce sont des enquêtes, des rapports, " +
    "des prises de position et des motions. Ils sont ici pour que rien ne soit " +
    "écarté. Ils ne traversent pas les six étapes d'un texte de loi : chaque " +
    "colonne est une catégorie, pas une étape."],
  change: ["Ce que la loi change au droit",
    "La comparaison entre l'article de loi tel qu'il était et tel qu'il est " +
    "devenu. Elle est calculée mot à mot à partir du texte officiel publié par " +
    "la Direction de l'information légale et administrative — rien n'est " +
    "reformulé ni résumé."],
  hemicycle: ["Ce dessin est une convention",
    "L'Assemblée publie le numéro du siège de chaque député — 576 sur 577 en " +
    "ont un, et c'est la même numérotation que celle des scrutins, sur " +
    "laquelle l'ordre des groupes est calculé. Ce qu'elle ne publie pas, " +
    "c'est où se trouve ce siège dans la salle. Le dessin place donc les " +
    "sièges de la gauche à la droite dans l'ordre des groupes, sans " +
    "prétendre à un plan de salle : les proportions et l'ordre sont justes, " +
    "la position d'un siège dans le dessin est une convention. Les couleurs " +
    "aussi.\n\nLe bouton « groupe / siège », en haut du dessin, change ce qui " +
    "est dessiné. « Par groupe » regroupe les députés d'un même groupe : des " +
    "blocs nets, et la place du groupe vient de son siège médian. « Par " +
    "siège » place chaque député à son propre numéro : les groupes y " +
    "apparaissent parfois mêlés, et c'est la réalité. Ainsi LIOT occupe les " +
    "sièges 382 à 483 et SOC les sièges 409 à 569 : il n'y a pas de frontière " +
    "entre eux, et aucun ordre ne peut en inventer une.\n\nD'où une limite du " +
    "mode « par groupe », qui vaut d'être connue : la place d'un petit groupe " +
    "dispersé y est approximative. Les onze non-inscrits, par exemple, " +
    "occupent les sièges 111 à 422 — d'un bout à l'autre de la salle, " +
    "puisqu'aucun groupe ne leur réserve de zone. Le dessin par groupe les " +
    "montre pourtant côte à côte.\n\nLe compte « 30 F / 41 H » d'un groupe est fait à l'affichage, " +
    "en lisant la civilité que la source imprime devant chaque nom — « Mme » " +
    "ou « M. ». L'open data ne publie rien d'autre là-dessus, et nous " +
    "n'ajoutons rien : ce qui est compté est ce qui est écrit."],
  deputes: ["Les députés du groupe",
    "Civilité, prénom, nom, département et numéro de circonscription sont " +
    "recopiés de l'open data de l'Assemblée, mot pour mot. Deux choses sont " +
    "de nous, et elles ne portent que sur la forme : le classement par nom " +
    "— la source ne classe pas — et l'écriture « 1re circonscription », que " +
    "la source donne comme un simple numéro."],
  senateurs: ["Les sénateurs du groupe",
    "Civilité, prénom, nom et département sont recopiés de l'open data du " +
    "Sénat, mot pour mot. Le classement par nom est de nous — la source ne " +
    "classe pas. **Il n'y a pas de photographies** : les mentions légales du " +
    "Sénat les couvrent par le droit d'auteur, contrairement aux travaux " +
    "parlementaires, qui sont libres."],
  procedureAcceleree: ["La procédure accélérée",
    "Le gouvernement a engagé la procédure accélérée sur ce texte. Concrètement, " +
    "le texte ne fait qu'une lecture dans chaque chambre avant qu'une commission " +
    "mixte paritaire — sept députés, sept sénateurs — tente d'écrire une version " +
    "commune. Sans elle, le texte ferait des allers-retours entre les deux " +
    "chambres jusqu'à ce qu'elles s'accordent. La date est celle que la source " +
    "donne à cet acte du parcours."],
  amendementDebattu: ["Un amendement adopté de justesse, après un long échange",
    "Deux choses sont comptées, séparément. Le vote : ce scrutin public s'est " +
    "joué à moins de 10 % d'écart entre les voix pour et les voix contre. Le " +
    "débat : au moins huit personnes ont pris la parole sur cet amendement en " +
    "séance. Aucune des deux ne dit l'autre — sur les 967 amendements où l'on " +
    "connaît les deux, un long débat n'annonce pas un vote serré, ni " +
    "l'inverse. Un amendement sans ce repère n'est pas pour autant passé sans " +
    "discussion : 97 % des amendements adoptés le sont à main levée, sans " +
    "qu'aucun décompte de voix soit enregistré."],
  vigueur: ["L'entrée en vigueur",
    "Une loi promulguée ne s'applique pas forcément tout de suite, ni en une " +
    "seule fois : certains de ses articles peuvent n'entrer en vigueur que " +
    "plus tard. Les dates affichées sont celles que porte le texte officiel."],
};

/* ------------------------------------------------------------------ */

let TEXTES = [];
let GROUPES = new Map();
let ETAT = {};
const filtres = { etapes: new Set(), etapesSenat: new Set(),
                  chambres: new Set(), types: new Set(), themes: new Set(),
                  activite: null, programme: false, vote: null, etat: null, mots: "" };

const nb = new Intl.NumberFormat("fr-FR");
const _dateCourte = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short", year: "numeric" });
const _dateLongue = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "long", year: "numeric" });
/* En français, le premier jour du mois s'écrit « 1er ». Le navigateur écrit
   « 1 janvier », qui se lit mal — et les dates d'entrée en vigueur tombent
   presque toujours un premier. */
// Le « 1 » n'est pas toujours en tête : « lundi 1 juin » le porte au milieu.
// On remplace donc le premier « 1 » isolé, quelle que soit sa place.
const premier = (rendu, d) => d.getDate() === 1 ? rendu.replace(/\b1\b/, "1er") : rendu;
const dateCourte = { format: (d) => premier(_dateCourte.format(d), d) };
const dateLongue = { format: (d) => premier(_dateLongue.format(d), d) };

/* Une archive facultative qui n'arrive pas ne vide plus la base : les données
   de la veille restent en place. Encore faut-il le dire — sans quoi la page se
   donnerait pour plus fraîche qu'elle n'est. `vuLe` est l'horodatage du dernier
   téléchargement réussi de l'archive, et `genereLe` celui de la publication du
   matin : quand les deux jours diffèrent, ce qu'on affiche date d'avant. */
function avisDeVeille(vuLe, quoi, poids) {
  if (!vuLe || !ETAT.genereLe) return null;
  const jour = (iso) => String(iso).slice(0, 10);
  if (jour(vuLe) === jour(ETAT.genereLe)) return null;
  return el("p", "avertissement",
    `${quoi} datent du ${dateLongue.format(enDate(jour(vuLe)))} : leur archive `
    + `de ${poids} n'est pas arrivée entière depuis. Rien n'a été effacé, et `
    + `le reste de la fiche est à jour. La récupération est retentée chaque `
    + `matin.`);
}

/* Le même avis pour le Sénat, dont les données ne viennent pas d'une archive
   mais de quatre sources. **La page ne doit jamais se donner pour plus fraîche
   qu'elle n'est** : quand la reconstruction échoue, celles de la veille
   restent affichées, et il faut le dire. */
function avisDuSenat() {
  if (!ETAT.senatVuLe || !ETAT.genereLe) return null;
  const jour = (iso) => String(iso).slice(0, 10);
  if (jour(ETAT.senatVuLe) === jour(ETAT.genereLe)) return null;
  return el("p", "avertissement",
    `Les données du Sénat datent du `
    + `${dateLongue.format(enDate(jour(ETAT.senatVuLe)))} : ses sources n'ont `
    + `pas pu être relues depuis. Rien n'a été effacé, et le reste du site est `
    + `à jour. La récupération est retentée chaque matin.`);
}

// Les six étapes du parcours, pour la frise. « Promulguée » n'en fait pas
// partie : c'est l'après, pas une septième étape.
const PARCOURS = ETAPES.filter((e) => e.n !== PROMULGUEE && e.n !== ARRETE)
                       .sort((a, b) => a.n - b.n);
const etapeDe = (n) => ETAPES.find((e) => e.n === n);
/* L'ordre du fil, de la frise et des filtres, qui doivent tous dire la même
   chose : les textes arrêtés d'abord, puis les six étapes, puis la
   promulgation. Le fil se lit de gauche à droite, et le premier trait de la
   frise mène à la première colonne — sans quoi la frise mentirait sur le fil. */
const FRISE_EN_ORDRE = [etapeDe(ARRETE), ...PARCOURS, etapeDe(PROMULGUEE)]
                       .filter(Boolean);
const statutDe = (t) => t.statut || (t.etape === PROMULGUEE ? "promulgue" : "en_cours");

/* **La recherche doit être souple, parce que le clavier l'est.** « legitime »
   doit trouver « Légitime », « coeur » trouver « cœur », et « l'usage »
   trouver « l’usage » — la source écrit l'apostrophe typographique, qu'aucun
   clavier ne donne au premier coup. Trois transformations, dans cet ordre :
   les ligatures (que la décomposition Unicode ne défait pas), puis les
   accents, puis les apostrophes. */
const LIGATURES = [[/œ/g, "oe"], [/æ/g, "ae"], [/[’‘‛´`]/g, "'"]];
function normaliser(s) {
  let t = (s || "").toLowerCase();
  for (const [de, vers] of LIGATURES) t = t.replace(de, vers);
  return t.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

/* ---------- les deux onglets ---------- *
 * « Textes » : ce qui peut devenir une loi, rangé par étape du parcours.
 * « Travaux » : tout le reste — enquêtes, rapports, prises de position,
 * motions — rangé par catégorie. Ces dossiers n'aboutissent à aucune loi,
 * mais rien n'est écarté : ils ont leur onglet.
 *
 * Les deux se dessinent avec la même machinerie de colonnes. Chaque onglet
 * dit seulement ce qui le distingue : sa liste, la catégorie d'un élément,
 * l'ordre des colonnes, et la carte à dessiner.
 * ------------------------------------------------------------------ */
let ONGLET = "textes";
let SENAT = [];
let THEMES = [];
let TRAVAUX = [];
let CATEGORIES_TRAVAUX = [];

const VUES = {
  // À gauche des deux autres, parce que c'est l'autre chambre qu'on vient
  // chercher : le fil de l'Assemblée reste l'onglet par défaut.
  senat: {
    nom: "Sénat",
    base: () => SENAT,
    liste: () => retenus("senat"),
    total: () => SENAT.length,
    // Pas d'étape de l'Assemblée ici — l'onglet range sur celles du Sénat.
    // Pas de « Votes » non plus : les votes portés par la carte sont ceux de
    // l'Assemblée, et un filtre les donnerait pour des votes du Sénat.
    filtres: ["etapesSenat", "etat", "themes", "chambres", "types", "activite"],
    categorieDe: (t) => t.senat.moment,
    ordre: () => ETAPES_SENAT,
    cleDe: (e) => e.cle,
    carte: (t) => carte(t),
    // Les étapes du Sénat sont un parcours, comme celles de l'Assemblée : une
    // colonne est « derrière » la colonne ouverte. Les travaux, eux, ne se
    // traversent pas.
    parcours: true,
    // La colonne la plus avancée, comme pour les textes : c'est là que se
    // passe l'actualité du Sénat.
    ouverture: (categories) => Math.max(categories.length - 1, 0),
  },
  textes: {
    nom: "Textes",
    parcours: true,
    base: () => TEXTES,
    liste: () => retenus("textes"),
    total: () => TEXTES.length,
    filtres: ["etapes", "etat", "themes", "chambres", "types", "activite",
              "vote", "programme"],
    categorieDe: (t) => t.etape,
    ordre: () => FRISE_EN_ORDRE,
    cleDe: (e) => e.n,
    carte: (t) => carte(t),
    // La colonne la plus avancée : c'est là que se passe l'actualité.
    ouverture: (categories) => {
      for (let i = categories.length - 1; i >= 0; i--) {
        if (categories[i][0] !== ARRETE) return i;
      }
      return 0;
    },
  },
  travaux: {
    nom: "Travaux",
    parcours: false,
    base: () => TRAVAUX,
    liste: () => retenus("travaux"),
    total: () => TRAVAUX.length,
    // **Un travail n'a ni étape du parcours, ni vote, ni séance programmée,
    // ni sujet**, et le socle ne publie pas ces champs pour lui. Le sujet
    // surtout : mesuré le 2026-10-04, **aucun des 721 travaux n'a de dossier
    // au Sénat** — ce sont des résolutions, des commissions d'enquête, des
    // rapports, qui ne quittent jamais l'Assemblée. Un filtre « Sujet » y
    // serait vide à jamais. Un filtre qui ne trouve jamais rien ne s'affiche
    // pas.
    filtres: ["etat", "chambres", "types", "activite"],
    categorieDe: (t) => t.type,
    ordre: () => CATEGORIES_TRAVAUX,
    cleDe: (c) => c.nom,
    carte: (t) => carteTravail(t),
    ouverture: () => 0,
  },
};

const vue = () => VUES[ONGLET];

/* **Les filtres valent dans les trois onglets, et chacun n'affiche que les
   siens** (2026-10-04). Avant, le panneau ne servait que l'onglet « Textes » :
   chercher « santé » au Sénat ne donnait rien, puisque la recherche était
   cachée. Un filtre absent de la liste `filtres` d'une vue n'est **ni
   dessiné, ni appliqué, ni compté** dans le badge du bouton — les trois
   doivent dire la même chose, sinon le badge annonce un filtre que le fil
   ignore. */
const aLeFiltre = (nom, v = ONGLET) => VUES[v].filtres.includes(nom);
// La catégorie affichée, décrite : son nom, ce qu'elle est, son rang.
function categorieDite(cle) {
  const liste = vue().ordre();
  const trouve = liste.find((c) => vue().cleDe(c) === cle);
  return trouve || { nom: String(cle), quoi: "" };
}

const $ = (id) => document.getElementById(id);
const enDate = (iso) => { const [a, m, j] = iso.split("-").map(Number); return new Date(a, m - 1, j); };
const jours = (iso) => Math.floor((Date.now() - enDate(iso)) / 86400000);

function el(balise, classe, texte) {
  const n = document.createElement(balise);
  if (classe) n.className = classe;
  if (texte != null) n.textContent = texte;
  return n;
}

function typeCourt(t) { return (TYPES[t] || [t])[0]; }

function expliquer(titre, texte, valeur) {
  document.querySelectorAll(".info .groupes").forEach((n) => n.remove());
  $("info-titre").textContent = titre;
  $("info-texte").textContent = texte;
  const v = $("info-valeur");
  // Ne pas répéter le titre juste au-dessus de lui-même.
  const utile = valeur && valeur !== titre;
  v.textContent = utile ? valeur : "";
  v.hidden = !utile;
  $("voile").hidden = false;
}
function fermer() { $("voile").hidden = true; }
$("info-fermer").addEventListener("click", fermer);
$("voile").addEventListener("click", (e) => { if (e.target === $("voile")) fermer(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") fermer(); });

/* ---------- filtrage ---------- */
const ACTIVITE = {
  semaine: ["Cette semaine", 7], mois: ["Ce mois-ci", 31],
  trimestre: ["3 derniers mois", 92], arret: ["À l'arrêt depuis 1 an", -365],
};
