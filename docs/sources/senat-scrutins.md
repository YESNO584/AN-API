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

## Ce qui reste à trancher avant d'écrire une ligne de code

- **La licence.** `data.senat.fr` a la sienne ; ces pages sont sur
  `senat.fr`, et rien ne dit qu'elle s'y applique. À vérifier.
- **La politesse.** Une lecture par jour, d'une page de 29 Ko, avec un
  `User-Agent` qui nomme le projet. Rien qui ressemble à une aspiration.
- **Où la ranger.** Ce n'est pas une archive mais une page : elle n'a pas sa
  place parmi les `SOURCES` du socle telles qu'elles sont écrites aujourd'hui,
  qui supposent toutes un fichier à télécharger et à ouvrir.
