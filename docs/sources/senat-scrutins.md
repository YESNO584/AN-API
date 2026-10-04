# Les scrutins du Sénat — comment les collecter, et que faire quand ça casse

**Mesuré le 2026-10-04.** Les commandes qui produisent ces chiffres sont dans
`tmp/senat/` (`m16.py` à `m24.py`).

Le lien entre un scrutin du Sénat et son dossier n'est pas dans l'open data :
il est sur les **pages de scrutins publics du site**. Pourquoi, et ce que ça
permet d'afficher : voir
[`../CE-QUE-LE-SENAT-APPORTERAIT.md`](../CE-QUE-LE-SENAT-APPORTERAIT.md), § 4.
Ce document-ci ne traite que d'une chose : **comment aller les chercher tous
les jours sans que l'application en dépende.**

## En trois chiffres

| | |
|---|---:|
| Coût d'une collecte quotidienne | **29 Ko, moins d'une seconde** |
| Coût d'une reprise de tout l'historique (20 sessions, depuis 2006) | 581 Ko, 15 secondes |
| Part du téléchargement quotidien actuel que ça représente | **0,007 %** (412 Mo aujourd'hui) |

C'est négligeable. La question du coût ne se pose pas ; celle de la solidité,
si.

## Une page par session, et une seule bouge

Le Sénat publie une page par session parlementaire,
`senat.fr/scrutin-public/scr<année>.html`. Il y en a **20**, de 2006-2007 à
aujourd'hui, listées dans le menu de chacune.

**Les sessions passées sont figées.** Vérifié : trois pages de sessions
closes, relues à quarante minutes d'intervalle, sont **identiques à l'octet
près**. Elles n'ont donc à être lues qu'une fois.

**Seule la page de la session en cours change.** C'est elle, et elle seule,
qu'il faut relire chaque jour — 29 Ko compressés, 0,65 seconde.

| | Pages | Transféré | Temps |
|---|---:|---:|---:|
| Tous les jours | 1 | 29 Ko | 0,7 s |
| Une fois, au premier remplissage | 20 | 581 Ko | 15 s |
| À chaque rentrée parlementaire (nouvelle session) | 1 de plus | 29 Ko | 0,7 s |

### Le serveur ne sait pas dire « rien n'a changé »

Les archives de l'Assemblée répondent « 304 » quand rien n'a bougé, et le
socle s'en sert pour économiser 10 Mo. **Ces pages-ci ne le permettent pas** :
aucun en-tête `ETag`, aucun `Last-Modified`, et une requête conditionnelle
renvoie la page entière. Chaque lecture est donc un téléchargement complet —
de 29 Ko, ce qui ne change rien.

**Toujours demander la compression** (`Accept-Encoding: gzip`) : la page fait
285 Ko en clair et 29 Ko compressée, soit huit fois moins.

## La fréquence peut-elle être élargie ? Oui, mais ça ne rapporte rien

Le Sénat ne vote au scrutin public **qu'un jour sur quatre environ** — 53 à 97
jours par an selon les années. Entre deux jours de scrutin : **un jour en
médiane, sept au neuvième décile**, et jusqu'à 127 jours pendant les vacances
parlementaires. Seuls 20 intervalles sur 297 depuis 2023 dépassent une semaine.

| Lecture | Ce qu'on économise | Ce qu'on perd |
|---|---|---|
| **Quotidienne** | — | rien |
| Hebdomadaire | 6 lectures de 29 Ko par semaine, soit **174 Ko** | un vote peut rester **jusqu'à 7 jours** invisible |

**Je ne la recommande pas**, pour trois raisons :

1. **L'économie est nulle** : 174 Ko par semaine, dans une chaîne qui en
   télécharge 412 **méga**-octets par jour.
2. **Elle coûterait du code** : la publication tourne tous les matins. Ne lire
   cette source qu'un jour sur sept demanderait un cas particulier, et un cas
   particulier est une chose qui casse.
3. **Elle décale l'application de sa source.** Le reste du site est à jour du
   matin ; cette rubrique-là aurait jusqu'à une semaine de retard, sans que
   rien ne le dise.

**En revanche, l'élargissement qui a du sens est ailleurs** : ne relire les 19
pages de sessions passées **qu'une fois**, puisqu'elles sont figées. C'est là
qu'est l'économie réelle — 552 Ko sur 581 — et elle est gratuite.

## Ce sur quoi la lecture s'appuie : deux formes d'adresse, rien d'autre

C'est le point qui décide de la solidité. Une page web se refait ; **son
système d'adressage, non**.

La lecture n'a besoin que de reconnaître deux motifs :

```
  /2025/scr2025-340.html              ← un scrutin, sa session et son numéro
  /dossier-legislatif/pjl25-689.html  ← le dossier qu'il concerne
```

et d'une seule règle : **chaque scrutin prend le dossier cité avant le scrutin
suivant.**

**Vérifié** : cette lecture, qui ne connaît ni balise, ni classe CSS, ni
formulation, donne **exactement le même résultat** que celle qui s'appuie sur
la mise en page — 340 scrutins sur 340 pour la session en cours, et les mêmes
totaux sur les cinq sessions essayées.

**À ne pas faire** : s'appuyer sur `<p class="my-2">`, sur le mot « consulter
le dossier législatif », ou sur `<span class="badge">`. Ce sont des choix de
mise en page, qui changent sans prévenir. Les adresses, elles, sont le
vocabulaire du Sénat.

## Ce que les deux sources ne se disent pas

La page donne le lien ; les chiffres du vote et les 1,66 million de votes
nominatifs viennent, eux, du fichier d'open data. Les deux moitiés doivent
donc se recouper. Mesuré sur cinq sessions, 1 445 scrutins :

| | |
|---|---:|
| Scrutins présents dans le fichier et absents de la page | **0** |
| Scrutins présents sur la page et absents du fichier | 21 |
| …dont des scrutins **portant un lien vers un dossier** | **0** |
| **Scrutins rattachés à un dossier et présents dans le fichier** | **1 424 sur 1 424 — 100 %** |

Autrement dit : **tout scrutin qui porte un lien vers un dossier a ses chiffres
dans l'open data.** Les 21 autres sont des déclarations du Gouvernement et des
votes que le fichier ne porte pas — ils n'ont pas de dossier, donc rien à
afficher.

Les deux sources avancent aussi au même rythme : le dernier scrutin de la page
et celui du fichier sont tous deux du 21 juillet 2026.

## Une seconde page du site : les groupes politiques

**Lue le 2026-10-04**, et c'est la **seule** source qui donne la couleur et le
nom complet d'un groupe du Sénat. `ODSEN_GENERAL.csv` ne porte que des codes,
et le dump n'a pas de table de groupes.

| | |
|---|---|
| **Adresse** | `https://www.senat.fr/vos-senateurs/groupes-politiques.html` |
| **Poids** | 163 Ko, une fois par jour — 0,2 % du coût quotidien du projet |
| **Où** | L'attribut `groups` d'un élément `<hemicycle-groups>` |
| **Forme** | Du JSON échappé **deux fois** : entités HTML (`&quot;`) puis séquences `\u00e9` |
| **Ce qu'il porte** | Par groupe : l'identifiant, le nom entier, **la liste des sièges**, la couleur |

**C'est de la donnée, pas de la mise en page** — la règle du projet tient : on
lit l'attribut, jamais le dessin qu'il sert à faire. Le contrôle est celui des
pages de scrutins : une page refaite rend **rien**, pas une moitié.

### Contrôle croisé

Les **neuf** sigles de la page sont les nôtres, et **les neuf effectifs
correspondent un pour un** à ceux de notre base. C'est la meilleure preuve que
la lecture est juste : deux chemins indépendants — un CSV d'open data et une
page web — donnent le même décompte.

### Le plan de salle existe, et il confirme qu'on ne peut pas s'en servir

La page publie le siège de chaque sénateur : **348 numéros**, dont 169 pour les
sénateurs qui ont un groupe (les 179 fraîchement élus portent tous le siège 0,
c'est-à-dire aucun).

Le projet avait écrit qu'aucun plan n'était publié. C'était faux, et la mesure
sur le vrai plan donne la **même conclusion** :

| | Sénat | Assemblée |
|---|---:|---:|
| Changements de groupe en suivant les numéros | **152** | 9 |
| Groupes différents par tranche de 40 numéros | 6 à 8 | 1 à 2 |

**Un numéro de siège au Sénat n'est pas une position.** La numérotation tourne
rang par rang. Placer les sénateurs à leur numéro éparpillerait chaque groupe
sur tout l'arc — c'est pourquoi l'écran du Sénat n'a pas le bouton « par
siège » de l'Assemblée.

## Quand ça casse — et ça cassera

Le Sénat refera sa page un jour. **L'application ne doit pas s'en apercevoir
autrement qu'en le disant.** Le projet a déjà tout ce qu'il faut pour ça : ce
sont les règles des sources facultatives, à appliquer telles quelles.

### Les quatre règles déjà en place

1. **La source est facultative.** Si elle manque, tout le reste se publie
   normalement — le parcours, les votes de l'Assemblée, les lois promulguées.
2. **On réessaie avant de la déclarer absente** — trois essais, vingt secondes
   de pause, comme pour les archives de l'Assemblée.
3. **On garde les données de la veille** au lieu de les effacer. Un scrutin du
   Sénat affiché hier reste affiché aujourd'hui.
4. **`etat.json` publie de quand elles datent**, et la page le dit à l'écran
   dès que ce jour n'est pas celui de la publication.

### La cinquième règle, propre à une page web : le témoin de structure

Une archive qui n'arrive pas se voit : le téléchargement échoue. **Une page
qui a changé de forme, non** : elle arrive, elle pèse son poids, et la lecture
en tire zéro. Sans garde-fou, le socle publierait « aucun vote au Sénat » sur
tous les textes, ce qui serait faux.

Quatre signaux, avec les seuils mesurés :

| Signal | Mesuré aujourd'hui | Ce qui doit déclencher l'alarme |
|---|---|---|
| Nombre de scrutins lus sur une page | 129 à 445 selon la session | **zéro** sur une page qui en portait |
| Part des scrutins portant un lien de dossier | 97 à 100 % | **moins de 90 %** |
| Nombre de scrutins de la session en cours | ne fait que croître | **une baisse** par rapport à la veille |
| Scrutins liés absents du fichier d'open data | 0 sur 1 424 | une **proportion notable** (le fichier a pris du retard) |

**Un témoin qui s'allume n'est pas un échec de publication** : c'est une source
facultative déclarée absente. Le socle garde les données de la veille, la page
affiche leur date, et le journal porte la raison. Personne ne voit une page
cassée ; on voit une rubrique qui date d'avant.

### Ce que l'écran montre, dans chaque cas

| Situation | Ce que l'application affiche |
|---|---|
| Tout va bien | Le vote du Sénat, groupe par groupe |
| La page n'a pas répondu ce matin | Le vote de la veille, **daté** |
| La page a changé de forme | Idem — le témoin l'a vue, les données de la veille tiennent |
| On n'a jamais rien eu pour ce texte | Rien sur le Sénat, et **pas** un « 0 vote » qui serait faux |

C'est exactement ce que le socle fait déjà pour les amendements et les débats
de l'Assemblée.

## La licence — lue le 2026-10-04

**Deux régimes séparés, et aucun des deux textes ne renvoie à l'autre.**

| | Les **fichiers** de `data.senat.fr` | Les **pages** de `www.senat.fr` |
|---|---|---|
| Le texte | [Licence Ouverte 2.0](https://data.senat.fr/licence/) (Etalab) | [Mentions légales](https://www.senat.fr/mentions-legales.html) du site |
| Ce qui est libre | « les données publiées dans des formats ouverts **sur le site Open Data du Sénat (data.senat.fr)** » | « les **travaux parlementaires** ne sont couverts par aucun droit d'auteur » (art. L.122-5 du code de la propriété intellectuelle) |
| Les conditions | citer la paternité : le nom du producteur **et la date de dernière mise à jour** | **trois** : la gratuité de la diffusion, le respect de l'intégrité des documents, et la citation expresse de `www.senat.fr` **avec un lien** |
| Usage commercial | explicitement permis | non traité ; la gratuité est exigée |
| Les photographies | — | **exclues** : « les autres contenus sont couverts par le droit d'auteur […] (photographies, infographies) » |

La licence de l'open data **se borne elle-même à `data.senat.fr`**, dès sa
première phrase. Elle ne couvre donc ni les pages de scrutins publics, ni le
fichier des sénateurs de `senat.fr`, ni les photos.

### Les pages de scrutins publics sont libres, sous trois conditions

Ce sont des travaux parlementaires. Les mentions légales du Sénat sont
explicites : leur reproduction « sous forme papier ou électronique est libre
sous réserve » de trois choses. Le projet en remplit déjà deux, et doit
ajouter la troisième :

| La condition | Où en est le projet |
|---|---|
| **La gratuité de la diffusion** | ✅ Le site est gratuit, sans compte, et le dépôt est public |
| **Le respect de l'intégrité** (aucune modification ni altération) | ✅ C'est déjà la règle du projet : ce qui vient d'une source est recopié mot pour mot |
| **La citation expresse de `www.senat.fr`, avec un lien** | ❌ **À ajouter.** Le pied de page cite l'Assemblée, pas le Sénat |

**Une nuance que je ne tranche pas.** La condition d'intégrité vise la
reproduction d'un *document*. Ici, on n'en reproduirait aucun : on extrairait
d'une page un lien — ce scrutin concerne ce texte — pour afficher des chiffres
qui viennent, eux, de l'open data. Je ne crois pas que ce soit « une
modification ou altération », mais le texte ne le dit pas, et ce n'est pas à
moi d'en décider.

### Le site autorise lui-même la lecture automatisée

`www.senat.fr/robots.txt` dit `Allow: /`, et aucune de ses règles d'exclusion
ne vise `/scrutin-public/`, `/api-senat/` ni `/senimg/`. Rien à demander, donc,
pour lire une page par jour — à condition de rester ce qu'on est : **une
lecture quotidienne de 29 Ko, avec un `User-Agent` qui nomme le projet**. Rien
qui ressemble à une aspiration.

### Ce que la licence change pour les autres pistes du Sénat

- **Les photos des sénateurs : à considérer comme non libres.** Je les avais
  présentées comme utilisables ; les mentions légales nomment explicitement
  les photographies parmi les contenus couverts par le droit d'auteur. **Le
  projet est déjà dans la même situation pour les députés** — leurs photos
  viennent du site de l'Assemblée, pas de l'open data, et `extraction.py` le
  note. Ce n'est donc pas une question nouvelle, c'est la même question
  étendue à une seconde chambre. Elle mérite d'être tranchée pour les deux à
  la fois.
- **Le fichier des sénateurs** (`senat.fr/api-senat/senateurs.json`) est sur le
  site, pas dans l'open data. Une liste de sénateurs avec leur groupe et leur
  siège est-elle un « travail parlementaire » ? Le texte ne le dit pas. Les
  mêmes trois conditions sont ce qu'on peut faire de plus prudent.
- **Tout le reste** — amendements, dossiers, thèmes, débats, scrutins chiffrés —
  vient de `data.senat.fr` et relève de la Licence Ouverte 2.0, sans
  ambiguïté.

### Ce qu'il faudra écrire à l'écran

La Licence Ouverte demande le nom du producteur **et la date de dernière mise
à jour** ; les mentions légales demandent le nom du site **et un lien**. Les
deux se satisfont d'une seule phrase au pied de page, à côté de celle qui cite
déjà l'Assemblée :

> Données du Sénat — [`data.senat.fr`](https://data.senat.fr) sous Licence
> Ouverte 2.0, et [`senat.fr`](https://www.senat.fr) pour les scrutins
> publics. Mises à jour le *(date)*.

## Ce qui reste à trancher avant d'écrire une ligne de code

- **Les photos**, pour les deux chambres à la fois (voir ci-dessus).
- **Où ranger cette source.** Ce n'est pas une archive mais une page : elle n'a
  pas sa place parmi les `SOURCES` du socle telles qu'elles sont écrites
  aujourd'hui, qui supposent toutes un fichier à télécharger et à ouvrir.
