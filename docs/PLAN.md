# Plan — Application de suivi de l'Assemblée nationale

**Statut :** brouillon v1 — étude de faisabilité + plan initial
**Dernière mise à jour :** 2026-08-31
**Ce document est vivant.** Il est mis à jour à chaque session. Voir le
« Journal des mises à jour » à la fin.

---

## 1. En bref

**Le projet est faisable.** L'Assemblée nationale publie elle-même, en accès
libre et gratuit, la quasi-totalité de ce que l'application doit suivre :
qui sont les députés, quels textes sont en discussion, qui a voté quoi, ce
qui s'est dit en séance, et l'agenda des réunions. Ces données sont sous
« Licence Ouverte » (la licence publique de l'État), donc réutilisables, y
compris dans un produit commercial, à condition de citer la source.

**Trois choses sont plus difficiles qu'elles n'en ont l'air :**

1. **Beaucoup de votes n'existent pas sous forme de données.** À
   l'Assemblée, la plupart des votes se font à main levée et ne sont
   enregistrés nulle part au nom de chaque député. Seuls les « scrutins
   publics » donnent la liste nominative. L'application ne pourra donc pas
   dire « votre député a voté pour » sur tous les sujets — seulement sur
   ceux-là.
2. **« Vote important » n'est pas une donnée, c'est un choix éditorial.**
   Rien dans les fichiers publics ne dit qu'un vote compte plus qu'un autre.
   C'est nous qui devrons définir la règle, et l'assumer.
3. **Les résumés de séance demandent un modèle de langage**, donc un coût,
   et surtout un risque : un résumé faux sur un sujet politique est un vrai
   problème de crédibilité. La bonne nouvelle est que le coût est faible
   (voir §7) ; le risque, lui, se gère par la méthode, pas par le budget.

**Ce qui n'est pas encore décidé :** la technologie, la forme de
l'application (site, mobile, notifications, lettre d'information), et
l'hébergement. Ces choix sont volontairement laissés ouverts — voir §8.

---

## 2. Ce que l'application doit suivre

Cinq objets, par ordre de difficulté croissante :

| # | Objet | Difficulté | Source |
|---|---|---|---|
| 1 | **Agenda** — ce qui se passe cette semaine à l'Assemblée | Facile | Jeu de données « Réunions » |
| 2 | **Textes de loi** — où en est un projet ou une proposition de loi | Facile | Jeu de données « Dossiers législatifs » |
| 3 | **Votes** — résultat d'un scrutin public, et position de chaque député | Facile à récupérer, **incomplet par nature** | Jeu de données « Scrutins » |
| 4 | **Débats** — ce qui s'est dit, par qui | Facile à récupérer, **volumineux** | Comptes rendus de séance |
| 5 | **Résumés de séance** — l'essentiel d'une journée en quelques lignes | **Difficile** | À produire nous-mêmes |

Les objets 1 à 4 sont de la récupération et de la mise en forme de données
publiques. L'objet 5 est le seul qui crée vraiment de la valeur nouvelle —
et le seul qui puisse se tromper.

---

## 3. Les sources de données

### 3.1 Source principale : le portail open data de l'Assemblée

**`data.assemblee-nationale.fr`**

C'est la source de référence. Elle publie, en XML et en JSON (et en CSV pour
une partie), sous **Licence Ouverte (Etalab)** :

- **Acteurs et organes** — les députés en exercice, leurs mandats, leurs
  groupes politiques, leurs commissions ; plus un historique des députés
  élus depuis juin 1997.
- **Dossiers législatifs** — chaque texte en discussion, ses documents
  (projet ou proposition de loi, texte adopté, rapports), le rapporteur, les
  dates d'examen.
- **Scrutins** — pour chaque scrutin public, la position de vote de chaque
  député.
- **Amendements** — tous les amendements déposés, en commission et en
  séance, avec leur auteur, leur contenu, leur exposé des motifs et leur
  sort (adopté / rejeté).
- **Questions** — les questions écrites des députés et les réponses du
  Gouvernement.
- **Réunions** — toutes les réunions tenues à l'Assemblée (séance publique,
  commissions, groupes d'études, etc.), avec l'heure, le lieu, l'ordre du
  jour quand il est connu, les participants et les absences.
- **Débats / comptes rendus** — le texte des débats en séance publique :
  jour, date, numéro de séance, sujets abordés, tous les intervenants
  (députés et ministres), et le texte lui-même.

**Deux détails qui comptent pour la mise à jour :**

- Une **liste quotidienne au format CSV** recense les documents nouvellement
  publiés (« au fil de l'eau »). C'est le point d'entrée naturel pour savoir
  ce qui a changé sans tout retélécharger chaque jour.
- L'accès se fait en HTTPS et en FTPS. Les comptes rendus sont publiés en
  XML par la DILA au fil de leur parution, avec un schéma XSD fourni.

**Attention :** les mêmes jeux de données sont aussi présents sur
`data.gouv.fr`, mais il s'agit d'un miroir **rarement mis à jour**. Ne pas
l'utiliser comme source vivante.

### 3.2 Délais de publication (ce qui conditionne la fraîcheur de l'appli)

C'est le point le plus important pour concevoir un produit « d'actualité » :

| Contenu | Disponible après la fin de la séance |
|---|---|
| Compte rendu analytique (version officielle, résumée) | **moins de 3 heures** |
| Compte rendu intégral, en HTML (le mot à mot) | **moins de 24 heures** |
| Compte rendu intégral, en PDF | environ 5 jours ouvrés |

Conséquence directe : une application qui publie un résumé **le lendemain
matin** est réaliste. Une application qui publie **en direct pendant la
séance** ne l'est pas à partir de ces sources — il faudrait passer par la
vidéo, ce qui est un autre projet (voir §6.5).

### 3.3 Sources complémentaires (optionnelles)

- **Légifrance, via le portail PISTE** — l'API juridique de l'État, gratuite
  après création d'un compte et acceptation des conditions d'utilisation.
  Utile pour la fin du parcours : la loi telle qu'elle est publiée au
  Journal officiel, et le suivi des dossiers législatifs côté
  Gouvernement. Nécessite une clé d'accès, donc une inscription — à ne faire
  que si l'on va jusqu'à « la loi est parue ».
- **NosDéputés.fr (association Regards Citoyens)** — une API et des exports
  de base de données déjà nettoyés et enrichis (présence des députés,
  indicateurs d'activité par député et par mois). Licences : **CC-BY-SA**
  pour le contenu, **ODbL** pour les données — plus contraignantes que la
  Licence Ouverte, car elles obligent à repartager les données modifiées.
  Très utile comme **référence de contrôle** (comparer nos chiffres aux
  leurs) même si on ne l'intègre pas au produit.
- **Le Sénat** publie aussi ses données de son côté. Hors périmètre pour
  l'instant, mais à garder en tête : une loi passe par les deux chambres, et
  un suivi qui s'arrête à l'Assemblée raconte la moitié de l'histoire.

### 3.4 Ce qui existe déjà

Des projets couvrent déjà une partie du sujet : **NosDéputés.fr**
(historique, associatif), et des sites plus récents comme **Civiqo** et
**CIVIX** qui exposent les scrutins publics. Ce n'est pas un obstacle — cela
prouve que les données sont exploitables — mais cela déplace la question :
**qu'est-ce que notre application apporte que ceux-là n'apportent pas ?**
Piste la plus crédible : le **résumé lisible** et le **suivi personnalisé**
(« préviens-moi quand on parle de X », « que fait mon député »), plutôt que
la simple mise à disposition des données brutes.

---

## 4. Niveau de vérification de ce document

Règle du projet : ne pas présenter comme un fait ce qui n'a pas été vérifié.

- **Le réseau de la session de travail bloque l'accès direct à
  `data.assemblee-nationale.fr`**, ainsi qu'à `data.gouv.fr`,
  `legifrance.gouv.fr` et `nosdeputes.fr`. Tout le §3 s'appuie donc sur des
  recherches web et sur les descriptions publiées de ces jeux de données —
  **pas sur les fichiers eux-mêmes**.
- **Non vérifié à ce stade, et à vérifier en premier (étape 0) :** les URL
  exactes des fichiers, leur taille, la structure précise du XML/JSON, la
  législature couverte par chaque jeu de données, et le comportement réel de
  la liste quotidienne des nouveautés.
- Tant que l'étape 0 n'est pas faite, **aucun chiffre de ce document portant
  sur les volumes ou les coûts ne doit être cité ailleurs** : ce sont des
  ordres de grandeur, pas des mesures.

---

## 5. Le plan par étapes

Chaque étape doit être utilisable seule. On ne passe à la suivante qu'une
fois la précédente vraiment terminée.

### Étape 0 — Vérifier le terrain (à faire depuis un poste sans blocage réseau)

**But :** remplacer les suppositions du §3 par des faits.

- Télécharger à la main un exemplaire de chaque jeu de données.
- Noter pour chacun : URL exacte, format, taille, période couverte,
  fréquence réelle de mise à jour.
- Vérifier ce que contient précisément la liste quotidienne des nouveautés.
- **Mesurer la taille d'une journée de séance** (nombre de caractères du
  compte rendu intégral) — c'est le chiffre dont dépend tout le calcul de
  coût du §7.
- Vérifier ce qui existe pour les votes : combien de scrutins publics par an,
  et sur quoi ils portent.

**Livrable :** une fiche par jeu de données, ajoutée à ce dossier `docs/`.
**Sans cette étape, tout le reste est du pari.**

### Étape 1 — Récupérer et stocker (le socle)

**But :** avoir chez nous, à jour tous les jours, une copie propre des
données publiques.

- Un programme qui télécharge les jeux de données et les range dans une base.
- Il tourne tous les jours, tout seul.
- Il sait ne retélécharger que ce qui a changé.
- Il garde une trace de ce qu'il a fait (pour qu'une panne se voie).

**Résultat visible :** aucun pour l'utilisateur. C'est la fondation.
**Piège à éviter :** vouloir tout stocker dès le début. Commencer par
députés + dossiers législatifs + scrutins. Les débats, très volumineux,
viennent après.

### Étape 2 — Rendre consultable (la première vraie version)

**But :** quelque chose qu'on peut montrer.

- Une liste des textes en cours d'examen, avec leur état d'avancement.
- Une fiche par député : groupe, commission, ses votes lors des scrutins
  publics.
- Une fiche par scrutin : le sujet, le résultat, qui a voté quoi, avec le
  détail par groupe politique.
- L'agenda de la semaine.

**C'est déjà une application utile**, et elle ne contient aucun texte écrit
par une machine — donc aucun risque d'erreur de notre fait. À ce stade, tout
ce qui est affiché vient directement de l'Assemblée.

### Étape 3 — Alerter (ce qui transforme un site en service)

**But :** l'utilisateur n'a plus besoin de venir voir ; on lui dit quoi.

- Suivre un texte de loi et être prévenu à chaque étape.
- Suivre un député.
- Suivre un mot-clé (« logement », « intelligence artificielle ») dans les
  débats et les amendements.
- Une lettre d'information hebdomadaire, automatique.

**Question à trancher avant de commencer :** par quel canal ? E-mail,
notification mobile, message sur une messagerie ? Ce choix détermine s'il
faut une application mobile ou non — donc une bonne partie de la
technologie. Voir §8.

### Étape 4 — Résumer (la partie difficile)

**But :** « voici ce qui s'est passé hier à l'Assemblée, en dix lignes ».

Trois niveaux, à faire dans cet ordre :

1. **Résumé d'un scrutin** — court, très cadré, facile à vérifier. Le bon
   terrain d'essai.
2. **Résumé d'un débat sur un texte** — les positions en présence, les
   points d'accord et de désaccord.
3. **Résumé d'une journée de séance** — le plus exposé aux erreurs.

**Règles non négociables pour cette étape :**

- **Toujours afficher le lien vers le compte rendu officiel** à côté du
  résumé. L'utilisateur doit pouvoir vérifier en un clic.
- **Indiquer clairement que le résumé est produit automatiquement.**
- **Ne jamais résumer ce qu'on n'a pas.** Si un vote s'est fait à main levée,
  le dire, plutôt que de laisser croire à un vote nominatif.
- **Neutralité de ton.** Décrire les positions, ne pas les juger.
- **Se relire soi-même :** avant publication, une seconde passe vérifie que
  chaque affirmation du résumé est bien présente dans le texte source. Un
  résumé qui invente un chiffre ou une citation est une faute grave sur un
  sujet politique.

### Étape 5 et au-delà — pistes, non engagées

- Étendre au Sénat, pour suivre une loi de bout en bout.
- Suivre le parcours d'un amendement : qui l'a déposé, ce qu'il est devenu.
- Statistiques sur la durée : présence, discipline de vote au sein d'un
  groupe, sujets qui reviennent.
- Suivi vidéo / temps réel (voir §6.5).

---

## 6. Les difficultés, en détail

### 6.1 Tous les votes ne sont pas enregistrés

À l'Assemblée, un vote se fait à main levée, par scrutin public ordinaire, ou
par scrutin à la tribune. **Le vote à main levée ne laisse aucune trace
nominative.** L'open data ne couvre que les scrutins publics : scrutins
solennels, déclarations du Gouvernement, motions de procédure, et autres
scrutins publics.

**Conséquence produit :** la promesse « suivez le vote de votre député sur
tous les sujets » est **impossible à tenir**. Il faut soit reformuler la
promesse, soit accepter d'afficher souvent « pas de vote nominatif sur ce
texte ». Mieux vaut en faire un élément d'information — expliquer pourquoi —
que de le cacher.

### 6.2 « Important » n'est pas dans les données

Aucune donnée ne dit qu'un vote compte. Il faut une règle, écrite et
assumée. Quelques critères possibles, à combiner :

- les **scrutins solennels** (l'Assemblée elle-même les distingue) ;
- le **vote sur l'ensemble d'un texte**, par opposition aux votes de détail ;
- les **motions de censure** et les votes de confiance ;
- les votes **serrés** (écart faible entre pour et contre) ;
- les votes où **un groupe se divise** — souvent le plus révélateur.

**Recommandation :** commencer par une règle simple et transparente
(scrutins solennels + vote sur l'ensemble + écart serré), l'afficher aux
utilisateurs, et la faire évoluer. Ne pas cacher la règle derrière un calcul
opaque.

### 6.3 Le volume des débats

Une journée de séance représente un texte très long, et il y a de l'ordre de
150 jours de séance par an. Cela pose deux questions : le stockage (peu
coûteux) et le traitement par un modèle de langage (voir §7). Ce n'est pas
bloquant, mais cela impose de **ne pas tout traiter en une seule fois** :
découper par sujet ou par intervention, ce que la structure du compte rendu
permet puisqu'elle identifie les orateurs et les sujets.

### 6.4 Le risque d'erreur sur un sujet politique

C'est le risque principal du projet, plus que la technique. Un résumé qui
attribue à un député une position qu'il n'a pas prise, sur un sujet
sensible, est un problème sérieux — juridique autant que de réputation. Les
règles de l'étape 4 ne sont pas des précautions de style : ce sont les
conditions pour que le produit soit publiable.

### 6.5 Le temps réel

Suivre la séance en direct supposerait de traiter la vidéo ou l'audio des
débats. C'est un projet à part entière, avec ses propres difficultés (qualité
de la transcription, identification des orateurs, coût continu). **À exclure
du plan actuel.** Le délai de moins de 3 heures du compte rendu analytique
offre déjà une fraîcheur très correcte.

### 6.6 Les changements de législature

Les jeux de données sont organisés par législature, et les archives des
législatures passées sont séparées des données courantes. Une application
conçue uniquement autour de « la législature en cours » se cassera au
prochain renouvellement de l'Assemblée. **À prévoir dès le modèle de
données**, pas après.

---

## 7. Coûts

### 7.1 Ce qui est gratuit

Toutes les données sources : le portail de l'Assemblée est gratuit et sans
inscription ; l'API Légifrance est gratuite après création d'un compte.

### 7.2 Hébergement

Faible tant qu'il n'y a pas beaucoup d'utilisateurs : un petit serveur, une
base de données, du stockage. À chiffrer une fois la technologie choisie.

### 7.3 Les résumés automatiques — moins chers qu'attendu

C'est la seule dépense qui grandit avec l'usage. Les prix ci-dessous sont
ceux de l'API Claude, par million de jetons (un « jeton » est à peu près
trois quarts de mot) :

| Modèle | Entrée / M jetons | Sortie / M jetons | Fenêtre de contexte |
|---|---|---|---|
| Claude Opus 5 | 5 $ | 25 $ | 1 M jetons |
| Claude Sonnet 5 | 2 $ | 10 $ | 1 M jetons |
| Claude Haiku 4.5 | 1 $ | 5 $ | 200 K jetons |

Trois leviers réduisent fortement la facture :

- **Le traitement par lots** (« batch ») : les résumés ne sont pas urgents à
  la seconde près, on peut les envoyer en traitement asynchrone → **-50 %**.
- **La mise en cache du contexte** : la partie fixe des instructions n'est
  facturée plein tarif qu'une fois.
- **La fenêtre de contexte d'un million de jetons** évite d'avoir à
  découper artificiellement les longs comptes rendus.

**Ordre de grandeur, à confirmer par l'étape 0 :** si une journée de séance
représente quelques centaines de milliers de jetons de texte, et qu'il y a
environ 150 jours de séance par an, le traitement d'une année entière de
débats se compte **en dizaines à quelques centaines d'euros**, pas en
milliers. Le coût des résumés **n'est pas le facteur limitant du projet** —
la qualité et la vérification le sont.

*(Ces chiffres sont des ordres de grandeur. La mesure réelle de la taille
d'une journée de séance est le livrable clé de l'étape 0.)*

---

## 8. Décisions à prendre

Ces questions ne sont volontairement pas tranchées. Chacune change
significativement la suite.

| # | Question | Pourquoi ça compte |
|---|---|---|
| 1 | **Pour qui ?** Grand public curieux, journalistes, professionnels du secteur public, associations ? | Détermine le niveau de détail, le ton, et si le produit est payant |
| 2 | **Sous quelle forme ?** Site web, application mobile, lettre d'information, robot de messagerie ? | C'est le choix le plus structurant. Une lettre d'information est dix fois plus rapide à faire qu'une application mobile |
| 3 | **Personnel ou général ?** Suivi personnalisé (comptes utilisateurs) ou contenu identique pour tous ? | Les comptes utilisateurs impliquent des obligations RGPD et beaucoup plus de travail |
| 4 | **Périmètre :** Assemblée seule, ou Assemblée + Sénat ? | Le Sénat double le travail de récupération, mais sans lui le suivi d'une loi est incomplet |
| 5 | **Budget et rythme :** projet personnel du week-end, ou produit à lancer ? | Détermine s'il faut viser l'étape 2 ou l'étape 4 |
| 6 | **Technologie** — laissée ouverte à votre demande. À trancher juste avant l'étape 1, une fois les points 1 à 5 connus | Choisir la technologie avant de savoir ce qu'on construit, c'est se contraindre pour rien |

**Recommandation :** répondre au moins aux questions 1, 2 et 5 avant de
commencer l'étape 1. Les autres peuvent attendre.

---

## 9. Points d'attention pour le dépôt lui-même

Rappels issus de `CLAUDE.md`, à traiter **dans la session qui écrira le
premier code** :

- La section « Architecture » de `CLAUDE.md` doit être remplacée par la vraie
  carte du projet (elle indique aujourd'hui que le dépôt est vide).
- `.claude/code_rules.json` est aujourd'hui un modèle générique pour du C#.
  Tant qu'il n'est pas régénéré à partir du vrai code, le vérificateur de
  règles de code ne vérifie rien : un rapport « 0 problème » ne veut rien
  dire.
- La règle « produit = tout ce qui n'est pas `.claude/` » devra être
  remplacée par le vrai chemin du code source dès qu'il existera.

---

## 10. Prochaine étape immédiate

1. Répondre aux questions 1, 2 et 5 du §8.
2. Faire l'étape 0 (vérification des données) depuis un poste sans blocage
   réseau, et écrire les fiches par jeu de données.
3. Revenir sur ce plan avec les vrais chiffres, et choisir la technologie.

---

## Journal des mises à jour

| Date | Version | Ce qui a changé |
|---|---|---|
| 2026-08-31 | v1 | Création : étude de faisabilité et plan initial. Sources vérifiées par recherche web uniquement — accès direct aux portails bloqué par le réseau. |

---

## Sources consultées

- Portail open data de l'Assemblée nationale — <https://data.assemblee-nationale.fr/>
- Travaux parlementaires (jeux de données) — <https://data.assemblee-nationale.fr/travaux-parlementaires>
- Réunions — <https://data.assemblee-nationale.fr/reunions>
- Foire aux questions du portail — <https://data.assemblee-nationale.fr/foire-aux-questions>
- Fiche de synthèse n°56 : Les votes à l'Assemblée nationale — <https://www.assemblee-nationale.fr/dyn/synthese/fonctionnement-assemblee-nationale/travail-legislatif/les-votes-a-l-assemblee-nationale>
- Fiche de synthèse n°30 : Les comptes rendus — <https://www.assemblee-nationale.fr/dyn/synthese/organisation-assemblee-nationale/les-comptes-rendus>
- Communiqué d'ouverture du site open data — <https://www.assemblee-nationale.fr/presse/communiques/20150622-01.asp>
- Comptes rendus des débats sur data.gouv.fr — <https://www.data.gouv.fr/datasets/comptes-rendus-des-debats-de-l-assemblee-nationale>
- Organisation « Assemblée nationale » sur data.gouv.fr — <https://www.data.gouv.fr/organizations/assemblee-nationale/datasets>
- Open data et API de Légifrance — <https://www.legifrance.gouv.fr/contenu/pied-de-page/open-data-et-api>
- Documentation de l'API NosDéputés.fr — <https://github.com/regardscitoyens/nosdeputes.fr/blob/master/doc/api.md>
- Données parlementaires en open data (Regards Citoyens) — <https://github.com/regardscitoyens/nosdeputes.fr/blob/master/doc/opendata.md>
- Scrutins publics, Civiqo — <https://www.civiqo.fr/scrutins>
- Votes de l'Assemblée nationale, CIVIX — <https://www.civix.fr/votes-assemblee-nationale>
