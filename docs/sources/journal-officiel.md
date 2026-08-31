# Journal officiel — le texte des lois promulguées (DILA)

**Vérifié le 2026-08-31.** Chiffres relevés sur 66 archives quotidiennes
réellement téléchargées.

## Deux adresses, une seule qui marche

| Adresse | Résultat |
|---|---|
| `legifrance.gouv.fr` — celle que publie l'Assemblée dans ses données | **403.** Page « Just a moment… » : protection anti-robot. Le proxy ne signale aucune erreur : c'est bien Légifrance qui refuse |
| **`echanges.dila.gouv.fr/OPENDATA/JORF/`** | **200.** L'open data officiel du Journal officiel, à jour de la veille |

Il n'y a donc pas à créer de compte ni à passer par l'API PISTE pour obtenir
le texte d'une loi promulguée.

## Ce qu'on y trouve

Des archives `tar.gz` :

- **un socle** : `Freemium_jorf_global_20250713-140000.tar.gz`, **1,6 Go** ;
- **deux archives par jour** depuis, de 100 ko à 10 Mo — 446 pour la seule
  année 2026.

Chaque texte s'y lit en deux fichiers XML :

- `texte/struct/…/JORFTEXT<id>.xml` — la nature (`LOI`, `DECRET`, `ARRETE`),
  le **numéro** de la loi, le **NOR**, la date, et la liste ordonnée de ses
  articles ;
- `article/…/JORFARTI<id>.xml` — le texte de chaque article, dans un
  `<BLOC_TEXTUEL>`.

## Le raccordement est déjà fait

Chaque loi porte deux clés que notre base contient déjà :

```
<NUM>2026-813</NUM>          →  dossier.loi_numero
<NOR>ECOX2602236L</NOR>      →  dossier.loi_url_jo (paramètre numjo)
```

Vérifié : la loi n° 2026-813 du Journal officiel correspond bien au dossier
« Protéger les mineurs des risques auxquels les expose l'utilisation des
réseaux sociaux ».

## Ce qu'il apporte, et lui seul

Le texte publié **signale les dispositions censurées** par le Conseil
constitutionnel, à leur place exacte :

> [Dispositions déclarées non conformes à la Constitution par la décision du
> Conseil constitutionnel n° 2026-911 DC du 14 août 2026.]

Aucune autre source ne dit à la fois ce que le Parlement a voté et ce que le
Conseil a retiré.

## Ce qu'il n'apporte pas

**Un diff contre le texte d'origine n'aurait pas de sens.** Sur 26 lois de
2026 comparées article par article au texte déposé, 77 % des articles portent
le même numéro mais **15 % seulement ont le même contenu** : un texte est
renuméroté de fond en comble pendant son parcours. Voir
[`../QUE-VOTE-T-ON.md`](../QUE-VOTE-T-ON.md).

Comparé au **dernier texte adopté**, le rapprochement monte à 67 % — l'écart
restant vient surtout des textes dont la dernière lecture a eu lieu au Sénat,
dont le texte final n'est donc pas celui de l'Assemblée.

## Ce que ça coûterait

| | |
|---|---:|
| Lois promulguées dans notre base | 107 |
| dont postérieures au socle du 2025-07-13 | 75 |
| Archives quotidiennes à lire pour ces 75 | ≈ 150, de 100 ko à 10 Mo |
| Pour les 32 autres | le socle de **1,6 Go** |

Les archives quotidiennes contiennent tout le Journal officiel, pas seulement
les lois : sur une journée prise au hasard, **2 lois pour 46 arrêtés, 12
décrets et 22 avis**. Il faut donc les décompresser pour en extraire peu de
chose — 66 archives pèsent 242 Mo compressées et 5,2 Go décompressées.

Aucune dépendance nouvelle : `tar` et la bibliothèque standard suffisent.
