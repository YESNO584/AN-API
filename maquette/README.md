# Maquette — le fil des textes en cours

**Étape 1 du plan** (`../docs/PLAN.md`, §6). Un écran qu'on peut mettre entre
les mains de quelqu'un pour regarder s'il comprend.

Un seul fichier : **`feed.html`**. Il s'ouvre dans un navigateur, au format
téléphone.

## Ce qu'elle montre

Les **1 990 textes de loi en cours d'examen**, groupés par étape du parcours,
**les plus avancés en premier** — un texte près d'être promulgué intéresse
plus qu'une proposition déposée et jamais examinée, et celles-ci sont
l'immense majorité.

### Les filtres

| Filtre | Ce qu'il permet |
|---|---|
| **Étape** | Les six étapes du parcours |
| **Où le texte se trouve** | Assemblée, Sénat, ou les deux (commission mixte paritaire) |
| **Nature du texte** | Proposition, projet, loi organique, constitutionnelle, budget, ratification… |
| **Dernier mouvement** | Cette semaine, ce mois-ci, ces trois mois — ou à l'arrêt depuis plus d'un an |
| **Calendrier** | Les textes dont une séance est déjà programmée |
| **Recherche** | Dans les titres |

Ils se combinent, chacun affiche son nombre de textes, ceux qui ne mèneraient
à rien sont grisés, et un bouton efface tout.

### Les explications

**Chaque élément affiché se touche et explique ce qu'il est**, en français
simple : l'étape, la chambre, la nature du texte, la lecture, le dernier
acte, le résultat d'un vote, la date, la frise, et chaque filtre.

Sur un téléphone il n'y a ni survol de souris ni clic droit : l'explication
s'ouvre donc **au toucher**, dans un panneau qui vient du bas. Dans le
panneau des filtres, un petit **ⓘ** à côté de chaque puce évite de confondre
« je veux comprendre » et « je veux filtrer ».

## D'où viennent les données

De **`https://yesno584.github.io/AN-API/textes.json`**, publié chaque matin
par le socle (voir `../socle/README.md`). La page les lit en direct, au
chargement — c'est exactement le chemin que suivra l'application Flutter,
donc la maquette essaie le dispositif autant que le dessin.

Il n'y a **plus de préparation hors ligne** : le script qui servait à cela a
disparu, le socle publie tout.

### Viser un socle local

```
feed.html?socle=http://127.0.0.1:8000
```

Utile pour travailler sans réseau, ou pour essayer une modification du socle
avant de la publier. Pour servir une copie locale :

```bash
cd ../socle && ./publier.py && (cd public && python3 -m http.server 8000)
```

En ouvrant alors `http://127.0.0.1:8000/feed.html?socle=http://127.0.0.1:8000`
après y avoir copié la page, tout tient sur une seule adresse.

## Ce que la maquette ne fait pas

Ni favoris, ni alertes, ni comptes, ni écran de détail par texte — le titre
renvoie au dossier officiel. Ce sont les étapes suivantes du plan.

## Les trois règles qui font que le fil est juste

Elles ne sont pas ici : elles vivent dans `../socle/extraction.py`, avec
leurs tests. En résumé — les dossiers qui ne fabriquent pas de loi sont
écartés, une saisine de commission le jour du dépôt n'est pas un examen, et
un texte se classe sur les actes de son jour le plus récent, pas sur l'étape
la plus avancée qu'il ait jamais atteinte. Détail dans
`../socle/README.md`.
