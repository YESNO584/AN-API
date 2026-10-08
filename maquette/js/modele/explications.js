/* Les explications au toucher du ⓘ, une par notion. Du texte, écrit ici une fois pour toutes. */

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
