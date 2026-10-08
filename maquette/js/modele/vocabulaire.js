/* Le vocabulaire de l'écran : les étapes des deux chambres, les issues, les types de texte, les chambres, les votes, et les mots qui vont avec. Rien ici ne s'exécute : ce sont des tables. */

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

function typeCourt(t) { return (TYPES[t] || [t])[0]; }

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

/* ---------- filtrage ---------- */
const ACTIVITE = {
  semaine: ["Cette semaine", 7], mois: ["Ce mois-ci", 31],
  trimestre: ["3 derniers mois", 92], arret: ["À l'arrêt depuis 1 an", -365],
};

/* ---------- les votes ---------- */
const POSITIONS = { pour: "pour", contre: "contre", abstention: "abstention",
                    "partagé": "partagé" };

/* ------------------------------------------------------------------ *
 * La fiche d'un texte
 * ------------------------------------------------------------------ */

const SORTS_AMDT = { "Adopté": "adopte", "Rejeté": "rejete" };

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

/* ---------- l'entrée en vigueur, et le lien vers le détail ---------- *
 * Rien n'est rédigé ici à partir de rien : les dates viennent du texte
 * officiel, le nombre d'articles est un compte, et la raison pour laquelle une
 * loi ne change aucun article est son propre type de dossier.
 * ------------------------------------------------------------------ */

// Les lois qui ne modifient aucun article, quand la source dit pourquoi.
// Seuls les types de dossier qui l'expliquent d'eux-mêmes sont ici ; pour les
// autres, on constate sans inventer de raison.
const POURQUOI_SANS_CHANGEMENT = {
  "Projet de ratification des traités et conventions":
    "ce texte autorise la ratification d'un traité",
};

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
