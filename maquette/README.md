# Maquette — le fil des textes en cours

**Étape 1 du plan** (`../docs/PLAN.md`, §6). Un écran qu'on peut mettre entre
les mains de quelqu'un pour regarder s'il comprend.

## Ce qu'il y a ici

| Fichier | À quoi il sert |
|---|---|
| `feed.html` | **La maquette.** Un fichier autonome : on l'ouvre dans un navigateur, il s'affiche. Aucune connexion, aucune dépendance |
| `preparer_donnees.py` | Le script qui remplit `feed.html` avec les données réelles de l'Assemblée |

## L'ouvrir

Double-cliquer sur `feed.html`, ou :

```bash
xdg-open feed.html      # Linux
open feed.html          # macOS
```

## Rafraîchir les données

```bash
./preparer_donnees.py
```

Le script télécharge l'archive des dossiers législatifs (10 Mo), en extrait
les textes en cours, et réécrit le bloc de données à l'intérieur de
`feed.html`. Tout le reste de la page — la mise en page, les styles — n'est
pas touché : on peut donc modifier le design à la main sans rien perdre.

```bash
./preparer_donnees.py --garder-zip     # garde l'archive dans .cache/
./preparer_donnees.py --zip fichier    # réutilise une archive déjà là
```

## Pourquoi un script, et pas la page qui va chercher les données

**Parce que les sites l'interdisent.** Ni `data.assemblee-nationale.fr` ni
`data.senat.fr` n'envoient l'en-tête `Access-Control-Allow-Origin` (vérifié
le 2026-08-31). Un navigateur refuse donc à une page de lire leurs fichiers.
Ce n'est pas contournable côté page — seuls ces sites peuvent changer ce
réglage.

S'y ajoutent deux obstacles pratiques : le fichier de l'Assemblée est une
archive compressée de 10 Mo contenant 10 000 fichiers, et celui du Sénat est
en latin-1.

Pour que les données se mettent à jour toutes seules, il faudra un programme
qui tourne quelque part et récupère les fichiers — c'est l'**étape 2** du
plan, pas la maquette.

## Les trois décisions qui font que le fil est juste

Ce sont les pièges trouvés à l'étape 0. Chacun est traité dans
`preparer_donnees.py`, avec un commentaire à l'endroit du code concerné.

1. **Tous les dossiers ne fabriquent pas une loi.** 708 des 2 859 dossiers de
   la législature sont des résolutions, rapports d'information, missions ou
   commissions d'enquête. Ils sont écartés : les mélanger à un fil de lois le
   rendrait faux.

2. **Une saisine de commission n'est pas un examen.** Un texte est renvoyé à
   une commission le jour même de son dépôt, automatiquement. Compter ce
   renvoi comme « en commission » classerait 1 815 textes sur 1 990 à cette
   étape, alors que la commission ne s'est jamais réunie sur presque aucun.
   Il faut un acte réel : nomination d'un rapporteur, réunion, ou rapport.

3. **Le parcours n'est pas une ligne droite.** Après une commission mixte
   paritaire qui échoue, un texte repart en nouvelle lecture. Classer sur
   « l'étape la plus avancée jamais atteinte » l'afficherait en sortie de
   navette alors qu'il est reparti chez l'autre chambre. On classe donc sur
   les actes du **jour le plus récent**, en retenant le plus avancé d'entre
   eux quand plusieurs partagent cette date.

Un quatrième point, visible dans la page : **la source contient des dates
futures** — des séances déjà programmées. Elles ne servent jamais à classer
un texte ; elles apparaissent comme « prochaine étape prévue ».

## Ce que la maquette ne fait pas

Ni recherche, ni favoris, ni écran de détail par texte, ni mise à jour
automatique. Ce sont les écrans voisins prévus au plan, à faire seulement si
celui-ci convainc.

## Source et licence

Dossiers législatifs de l'Assemblée nationale, sous **Licence Ouverte
(Etalab)** — réutilisation libre, y compris commerciale, avec mention de la
source. Détail dans `../docs/sources/assemblee-nationale.md`.
