# Plan — Application de suivi du Parlement (Assemblée nationale + Sénat)

**Statut :** v3.2 — **étapes 0, 1 et 2 faites ; l'application Flutter est la suite**
**Dernière mise à jour :** 2026-08-31
**Ce document est vivant.** Il est mis à jour à chaque session. Voir le
« Journal des mises à jour » à la fin.

---

## 1. En bref

**Le projet est faisable.** Les deux chambres du Parlement publient
elles-mêmes, en accès libre et gratuit, la quasi-totalité de ce que
l'application doit suivre : qui sont les parlementaires, quels textes sont en
discussion, qui a voté quoi, ce qui s'est dit en séance, et l'agenda des
réunions.

**Ce qui a été décidé** (voir §10) : une plateforme unique mobile et web,
pour le grand public curieux ; la première fonctionnalité à tester est le
**suivi d'un texte de loi sur toute sa durée de vie**, et chacun choisit ses
textes en **favoris** ; le périmètre couvre **l'Assemblée et le Sénat** ; et
l'objectif immédiat est une **maquette testable**, pas un produit fini.

**Trois choses sont plus difficiles qu'elles n'en ont l'air :**

1. **Suivre un texte de bout en bout n'est pas additionner deux sources.**
   Un texte fait des allers-retours entre les deux chambres. Chacune publie
   ses propres données, avec ses propres identifiants. Recoller les deux
   moitiés du parcours est le vrai travail technique du projet — voir §3.
2. **Beaucoup de votes n'existent pas sous forme de données.** La plupart
   des votes se font à main levée et ne sont enregistrés nulle part au nom
   de chaque parlementaire. Seuls les « scrutins publics » donnent la liste
   nominative. L'application ne pourra donc pas dire « votre député a voté
   pour » sur tous les sujets — seulement sur ceux-là.
3. **Les résumés de séance demandent un modèle de langage**, donc un coût,
   et surtout un risque : un résumé faux sur un sujet politique est un vrai
   problème de crédibilité. Le coût est faible (voir §9) ; le risque, lui,
   se gère par la méthode, pas par le budget.

**Bonne nouvelle inattendue :** un projet associatif, **La Fabrique de la
Loi**, a déjà résolu le problème n°1 et publie le résultat en accès libre.
S'il est encore à jour, il peut servir de socle à la maquette et faire
gagner des mois. C'est le premier point à vérifier (étape 0, §6).

**Ce qui n'est pas encore décidé :** la technologie, et l'hébergement.

---

## 2. Ce que l'application doit suivre

Cinq objets, par ordre de difficulté croissante :

| # | Objet | Difficulté | Source |
|---|---|---|---|
| 1 | **Agenda** — ce qui se passe cette semaine au Parlement | Facile | Jeux de données « Réunions » des deux chambres |
| 2 | **Textes de loi** — où en est un texte, dans son parcours complet | **Le cœur du produit.** Facile par chambre, **difficile à recoller** | Dossiers législatifs des deux chambres |
| 3 | **Votes** — résultat d'un scrutin public, et position de chaque élu | Facile à récupérer, **incomplet par nature** | Jeux de données « Scrutins » |
| 4 | **Débats** — ce qui s'est dit, par qui | Facile à récupérer, **volumineux** | Comptes rendus de séance |
| 5 | **Résumés de séance** — l'essentiel d'une journée en quelques lignes | **Difficile** | À produire nous-mêmes |

L'objet 2 est celui que l'utilisateur vient chercher. Les objets 1, 3 et 4
l'enrichissent. L'objet 5 est le seul qui crée du texte nouveau — et le seul
qui puisse se tromper.

---

## 3. Le parcours d'une loi, et ce que « suivre de bout en bout » implique

C'est la section qui conditionne toute l'architecture du produit.

### 3.1 Le parcours réel d'un texte

Un texte ne suit pas une ligne droite. Dans les grandes lignes :

1. **Dépôt** — le Gouvernement dépose un *projet* de loi, ou un
   parlementaire une *proposition* de loi, dans l'une des deux chambres.
2. **Commission** — une commission examine le texte, l'amende, et publie
   son propre texte.
3. **Séance publique** — la chambre débat, amende encore, puis vote sur
   l'ensemble.
4. **Navette** — le texte part à l'autre chambre, qui recommence tout. Si
   elle le modifie, il repart. Cet aller-retour peut se répéter.
5. **Sortie de navette** — soit un accord, soit une commission mixte
   paritaire (sept députés, sept sénateurs) qui tente un compromis, soit le
   dernier mot donné à l'Assemblée.
6. **Après le vote** — contrôle éventuel du Conseil constitutionnel, puis
   promulgation et publication au Journal officiel.

**Conséquence pour le produit :** l'objet central n'est pas « un texte à
l'Assemblée », c'est **un dossier législatif unique auquel se rattachent des
étapes datées, chacune située dans une chambre.** Se tromper là-dessus
oblige à tout refaire plus tard.

### 3.2 Le problème du recollement

**Vérifié le 2026-08-31 : le problème n'existe pas.** L'Assemblée publie,
dans chaque dossier, le champ `senatChemin` — l'adresse du dossier
correspondant sur `senat.fr`. Rapproché du fichier du Sénat, cela marche sur
**100 %** des 910 dossiers concernés (901 directement, les 9 autres après
normalisation d'une ancienne forme d'adresse). Détail dans
`sources/assemblee-nationale.md`.

**C'est donc la stratégie A qui gagne, mais pas celle qu'on croyait** : ce
n'est pas La Fabrique de la Loi qui a fait le recollement, c'est l'Assemblée
nationale elle-même.

Le texte d'origine de cette section, conservé pour mémoire :

> Chaque chambre publie ses propres données, avec ses propres numéros. Rien
> ne garantit qu'un identifiant permette de dire « ce texte au Sénat est le
> même que celui-là à l'Assemblée ».

Trois stratégies possibles, de la meilleure à la moins bonne :

| Stratégie | Principe | Ce qu'il faut vérifier |
|---|---|---|
| **A — Réutiliser La Fabrique de la Loi** | Un projet associatif a déjà fait ce recollement et publie le résultat | Est-il encore à jour ? Sous quelle licence ? |
| **B — S'appuyer sur Légifrance** | Légifrance publie des « dossiers législatifs » qui couvrent le parcours entier | La couverture est-elle complète et assez fraîche ? |
| **C — Recoller nous-mêmes** | Rapprocher les données des deux chambres par titre, date et numéro | Coûteux, fragile, et jamais fiable à 100 % |

**Résultat de la vérification :**

| Stratégie | Verdict |
|---|---|
| **A — La Fabrique de la Loi** | **Écartée.** Figée depuis 2022 (§4.4) |
| **B — Légifrance** | **Sans objet.** Ne servait que de secours ; le rapprochement fonctionne sans elle |
| **C — Recoller nous-mêmes** | **Inutile.** L'Assemblée fournit le lien |

**Aucune ligne de code de recollement n'est à écrire.**

---

## 4. Les sources de données

### 4.1 Assemblée nationale — `data.assemblee-nationale.fr`

Publie en XML et en JSON (CSV pour une partie), sous **Licence Ouverte
(Etalab)** — réutilisable y compris commercialement, à condition de citer la
source :

- **Acteurs et organes** — les députés, leurs mandats, groupes et
  commissions ; historique depuis juin 1997.
- **Dossiers législatifs** — chaque texte en discussion, ses documents, le
  rapporteur, les dates d'examen. **Couvre la législature en cours** ; les
  législatures passées sont dans des jeux d'archives séparés.
- **Scrutins** — pour chaque scrutin public, la position de chaque député.
- **Amendements** — tous les amendements, avec auteur, contenu, exposé des
  motifs et sort (adopté / rejeté).
- **Questions** — questions écrites et réponses du Gouvernement.
- **Réunions** — séance publique, commissions, groupes d'études : heure,
  lieu, ordre du jour, participants et absences.
- **Débats / comptes rendus** — le texte des débats, avec les intervenants.

**Deux détails qui comptent pour la mise à jour :**

- Une **liste quotidienne au format CSV** recense les documents nouvellement
  publiés (« au fil de l'eau »). C'est le point d'entrée naturel pour savoir
  ce qui a changé sans tout retélécharger chaque jour.
- L'accès se fait en HTTPS et en FTPS. Les comptes rendus sont publiés en
  XML par la DILA au fil de leur parution, avec un schéma XSD fourni.

**Attention :** les mêmes jeux de données existent aussi sur `data.gouv.fr`,
mais il s'agit d'un miroir **rarement mis à jour**. Ne pas l'utiliser comme
source vivante.

### 4.2 Sénat — `data.senat.fr`

Le Sénat a son propre portail open data, organisé en quatre familles :
travaux législatifs, amendements, comptes rendus, et questions des
sénateurs.

- **La base DOSLEG** est l'équivalent sénatorial des dossiers législatifs.
  Elle couvre les documents déposés au Sénat **depuis octobre 1977** :
  projets et propositions de loi, rapports, textes de commission. Un export
  liste l'ensemble des dossiers législatifs publiés sur le site du Sénat.
- **Formats :** XML au standard international **Akoma Ntoso** (un format
  d'échange de documents parlementaires), plus des **exports SQL complets**
  et des **extraits CSV** plus simples à manipuler.
- Un jeu « Travaux législatifs (Sénat) » est également publié sur
  `data.gouv.fr`.

**Différence de nature avec l'Assemblée :** le Sénat remonte à 1977, quand
les dossiers législatifs de l'Assemblée sont organisés par législature.
Pour un suivi historique, les deux ne se comportent pas pareil.

### 4.3 Légifrance, via le portail PISTE

L'API juridique de l'État. **Gratuite, mais elle exige une inscription** sur
`piste.gouv.fr` et une clé d'accès — ce n'est pas un téléchargement anonyme.
Elle expose les codes, les lois, les décrets, le Journal officiel, la
jurisprudence, et surtout **les dossiers législatifs et les débats
parlementaires**.

C'est la **stratégie B** du §3.2 : potentiellement une vue du parcours
complet, côté État, indépendante des deux chambres. Couverture et fraîcheur
à vérifier à l'étape 0.

### 4.4 La Fabrique de la Loi (Regards Citoyens) — ÉCARTÉE

> **Vérifié le 2026-08-31 : le projet est figé.** Ses données s'arrêtent au
> 11 janvier 2022 et ne couvrent que la 15e législature. La législature en
> cours est la 17e : elle est absente en totalité. La source ne peut pas
> servir à suivre l'actualité législative. Détail et chiffres dans
> `sources/fabrique-de-la-loi.md`.
>
> **Effet secondaire favorable :** la contrainte de licence ODbL décrite
> ci-dessous disparaît avec elle. L'Assemblée et le Sénat publient sous des
> licences nettement plus permissives.
>
> Ce qui suit décrit le projet tel qu'il a été, et reste utile sur un point :
> **son modèle d'étapes est bien conçu et vaut d'être repris.**

Un projet associatif mené avec deux laboratoires de Sciences Po Paris.
**Il fait déjà exactement ce que notre fonctionnalité principale doit
faire :** montrer le parcours d'un texte à travers toutes ses étapes
parlementaires, dans les deux chambres, avec les modifications du texte à
chaque phase, les amendements et les interventions.

- **Comment il est construit :** à partir de la base DOSLEG du Sénat, des
  sites des deux chambres, et de NosDéputés.fr / NosSénateurs.fr.
- **Ce qu'il publie :** une API ouverte, un fichier `dossiers.csv` listant
  tous les textes (promulgués comme en discussion) avec leurs métadonnées,
  et par texte le détail de ses étapes.
- **Licence : ODbL.** C'est important et différent de la Licence Ouverte :
  l'ODbL impose de **repartager sous la même licence** toute base dérivée
  qu'on redistribue. Utilisable, mais cela contraint un éventuel produit
  commercial. À regarder de près avant d'en faire le socle définitif.

**Les deux questions posées ici ont reçu leur réponse le 2026-08-31 :
non, et non.** Voir l'encadré en tête de section.

### 4.5 Délais de publication (ce qui conditionne la fraîcheur de l'appli)

| Contenu | Disponible après la fin de la séance |
|---|---|
| Compte rendu analytique (version officielle, résumée) | **moins de 3 heures** |
| Compte rendu intégral, en HTML (le mot à mot) | **moins de 24 heures** |
| Compte rendu intégral, en PDF | environ 5 jours ouvrés |

Conséquence directe : une application qui publie un résumé **le lendemain
matin** est réaliste. Une application qui publie **en direct pendant la
séance** ne l'est pas à partir de ces sources — il faudrait passer par la
vidéo, ce qui est un autre projet (voir §8.5).

### 4.6 Sources complémentaires

- **NosDéputés.fr / NosSénateurs.fr (Regards Citoyens)** — API et exports
  déjà nettoyés et enrichis (présence, indicateurs d'activité). Licences
  **CC-BY-SA** et **ODbL**. Très utiles comme **référence de contrôle**
  (comparer nos chiffres aux leurs) même sans les intégrer au produit.

### 4.7 Ce qui existe déjà

Des projets couvrent déjà une partie du sujet : **La Fabrique de la Loi**
(le parcours des textes), **NosDéputés.fr** (l'activité des élus), et des
sites plus récents comme **Civiqo** et **CIVIX** (les scrutins publics).

Ce n'est pas un obstacle — cela prouve que les données sont exploitables —
mais cela pose la vraie question : **qu'apporte notre application que
ceux-là n'apportent pas ?** Les réponses les plus crédibles, compte tenu des
décisions prises :

- **Le grand public, pas les spécialistes.** Les outils existants sont
  denses, faits pour des gens qui connaissent déjà la procédure.
- **Le suivi personnalisé.** Choisir ses textes en favoris et être prévenu
  quand ils bougent — aucun des sites existants ne le propose vraiment.
- **Mobile et web dans la même expérience.**

---

## 5. Niveau de vérification de ce document

Règle du projet : ne pas présenter comme un fait ce qui n'a pas été vérifié.

**L'étape 0 a été faite le 2026-08-31.** Les fichiers ont été téléchargés et
comptés. Le détail est dans **`sources/`** — une fiche par source, plus un
`sources/README.md` qui résume ce qui a changé.

Ce qui est désormais **mesuré** :

- Les adresses exactes, formats, tailles et fraîcheur des jeux de données des
  deux chambres.
- La structure des dossiers législatifs de l'Assemblée et de la liste du
  Sénat.
- **L'identifiant commun entre les deux chambres : il existe** (voir §3.2).
- **L'état de La Fabrique de la Loi : figée depuis 2022** (voir §4.4).
- Le volume des débats, et donc le coût des résumés (voir §9.3).

Ce qui reste **non vérifié**, et pourquoi :

- **L'API Légifrance via PISTE.** Elle demande un compte et une clé, qu'une
  session ne peut pas créer. Voir `sources/legifrance-piste.md`. Ce point
  n'est plus bloquant : il ne servait que de solution de secours au
  rapprochement des deux chambres, qui fonctionne.
- **NosDéputés.fr et NosSénateurs.fr**, hors service au moment du test.

L'accès réseau n'est plus un obstacle : les portails répondent normalement.
Voir `ACCES-RESEAU.md`.

---

## 6. Le plan par étapes

**L'ordre a changé en v2.** La v1 construisait d'abord la récupération
complète des données, puis l'affichage. Puisque l'objectif immédiat est une
**maquette testable**, on inverse : on montre l'écran principal le plus tôt
possible, sur un petit échantillon de données réelles, et on n'industrialise
qu'ensuite.

Chaque étape doit être utilisable seule.

### Étape 0 — Vérifier le terrain — **FAITE le 2026-08-31**

**But :** remplacer les suppositions des §3 et §4 par des faits.

**Résultats dans `sources/`.** État de chaque point :

| | Point | État |
|---|---|---|
| 1 | La Fabrique de la Loi est-elle vivante ? | ✅ **Non** — figée depuis janvier 2022 |
| 2 | Identifiant commun entre les deux chambres ? | ✅ **Oui** — l'Assemblée publie le lien vers le Sénat, 100 % de correspondance |
| 3 | Que vaut Légifrance sur les dossiers législatifs ? | ⬜ **Non fait** — demande un compte PISTE. N'est plus bloquant |
| 4 | Inventaire des jeux de données des deux chambres | ✅ Fait — adresses, formats, tailles, fraîcheur |
| 5 | Taille d'une journée de séance | ✅ Mesurée — voir §9.3 |
| 6 | Nombre de scrutins publics par an | ✅ 4 422 à l'Assemblée en 2025, essentiellement sur des amendements |

**Par ordre d'importance :**

1. **La Fabrique de la Loi est-elle vivante ?** Récupérer `dossiers.csv`,
   regarder la date du texte le plus récent, et le détail des étapes d'un
   texte en cours. **Si oui, la maquette est à quelques jours ; si non, à
   quelques semaines.** C'est la question qui change tout.
2. **Existe-t-il un identifiant commun entre les deux chambres ?** Prendre
   trois textes récents passés par les deux, et regarder si les données de
   l'Assemblée et du Sénat permettent de les rapprocher sans deviner.
3. **Que vaut Légifrance sur les dossiers législatifs ?** Créer un compte
   PISTE, et regarder si le parcours complet y est, et à quelle fraîcheur.
4. Télécharger un exemplaire de chaque jeu de données des deux chambres.
   Noter pour chacun : URL exacte, format, taille, période couverte,
   fréquence réelle de mise à jour.
5. **Mesurer la taille d'une journée de séance** (nombre de caractères du
   compte rendu intégral) — c'est le chiffre dont dépend tout le calcul de
   coût du §9.
6. Compter les scrutins publics par an, et regarder sur quoi ils portent.

**Livrable :** une fiche par source, ajoutée à ce dossier `docs/`.
**Sans cette étape, tout le reste est du pari.**

### Étape 1 — La maquette — **commencée le 2026-08-31**

> **Fait :** le fil des textes en cours, classés par étape du parcours, sur
> **données réelles** (1 990 textes de la 17e législature). Dans
> `maquette/` — `feed.html` (page autonome) et `preparer_donnees.py`.
>
> **Reste à faire dans cette étape :** l'écran de suivi d'un texte, la
> recherche, l'étoile « suivre » et l'écran des favoris.

**But :** un écran qu'on peut mettre entre les mains de quelqu'un et
regarder s'il comprend.

- **L'écran de suivi d'un texte** : son titre en français simple, où il en
  est aujourd'hui, et la frise de son parcours — étapes passées, étape en
  cours, étapes à venir, dans les deux chambres.
- **Une liste de textes** avec une recherche, et l'étoile « suivre ».
- **L'écran « mes favoris »** : les textes suivis, et ce qui a bougé.
- **Sur données réelles mais partielles** : une vingtaine de textes,
  récupérés une fois pour toutes, pas de mise à jour automatique.

**Pourquoi cet ordre :** l'écran de parcours est la partie du produit dont
personne ne sait encore si elle est compréhensible pour un non-spécialiste.
C'est donc elle qu'il faut tester en premier, pas la tuyauterie.

**Piège à éviter :** vouloir des données complètes et à jour pour la
maquette. Vingt textes figés suffisent à savoir si l'écran fonctionne.

### Étape 2 — Récupérer et stocker (le socle) — **faite le 2026-08-31**

> **Décidé le 2026-08-31 : cette étape passe avant l'application.** Sans elle,
> un téléphone devrait télécharger et décortiquer une archive de 10 Mo à
> chaque ouverture, et la future version web ne pourrait lire aucune donnée.
>
> **Livré**, dans `../socle/` : le programme quotidien (`recuperer.py`), la
> base (SQLite, modèle du §3.1), le serveur qui la sert à l'application
> (`serveur.py`, avec l'en-tête qui débloque le web), et 21 tests sur le
> classement des étapes.
>
> **Périmètre couvert :** les dossiers législatifs, comme le plan le
> prévoyait. Les parlementaires, les scrutins et les débats restent à faire.
>
> **Ce qui manque encore :** le déclenchement quotidien. Le programme est
> prêt et la ligne de `cron` est documentée, mais il faut une machine qui
> l'exécute — c'est la question 8 du §10, l'hébergement.

**But :** avoir chez nous, à jour tous les jours, une copie propre des
données publiques des deux chambres.

- Un programme qui télécharge les jeux de données et les range dans une base.
- Il tourne tous les jours, tout seul, et ne retélécharge que ce qui a changé.
- Il garde une trace de ce qu'il a fait (pour qu'une panne se voie).
- **Le modèle de données est celui du §3.1** : un dossier, des étapes
  datées, chacune rattachée à une chambre.

**Commencer par :** dossiers législatifs des deux chambres + parlementaires
+ scrutins. Les débats, très volumineux, viennent après.

### Étape 3 — La vraie application — **en Flutter, mobile d'abord**

**But :** la maquette de l'étape 1, mais sur données complètes et à jour.

**Technologie arrêtée le 2026-08-31 :** Flutter, un seul code pour mobile et
web. **On livre le mobile ; le web vient ensuite.** Ce que cela implique sur
le besoin d'un serveur est décrit à la question 7 du §10.

- Tous les textes en cours, dans les deux chambres.
- Une fiche par parlementaire : groupe, commission, ses votes lors des
  scrutins publics.
- Une fiche par scrutin : sujet, résultat, qui a voté quoi, détail par
  groupe politique.
- L'agenda de la semaine.

**À ce stade, tout ce qui est affiché vient directement du Parlement** —
aucun texte écrit par une machine, donc aucun risque d'erreur de notre fait.

### Étape 4 — Alerter (ce qui transforme un site en service)

**But :** l'utilisateur n'a plus besoin de venir voir ; on lui dit quoi.

- Être prévenu quand un texte suivi franchit une étape. **C'est la suite
  directe des favoris**, et la fonctionnalité la plus attendue.
- Suivre un parlementaire.
- Suivre un mot-clé (« logement », « intelligence artificielle ») dans les
  débats et les amendements.
- Une lettre d'information hebdomadaire, automatique.

**Question à trancher avant de commencer :** par quel canal ? Notification
mobile, e-mail, les deux ? Le choix a des conséquences sur les comptes
utilisateurs (§7).

### Étape 5 — Résumer (la partie difficile)

**But :** « voici ce qui s'est passé hier au Parlement, en dix lignes ».

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

### Étape 6 et au-delà — pistes, non engagées

- Suivre le parcours d'un amendement : qui l'a déposé, ce qu'il est devenu.
- Statistiques sur la durée : présence, discipline de vote au sein d'un
  groupe, sujets qui reviennent.
- Suivi vidéo / temps réel (voir §8.5).

---

## 7. Les favoris et le suivi personnalisé

Les favoris ont l'air d'un détail d'interface. Ce sont en réalité la
décision la plus structurante du produit après le périmètre, parce qu'ils
obligent à stocker quelque chose **par personne**.

### 7.1 Trois niveaux, à choisir en connaissance de cause

| Niveau | Ce que ça donne | Ce que ça coûte |
|---|---|---|
| **A — Sur l'appareil** | Les favoris sont enregistrés dans le téléphone ou le navigateur | Presque rien. Pas de compte, pas de données personnelles, **pas de RGPD**. Mais on perd ses favoris en changeant d'appareil, et le web et le mobile ne se parlent pas |
| **B — Compte utilisateur** | Les favoris suivent la personne d'un appareil à l'autre | Inscription, mots de passe, base de données de comptes, **obligations RGPD**, suppression de compte, sécurité |
| **C — Compte + notifications** | On peut prévenir la personne quand son texte bouge | Tout le niveau B, plus la gestion des envois et du consentement |

### 7.2 Recommandation

**Commencer au niveau A pour la maquette.** Les favoris sur l'appareil
suffisent entièrement à tester si l'idée plaît, et ils évitent d'ouvrir le
chantier RGPD avant d'être sûr du produit.

**Mais concevoir dès maintenant comme si on passerait au niveau B**, c'est-à-
dire garder la liste des favoris dans un seul endroit du code, facile à
remplacer par un appel au serveur plus tard. Le niveau C n'a de sens qu'à
l'étape 4.

**Le point à ne pas manquer :** dès qu'on veut des notifications, il faut
des comptes. La décision « on veut prévenir les gens » et la décision « on
gère des données personnelles » sont la même décision.

---

## 8. Les difficultés, en détail

### 8.1 Tous les votes ne sont pas enregistrés

À l'Assemblée comme au Sénat, la plupart des votes se font à main levée et
ne laissent aucune trace nominative. Seuls les **scrutins publics** donnent
la liste de qui a voté quoi.

**Conséquence produit :** sur la fiche d'un texte, il faut dire clairement
« ce vote a eu lieu à main levée, le détail par élu n'existe pas » plutôt
que de laisser un blanc que l'utilisateur interprétera mal.

### 8.2 « Important » est maintenant un choix de l'utilisateur

**Ce point a changé en v2.** La v1 traitait « quels votes sont importants ? »
comme un problème éditorial à trancher par nous, avec une règle à écrire et
à assumer.

**La décision prise est plus simple et meilleure : c'est l'utilisateur qui
désigne ce qui compte, en mettant des textes en favoris.** Nous n'avons pas à
hiérarchiser l'actualité parlementaire à sa place.

Il reste un cas où la question revient, mais beaucoup plus petit : **le
classement de la liste de textes** que voit quelqu'un qui n'a encore rien
mis en favoris. Là, quelques critères simples et transparents suffisent —
activité récente, textes en séance cette semaine, scrutins solennels — et la
règle doit être affichée, jamais cachée derrière un calcul opaque.

### 8.3 Le volume des débats

Une journée de séance représente un texte très long, et il y a de l'ordre de
150 jours de séance par an et par chambre. Cela pose deux questions : le
stockage (peu coûteux) et le traitement par un modèle de langage (voir §9).
Ce n'est pas bloquant, mais cela impose de **ne pas tout traiter en une
seule fois** : découper par sujet ou par intervention, ce que la structure
du compte rendu permet puisqu'elle identifie les orateurs et les sujets.

### 8.4 Le risque d'erreur sur un sujet politique

C'est le risque principal du projet, plus que la technique. Un résumé qui
attribue à un élu une position qu'il n'a pas prise, sur un sujet sensible,
est un problème sérieux — juridique autant que de réputation. Les règles de
l'étape 5 ne sont pas des précautions de style : ce sont les conditions pour
que le produit soit publiable.

### 8.5 Le temps réel

Suivre la séance en direct supposerait de traiter la vidéo ou l'audio des
débats. C'est un projet à part entière, avec ses propres difficultés (qualité
de la transcription, identification des orateurs, coût continu). **À exclure
du plan actuel.** Le délai de moins de 3 heures du compte rendu analytique
offre déjà une fraîcheur très correcte.

### 8.6 Les changements de législature

Les données de l'Assemblée sont organisées par législature, et les archives
des législatures passées sont séparées des données courantes. Une
application conçue uniquement autour de « la législature en cours » se
cassera au prochain renouvellement. Le Sénat, dont la base remonte à 1977,
ne se comporte pas de la même façon. **À prévoir dès le modèle de données**,
pas après.

### 8.7 Deux chambres, deux modes de fonctionnement

Le Sénat n'est pas une copie de l'Assemblée : renouvellement par moitié,
règles de séance différentes, et une base de données de structure et de
profondeur historique différentes. **Ne pas supposer qu'un traitement écrit
pour une chambre marchera sur l'autre en changeant l'URL.**

---

## 9. Coûts

### 9.1 Ce qui est gratuit

Toutes les données sources. Les portails des deux chambres sont gratuits et
sans inscription ; l'API Légifrance est gratuite mais demande la création
d'un compte PISTE.

### 9.2 Hébergement

Faible tant qu'il n'y a pas beaucoup d'utilisateurs : un petit serveur, une
base de données, du stockage. À chiffrer une fois la technologie choisie.
Les comptes utilisateurs (§7, niveau B) ajoutent une base à sauvegarder et
à sécuriser.

### 9.3 Les résumés automatiques — moins chers qu'attendu

C'est la seule dépense qui grandit avec l'usage. Prix de l'API Claude, par
million de jetons (un « jeton » est à peu près trois quarts de mot) —
**vérifiés le 2026-08-31** :

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

**Mesuré le 2026-08-31**, sur les comptes rendus réellement publiés :

| | Assemblée | Sénat |
|---|---:|---:|
| Texte par unité publiée | 198 000 caractères **par séance** | 462 000 caractères **par journée** |
| Unités en 2025 | 314 séances | 126 journées |
| Volume 2025 | 63,1 M caractères | 67,4 M caractères |

**Une année entière de débats des deux chambres : 130,5 millions de
caractères, soit environ 34,8 millions de jetons.** Au tarif d'entrée, avec
le traitement par lots :

| Modèle | Coût pour une année de débats |
|---|---:|
| Claude Haiku 4.5 | **17 $** |
| Claude Sonnet 5 | **35 $** |
| Claude Opus 5 | **87 $** |

**La conclusion de cette section se renforce :** on parle de **dizaines**
d'euros par an, pas de centaines. Le coût des résumés **n'est pas le facteur
limitant du projet** — la qualité et la vérification le sont.

*(Détail du calcul dans `sources/README.md`. Le nombre de jetons est estimé à
3,75 caractères par jeton, ordre de grandeur pour du français.)*

---

## 10. Décisions prises

| # | Question | Décision | Date |
|---|---|---|---|
| 1 | **Pour qui ?** | Grand public curieux | 2026-08-31 |
| 2 | **Sous quelle forme ?** | Plateforme unique, mobile **et** web — **mobile d'abord**, web ensuite, dans le même code | 2026-08-31 |
| 3 | **Personnel ou général ?** | Personnel — chacun choisit ses favoris. Voir §7 pour la mise en œuvre progressive | 2026-08-31 |
| 4 | **Périmètre** | **Assemblée + Sénat**, suivi complet | 2026-08-31 |
| 5 | **Budget et rythme** | Maquette testable d'abord ; le reste ensuite | 2026-08-31 |
| 6 | **Fonctionnalité à tester en premier** | Le suivi d'un texte sur toute sa durée de vie | 2026-08-31 |
| 7 | **Technologie** | **Flutter**, un seul code pour mobile et web. **On se concentre sur le mobile ; le web viendra plus tard** | 2026-08-31 |

#### Ce que le choix de Flutter implique

Deux conséquences, constatées à l'étape 0, à connaître avant d'écrire du code.
Elles ne remettent pas le choix en cause : elles disent quand un serveur
devient nécessaire.

1. **Le web ne sera pas gratuit.** Flutter partage bien le code entre mobile et
   web, c'est son intérêt. Mais une application Flutter **web** s'exécute dans
   un navigateur : elle se heurtera au même refus que la maquette HTML
   d'aujourd'hui, puisque `data.assemblee-nationale.fr` et `data.senat.fr`
   n'envoient pas l'en-tête `Access-Control-Allow-Origin`. **L'application
   mobile, elle, n'a pas cette limite.** Le jour où l'on passe au web, il
   faudra un serveur intermédiaire.
2. **Le mobile s'en passera moins longtemps qu'il n'y paraît.** Les dossiers
   législatifs forment une archive de 10 Mo contenant 10 000 fichiers. Un
   téléphone ne peut pas la télécharger et la décortiquer à chaque ouverture.

**Recommandation, non encore tranchée :** faire venir l'**étape 2** (un
service qui prépare et sert les données) **avant** l'application, plutôt
qu'après. À défaut, l'application embarquera des données préparées à
l'avance, comme la maquette.

### Encore ouvert

| # | Question | Quand la trancher |
|---|---|---|
| 8 | **Hébergement** | Dès que l'étape 2 est engagée — le choix de Flutter la rend nécessaire plus tôt que prévu (voir ci-dessus) |
| 9 | **Modèle économique** (gratuit, payant, associatif) | Pas urgent, et **plus contraint par les licences** : la seule source en ODbL était La Fabrique de la Loi, écartée à l'étape 0 (§4.4). L'Assemblée et le Sénat publient sous des licences qui n'imposent rien à la redistribution |

---

## 11. Points d'attention pour le dépôt lui-même

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

## 12. Prochaine étape immédiate

**L'étape 0 est faite** (2026-08-31, résultats dans `sources/`). Elle a
tranché les deux questions qui commandaient tout : La Fabrique de la Loi est
inutilisable, et le rapprochement entre les deux chambres est déjà fait par
l'Assemblée. La maquette peut donc se construire sur données réelles.

1. **L'application Flutter**, sur le socle. C'est l'étape 3, et plus rien ne
   la bloque : les données sont servies, le modèle est stable.
2. **Trouver où faire tourner le socle** — question 8 du §10. Le programme
   quotidien existe mais rien ne le déclenche.
3. **Compléter le socle** si le besoin s'en fait sentir : parlementaires,
   scrutins, puis les débats.
4. **Si et seulement si le texte consolidé des lois devient nécessaire** :
   créer un compte PISTE et évaluer l'API Légifrance.

---

## Journal des mises à jour

| Date | Version | Ce qui a changé |
|---|---|---|
| 2026-08-31 | **v3.2** | **Étape 2 faite, et placée avant l'application** comme décidé. Le socle est dans `socle/` : programme quotidien, base SQLite au modèle du §3.1, serveur JSON avec l'en-tête qui débloquera la version web, 21 tests. Le code de lecture des dossiers, écrit pour la maquette, y a été déplacé — la maquette s'appuie dessus et produit exactement les mêmes données qu'avant. Découverte au passage, inscrite dans la fiche de l'Assemblée : l'archive est servie par plusieurs machines qui ne publient pas la même génération, ce qui oblige à comparer le contenu et pas seulement les en-têtes. |
| 2026-08-31 | **v3.1** | **Technologie décidée : Flutter**, un seul code pour mobile et web, **le mobile d'abord** (question 7 du §10, qui était la dernière question bloquante). Deux conséquences inscrites au §10 : l'application Flutter *web* butera sur le même refus que la maquette HTML et exigera un serveur, tandis que le mobile n'a pas cette limite ; et l'archive de 10 Mo ne peut pas être décortiquée sur un téléphone à chaque ouverture. D'où une recommandation, non tranchée : faire venir l'étape 2 avant l'application. |
| 2026-08-31 | **v3** | **Étape 0 faite** : les fichiers des deux chambres ont été téléchargés et comptés. Fiches par source dans `sources/`. Trois conclusions changent le plan — **La Fabrique de la Loi est écartée** (figée depuis 2022, §4.4) ; **le recollement entre les deux chambres n'est pas à faire**, l'Assemblée publie le lien (§3.2) ; **le coût des résumés est de l'ordre de 35 $ par an** pour les deux chambres, mesuré, pas estimé (§9.3). §5 réécrit : ce qui est mesuré, ce qui ne l'est pas. §12 : la maquette peut commencer sur données réelles. |
| 2026-08-31 | v2 | Décisions prises intégrées (§10) : grand public, mobile + web, favoris, **Assemblée + Sénat**, maquette d'abord. Nouveau §3 sur le parcours d'une loi et le recollement entre les deux chambres. Nouveau §7 sur les favoris et le RGPD. §4 étendu au Sénat, à Légifrance et à La Fabrique de la Loi. §6 réordonné : la maquette passe avant la récupération des données. §8.2 réécrit : « important » devient un choix de l'utilisateur. Tarifs de l'API Claude vérifiés. Accès réseau retesté : toujours bloqué côté session, et la marche à suivre pour le débloquer est désormais dans `ACCES-RESEAU.md`. |
| 2026-08-31 | v1 | Création : étude de faisabilité et plan initial. Sources vérifiées par recherche web uniquement — accès direct aux portails bloqué par le réseau. |

---

## Sources consultées

### Assemblée nationale
- Portail open data — <https://data.assemblee-nationale.fr/>
- Travaux parlementaires (jeux de données) — <https://data.assemblee-nationale.fr/travaux-parlementaires>
- Dossiers législatifs — <https://data.assemblee-nationale.fr/archives-16e/dossiers-legislatifs>
- Réunions — <https://data.assemblee-nationale.fr/reunions>
- Foire aux questions du portail — <https://data.assemblee-nationale.fr/foire-aux-questions>
- Fiche de synthèse n°56 : Les votes à l'Assemblée nationale — <https://www.assemblee-nationale.fr/dyn/synthese/fonctionnement-assemblee-nationale/travail-legislatif/les-votes-a-l-assemblee-nationale>
- Fiche de synthèse n°30 : Les comptes rendus — <https://www.assemblee-nationale.fr/dyn/synthese/organisation-assemblee-nationale/les-comptes-rendus>
- Communiqué d'ouverture du site open data — <https://www.assemblee-nationale.fr/presse/communiques/20150622-01.asp>

### Sénat
- Portail open data — <https://data.senat.fr/>
- La base DOSLEG — <https://data.senat.fr/dosleg/>
- Liste des dossiers législatifs — <https://data.senat.fr/aide/liste-des-dossiers-legislatifs/>
- Données — <https://data.senat.fr/donnees/>
- Foire aux questions — <https://data.senat.fr/faq/>
- Ouverture du site open data du Sénat — <https://data.senat.fr/le-senat-ouvre-son-site-open-data/>
- Travaux législatifs (Sénat) sur data.gouv.fr — <https://www.data.gouv.fr/datasets/travaux-legislatifs-senat>
- La navette parlementaire — <https://www.senat.fr/connaitre-le-senat/role-et-fonctionnement/la-navette-parlementaire.html>

### État
- Open data et API de Légifrance — <https://www.legifrance.gouv.fr/contenu/pied-de-page/open-data-et-api>
- API Légifrance sur data.gouv.fr — <https://www.data.gouv.fr/dataservices/legifrance>
- Inscription au portail PISTE — <https://piste.gouv.fr/registration>
- Comptes rendus des débats sur data.gouv.fr — <https://www.data.gouv.fr/datasets/comptes-rendus-des-debats-de-l-assemblee-nationale>
- Organisation « Assemblée nationale » sur data.gouv.fr — <https://www.data.gouv.fr/organizations/assemblee-nationale/datasets>

### Projets existants
- La Fabrique de la Loi — <https://www.regardscitoyens.org/la-fabrique-de-la-loi/>
- API de La Fabrique de la Loi — <https://www.lafabriquedelaloi.fr/api/HEADER.html>
- La Fabrique de la Loi reprend du service — <https://www.regardscitoyens.org/la-fabrique-de-la-loi-reprend-du-service/>
- Applications utilisant les données du Sénat — <https://data.senat.fr/applications/>
- Documentation de l'API NosDéputés.fr — <https://github.com/regardscitoyens/nosdeputes.fr/blob/master/doc/api.md>
- Données parlementaires en open data (Regards Citoyens) — <https://github.com/regardscitoyens/nosdeputes.fr/blob/master/doc/opendata.md>
- Scrutins publics, Civiqo — <https://www.civiqo.fr/scrutins>
- Votes de l'Assemblée nationale, CIVIX — <https://www.civix.fr/votes-assemblee-nationale>

### Tarifs
- Tarifs de l'API Claude — <https://claude.com/pricing#api>
