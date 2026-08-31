# La Fabrique de la Loi — à écarter

**Vérifié le 2026-08-31.**

## La conclusion en une phrase

**Le projet est figé : ses données s'arrêtent en janvier 2022, il ne couvre
donc ni la législature en cours ni la précédente** — il ne peut pas servir à
suivre l'actualité législative.

C'est l'inverse de ce que supposait le plan, qui en faisait la piste n° 1
(« stratégie A ») et estimait que si elle tenait, la maquette était « à
quelques jours ».

## Ce qui a été mesuré

L'API répond, le site sert les fichiers — **le problème n'est pas technique,
c'est le contenu qui s'arrête.**

| Vérification | Résultat |
|---|---|
| `dossiers.csv` téléchargé | 623 Ko, 1 530 dossiers |
| Dossier le plus récent | **11 janvier 2022** |
| Dossiers promulgués | 1 042, le dernier en **avril 2021** |
| Législatures couvertes | jusqu'à la **15e** (2017-2022). Aucun texte des 16e ni 17e |
| Répertoires publiés | 1 818 |
| Dernière modification, tous répertoires confondus | **juillet 2024**, et il s'agissait des dossiers `stats/` et `logs/` |
| Dernière modification d'un dossier de texte | **mars 2024**, sur des répertoires temporaires de la 15e législature |

Répartition des répertoires par année de dernière modification :
1 307 en 2020, 265 en 2021, 98 en 2022, 121 en 2023, 27 en 2024, **aucun
depuis**.

La législature en cours est la **17e**. Elle est absente en totalité.

## Ce qui reste utile

Deux choses, malgré tout :

1. **Son modèle d'étapes est bien conçu et vaut d'être copié.** Le fichier
   `procedure.json` de chaque texte décrit les étapes ainsi :

   ```
   date         institution   stage           step
   2021-12-27   assemblee     1ère lecture    depot
   2021-12-30   assemblee     1ère lecture    commission
   2022-01-03   assemblee     1ère lecture    hemicycle
   ```

   Trois axes — **quand, quelle chambre, quelle étape** — plus un champ
   `id_opendata` qui pointe vers la donnée officielle. C'est exactement la
   forme dont un affichage de parcours a besoin, et elle se retrouve dans
   l'open data de l'Assemblée.

2. **Comme point de comparaison historique**, si l'on veut un jour vérifier
   un traitement sur la période 2008-2022.

## La question de licence ne se pose plus

Le plan s'inquiétait de l'ODbL, qui oblige à repartager toute base dérivée
sous la même licence, et « contraint un éventuel produit commercial ».
**Puisque la source est écartée, la contrainte disparaît** : l'Assemblée et
le Sénat publient sous Licence Ouverte, nettement plus permissive.

C'est un effet secondaire favorable d'une mauvaise nouvelle.

## Deux sources associées, hors service

Au moment du test, les deux sites d'où La Fabrique tire ses données étaient
eux-mêmes en panne, ce qui va dans le même sens :

- `www.nosdeputes.fr` — erreur 500 du serveur
- `www.nossenateurs.fr` — certificat de sécurité expiré

Détail dans `../ACCES-RESEAU.md`.
