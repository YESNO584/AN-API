# Monalisa — le texte de loi lui-même, en XML (Sénat)

**Mesuré le 2026-08-31.** Chiffres relevés sur les fichiers réellement
téléchargés ce jour-là : les 1 113 textes adoptés, plus les 449 versions
intermédiaires des dossiers concernés.

Adresse : `https://www.senat.fr/akomantoso/<nom>.akn.xml`
Index : `depots.xml` (textes déposés) et `adoptions.xml` (textes adoptés).

## La conclusion en une phrase

**Monalisa contient le texte complet des lois, article par article, ce qui
permet de calculer une vraie comparaison entre deux versions — mais
seulement du côté Sénat, ce qui représente aujourd'hui 203 de nos 2 859
dossiers.**

## Ce que c'est

Le Sénat publie chaque texte qu'il imprime dans un format XML normalisé
(Akoma Ntoso, la norme internationale des textes de loi). Contrairement au
reste de l'open data, ce n'est pas une fiche *sur* le texte : c'est le texte,
découpé en articles et en alinéas, chacun portant un identifiant.

Chaque fichier porte l'adresse du dossier Sénat correspondant :

```xml
<FRBRalias name="url-senat" value="https://www.senat.fr/dossier-legislatif/ppl25-304.html"/>
```

C'est exactement la clé de rapprochement que le socle utilise déjà
(`extraction.cle_senat`). Le raccordement ne demande donc aucun travail neuf.

Chaque fichier contient aussi le parcours complet du texte, avec un lien vers
chaque version :

```xml
<step date="2025-03-05" outcome="de la commission" href="/akn/fr/pjl/2024/404/fr@"/>
<step date="2025-03-12" outcome="adopté par le Sénat" href="/akn/fr/pjl/2024/TA76/fr@"/>
```

C'est ce qui permet de retrouver toutes les versions d'un même texte sans
deviner leur nom.

## Ce que ça couvre, en chiffres

| Mesure | Nombre |
|---|---:|
| Textes déposés indexés (`depots.xml`) | 3 684 |
| Textes adoptés indexés (`adoptions.xml`) | 1 113 |
| **Nos dossiers** (17e législature) | **2 859** |
| dont portant un lien vers le Sénat | 719 |
| dont la version déposée est chez Monalisa | 692 |
| dont une version adoptée est chez Monalisa | 207 |
| **dont au moins deux versions existent → comparaison possible** | **203** |
| Versions téléchargeables par dossier comparable, en moyenne | 3,4 |

État de ces 203 dossiers : 103 promulgués, 93 en cours, 4 non adoptés,
3 rejetés.

## La limite, et elle est structurelle

**Monalisa ne contient que les versions imprimées par le Sénat.** Pour un
texte né à l'Assemblée, le parcours annonce bien les étapes de l'Assemblée,
mais leurs liens ne mènent à aucun fichier : testé sur 8 dossiers en cours,
les trois premières étapes (dépôt, commission, texte adopté à l'Assemblée)
renvoient une erreur 404, seule l'étape « transmis au Sénat » existe.

Conséquence : un texte qui n'a pas encore atteint le Sénat n'a qu'une seule
version, donc rien à comparer. C'est le cas de 468 de nos dossiers en cours.

Du côté de l'Assemblée, le texte n'existe pas sous forme structurée :

- son open data ne publie que des fiches signalétiques (auteur, dates,
  titre) et un lien vers le fichier ;
- le fichier officiel est un document Word, sur `docparl.assemblee-nationale.fr`,
  **domaine refusé par le proxy de sortie de cette session** ;
- une version PDF est accessible (`.../l17b0621_projet-loi.pdf`, 162 ko).

Reconstituer la comparaison côté Assemblée voudrait donc dire lire des PDF.
C'est un autre métier, avec une autre fiabilité.

## La comparaison : ça marche, et voici comment

Les identifiants d'article (`eId` et `GUID`) sont **stables d'une version à
la suivante**, ce qui permet d'apparier les articles sans se fier à leur
numéro — un article renuméroté reste reconnu.

Mesure sur les 493 paires de versions consécutives des 203 dossiers
(5 030 articles dans la version antérieure) :

| Appariement | Articles | Part |
|---|---:|---:|
| Par identifiant stable | 3 561 | 70,8 % |
| Par numéro d'article (secours) | 777 | 15,4 % |
| **Total apparié** | **4 338** | **86,2 %** |
| Sans correspondance (article supprimé ou refondu) | 692 | 13,8 % |

À quoi s'ajoutent 1 143 articles apparus en cours de route — des ajouts
réels, pas des erreurs.

Trois précautions, mesurées :

1. **Comparer des versions consécutives, jamais les extrêmes.** Entre le
   dépôt et le texte final d'un dossier testé, l'appariement par identifiant
   tombe à 0 : les identifiants sont régénérés quand le texte change de
   chambre. Enchaîner les comparaisons deux à deux marche ; sauter les
   étapes ne marche pas.
2. **Comparer au niveau de l'article, pas de l'alinéa.** Sur un dossier
   testé, 6 articles sur 6 s'apparient par identifiant, mais seulement
   11 alinéas sur 24.
3. **L'appariement de secours par numéro est moins sûr.** 40 % de ces paires
   ont moins de la moitié de leur texte en commun, contre 18 % des paires
   appariées par identifiant : derrière un même numéro se cache parfois un
   article entièrement réécrit — ou un mauvais rapprochement.

## Un exemple réel

Dossier `ppl24-079`, du texte de commission (`ppl24-368`) au texte adopté par
le Sénat (`tas24-066`), article 1er :

> Après l'article L. 541‑10‑20 du code de l'environnement, […] d'incendie.
> « Les modalités d'application du présent article sont précisées
> ~~par décret.~~ **dans les cahiers des charges mentionnés à l'article
> L. 541‑10.** »

Le calcul est une comparaison mot à mot (`difflib`, bibliothèque standard de
Python) : aucune dépendance nouvelle, aucun modèle de langage, aucun coût.

## Ce que ça vaut pour le produit

Ce que Monalisa apporterait, et que rien d'autre n'apporte :

- le **texte complet** d'un projet ou d'une proposition de loi, structuré ;
- la **comparaison réelle** entre deux versions, à afficher en rouge barré
  pour les retraits et en ajout pour le reste — ce que la maquette ne fait
  aujourd'hui que sur les passages cités par les amendements eux-mêmes.

Ce que ça ne remplace pas : la coloration des amendements déjà en place, qui
couvre les textes de l'Assemblée, c'est-à-dire l'essentiel du flux.

Volume à prévoir : 111 Mo pour les 1 113 textes adoptés, soit environ 100 ko
par fichier. Un texte publié ne change plus, donc le téléchargement est
incrémental — seul l'index quotidien est à relire.
