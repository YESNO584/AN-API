# Accès réseau aux sites du Parlement depuis une session Claude Code

**Dernière mise à jour :** 2026-08-31 (accès vérifié le même jour)

## L'état actuel en une phrase

**L'accès fonctionne** : depuis une session cloud, les portails de
l'Assemblée, du Sénat, de data.gouv.fr et de PISTE répondent normalement —
aucun réglage n'est à faire aujourd'hui.

Ce document a d'abord été écrit à un moment où ces sites étaient bloqués. Ce
n'est plus le cas. Il garde donc deux rôles :

1. **Constater l'état vérifié** (section suivante) — y compris les trois
   sites qui ne répondent pas, pour une raison qui leur appartient et qu'aucun
   réglage ne corrigera.
2. **Servir de mode d'emploi si le blocage revient** — dans un nouvel
   environnement, ou après un changement de réglage. Toute la partie
   « Débloquer » plus bas est là pour ça.

**Ce n'est jamais une question de pays.** Quand un blocage existe, le
filtrage se fait par nom de site, pas par localisation. Travailler « depuis
la France » ne change rien ; ce qui change tout, c'est le niveau d'accès
réseau de l'environnement.

---

## État vérifié le 2026-08-31

Les 30 adresses citées dans `docs/` ont été testées une par une, plus les
domaines racines de la liste d'autorisations. Le proxy sortant ne signale
**aucun domaine refusé** : sa liste des rejets récents est vide.

### Ce qui répond

| Site | Résultat |
|---|---|
| `data.assemblee-nationale.fr` (5 pages) | 200 |
| `www.assemblee-nationale.fr` (4 pages) | 200 |
| `data.senat.fr` (7 pages) | 200 |
| `www.senat.fr` | 200 |
| `piste.gouv.fr`, dont `/registration` | 200 |
| `www.data.gouv.fr` (4 pages) | 200 |
| `www.regardscitoyens.org` (3 pages) | 200 |
| `www.civiqo.fr`, `www.civix.fr` | 200 |
| `www.lafabriquedelaloi.fr/api/` | 200 |
| GitHub (`git ls-remote`) | fonctionne |

### Les trois exceptions

Elles échouent **à cause du site distant**, pas du réseau. Ajouter un domaine
à une liste d'autorisations ne les réparera pas.

| Site | Ce qui se passe | Conséquence |
|---|---|---|
| `www.nossenateurs.fr` | Certificat de sécurité expiré (3 essais sur 3) | Inutilisable tant que l'association ne le renouvelle pas |
| `www.nosdeputes.fr` | Erreur 500 : le serveur répond mais son application plante | Inutilisable pour l'instant |
| `www.lafabriquedelaloi.fr` (page d'accueil) | Instable : 1 réponse correcte sur 3, sinon coupure ou délai dépassé | Réessayer suffit. Son répertoire `/api/`, celui dont le projet a besoin, répond bien |

Ces trois sites sont des **sources de contrôle**, pas des sources
principales : le projet peut avancer sans eux. Voir `PLAN.md`, §4.

### Un cas à ne pas confondre

`www.legifrance.gouv.fr` renvoie `403`. **Ce n'est pas un blocage réseau** :
le site est bien atteint, il refuse simplement les requêtes automatisées
(filtre anti-robot). L'accès aux données de Légifrance passe de toute façon
par l'API PISTE, qui répond.

---

## Débloquer, si le blocage revient

### Le réglage

Il s'appelle **Network access** et appartient à **l'environnement**, pas à
la session. L'environnement par défaut, nommé `Default`, est au niveau
**Trusted** : dépôts de paquets et GitHub autorisés, rien d'autre.

#### Où le trouver

Dans l'application (mobile, bureau ou web) : **l'icône de nuage qui affiche
le nom de l'environnement, dans la barre juste au-dessus de la zone de
saisie**. Survoler l'environnement, puis toucher l'icône de réglages qui
apparaît à droite.

**Il n'y a pas de page de paramètres séparée ni d'adresse directe** — cette
icône est le seul chemin.

#### Les quatre niveaux

| Niveau | Ce qui passe |
|---|---|
| **None** | Rien |
| **Trusted** | Le niveau par défaut : dépôts de paquets, GitHub, SDK cloud |
| **Full** | N'importe quel site |
| **Custom** | Votre propre liste, en plus ou à la place de Trusted |

**Choisir `Custom`.** `Full` fonctionne aussi, mais autorise tout ; `Custom`
donne le même résultat pour ce projet en gardant la maîtrise de ce que la
session peut joindre.

---

### La liste à coller

Dans le champ **Allowed domains**, un domaine par ligne :

```
assemblee-nationale.fr
*.assemblee-nationale.fr
senat.fr
*.senat.fr
legifrance.gouv.fr
*.legifrance.gouv.fr
piste.gouv.fr
*.piste.gouv.fr
data.gouv.fr
*.data.gouv.fr
lafabriquedelaloi.fr
*.lafabriquedelaloi.fr
regardscitoyens.org
*.regardscitoyens.org
nosdeputes.fr
*.nosdeputes.fr
nossenateurs.fr
*.nossenateurs.fr
```

#### Trois pièges à éviter

1. **Cocher « Also include default list of common package managers ».**
   Sans cette case, la liste ci-dessus *remplace* la liste Trusted au lieu
   de la compléter : plus de dépôts de paquets, donc plus d'installation
   possible.
2. **Les doublons ne sont pas une erreur.** `*.senat.fr` couvre les
   sous-domaines comme `data.senat.fr`, mais **pas** `senat.fr` tout court.
   Il faut les deux lignes.
3. **Le changement ne s'applique pas à la session en cours.** La politique
   réseau est lue au démarrage du conteneur. Il faut **ouvrir une nouvelle
   session** pour en profiter.

#### Ce qui n'est pas affecté

**GitHub continue de fonctionner quel que soit le niveau choisi**, y compris
`None` : il passe par un chemin séparé. Changer ce réglage ne peut donc pas
vous couper du dépôt.

---

### À quoi sert chaque domaine

| Domaine | Pourquoi il est dans la liste |
|---|---|
| `assemblee-nationale.fr` | Portail open data de l'Assemblée, et le site lui-même |
| `senat.fr` | Portail open data du Sénat (base DOSLEG) |
| `legifrance.gouv.fr` | Dossiers législatifs côté État |
| `piste.gouv.fr` | Portail d'accès à l'API Légifrance (inscription et clé) |
| `data.gouv.fr` | Miroirs et jeux de données complémentaires |
| `lafabriquedelaloi.fr` | Le parcours des textes à travers les deux chambres |
| `regardscitoyens.org` | L'association qui publie La Fabrique de la Loi |
| `nosdeputes.fr`, `nossenateurs.fr` | Données d'activité des élus, utiles comme référence de contrôle |

Le détail de chaque source est dans `PLAN.md`, §4.

---

### Une autre voie : l'environnement « bridge »

Un environnement de type *bridge* exécute la session **sur votre propre
machine**, donc sur votre réseau, sans passer par le filtrage décrit
ci-dessus. Il apparaît dans le même sélecteur que les environnements cloud.

**Avantage :** aucun réglage à faire, tous les sites sont joignables.
**Contrainte :** la machine doit être allumée et connectée pendant toute la
session.

C'est une solution de repli valable si la liste `Custom` pose problème.

---

### En dernier recours

Si un jour aucun de ces chemins n'est disponible : l'étape 0 du plan est
essentiellement du téléchargement de fichiers. Elle se fait très bien à la
main, depuis un navigateur, sans aucun outil : ouvrir
`lafabriquedelaloi.fr`, récupérer `dossiers.csv`, regarder la date du texte
le plus récent. Cela répond en quelques minutes à la question qui conditionne
tout le reste du projet.

---

## Revérifier l'accès

Le test est automatisé. Dans une session, demander :

```
Vérifie l'accès aux sites cités dans docs/
```

L'agent `doc-url-reachability-checker` (dans `.claude/agents/`) relève toutes
les adresses du dossier `docs/`, les teste une par une, et surtout **dit qui
est en cause** : le filtrage réseau, ou le site lui-même. C'est la distinction
qui compte, et celle qu'on se trompe le plus souvent à faire.

Si l'on préfère vérifier à la main, deux repères :

- Un `CONNECT tunnel failed, response 403` signifie que le domaine n'est pas
  passé le filtre — vérifier son orthographe dans la liste, et que la session
  tourne bien dans l'environnement modifié.
- Le détail de chaque refus est lisible avec :

  ```bash
  curl -sS "$HTTPS_PROXY/__agentproxy/status"
  ```

  Le champ `recentRelayFailures` nomme chaque site refusé et la raison. C'est
  plus fiable que d'interpréter un code d'erreur `curl`, qui masque le corps
  de la réponse quand la connexion échoue. **Vide = aucun blocage réseau**, et
  les échecs qui restent viennent alors des sites eux-mêmes.

Trois pièges de mesure, appris en testant :

1. **Un seul échec ne prouve rien.** Toujours refaire l'essai en série avant
   de conclure : `lafabriquedelaloi.fr` alterne entre réponse correcte et
   coupure.
2. **Ne pas lancer trop de requêtes en parallèle** (6 au maximum). Au-delà,
   les coupures observées sont provoquées par le test lui-même.
3. **Un `403` n'est pas un blocage réseau.** C'est le plus souvent un filtre
   anti-robot du site : réessayer en se présentant comme un navigateur.
