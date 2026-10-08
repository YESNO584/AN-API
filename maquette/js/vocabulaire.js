/* Le vocabulaire de l'écran : les étapes des deux chambres, les issues, les types de texte, les chambres. Rien ici ne s'exécute : ce sont des tables. */

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
