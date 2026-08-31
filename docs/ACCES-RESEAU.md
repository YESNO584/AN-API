# Débloquer l'accès aux sites du Parlement depuis une session Claude Code

**Dernière mise à jour :** 2026-08-31

## Le problème en une phrase

Les sessions Claude Code qui tournent dans le cloud ne peuvent joindre que
les sites d'une liste d'autorisations, et les portails du Parlement n'y sont
pas — donc aucune session cloud ne peut ouvrir les fichiers de données du
projet tant que ce réglage n'est pas changé.

**Ce n'est pas une question de pays.** Le filtrage se fait par nom de site,
pas par localisation. Travailler « depuis la France » ne change rien ; ce
qui change tout, c'est le niveau d'accès réseau de l'environnement.

---

## Le réglage

Il s'appelle **Network access** et appartient à **l'environnement**, pas à
la session. L'environnement par défaut, nommé `Default`, est au niveau
**Trusted** : dépôts de paquets et GitHub autorisés, rien d'autre.

### Où le trouver

Dans l'application (mobile, bureau ou web) : **l'icône de nuage qui affiche
le nom de l'environnement, dans la barre juste au-dessus de la zone de
saisie**. Survoler l'environnement, puis toucher l'icône de réglages qui
apparaît à droite.

**Il n'y a pas de page de paramètres séparée ni d'adresse directe** — cette
icône est le seul chemin.

### Les quatre niveaux

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

## La liste à coller

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

### Trois pièges à éviter

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

### Ce qui n'est pas affecté

**GitHub continue de fonctionner quel que soit le niveau choisi**, y compris
`None` : il passe par un chemin séparé. Changer ce réglage ne peut donc pas
vous couper du dépôt.

---

## Vérifier que ça a marché

Dans une **nouvelle** session, demander :

```
Teste l'accès à data.senat.fr et data.assemblee-nationale.fr
```

Attendu : un code HTTP `200`. Si la réponse est `CONNECT tunnel failed,
response 403`, le domaine n'est pas passé — vérifier l'orthographe dans la
liste, et que la nouvelle session tourne bien dans l'environnement modifié.

Le détail de chaque refus est lisible avec :

```bash
curl -sS "$HTTPS_PROXY/__agentproxy/status"
```

Le champ `recentRelayFailures` nomme chaque site refusé et la raison. C'est
plus fiable que d'interpréter un code d'erreur `curl`, qui masque le corps
de la réponse quand la connexion échoue.

---

## À quoi sert chaque domaine

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

## Une autre voie : l'environnement « bridge »

Un environnement de type *bridge* exécute la session **sur votre propre
machine**, donc sur votre réseau, sans passer par le filtrage décrit
ci-dessus. Il apparaît dans le même sélecteur que les environnements cloud.

**Avantage :** aucun réglage à faire, tous les sites sont joignables.
**Contrainte :** la machine doit être allumée et connectée pendant toute la
session.

C'est une solution de repli valable si la liste `Custom` pose problème.

---

## Si rien de tout cela n'est possible

L'étape 0 du plan est essentiellement du téléchargement de fichiers. Elle se
fait très bien à la main, depuis un navigateur, sans aucun outil : ouvrir
`lafabriquedelaloi.fr`, récupérer `dossiers.csv`, regarder la date du texte
le plus récent. Cela répond en quelques minutes à la question qui conditionne
tout le reste du projet.
