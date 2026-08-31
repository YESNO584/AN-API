# Légifrance via PISTE — non vérifié

**Constaté le 2026-08-31.**

## Pourquoi cette fiche ne conclut pas

**L'API Légifrance demande un compte et une clé d'accès, qu'une session
Claude Code ne peut pas créer.** Le point 3 de l'étape 0 reste donc à faire,
et il vous revient. Ce qui suit est ce qui est visible sans compte.

## Ce qui est établi

| | |
|---|---|
| **Portail d'accès** | `https://piste.gouv.fr` — le site répond (code 200), la page d'inscription aussi |
| **Adresse de l'API** | `https://sandbox-api.piste.gouv.fr` pour l'environnement d'essai |
| **Conditions d'accès** | **« Accès restreint »**, d'après la fiche officielle sur data.gouv.fr. Il faut demander un accès |
| **Limites d'usage** | Quotas d'appels par jeton. Le détail n'est pas public |
| **Producteur** | Premier ministre / DILA |
| **Disponibilité annoncée** | Non communiquée |
| **Documentation** | Swagger, accessible depuis la fiche data.gouv.fr |

Le jeu associé **LEGI** (codes, lois et règlements consolidés) est, lui,
téléchargeable librement et était à jour à deux jours près lors du test.

## Ce que cela change pour le projet — probablement rien

C'est la bonne nouvelle de cette fiche. Le plan gardait Légifrance comme
« stratégie B » : une vue de secours du parcours complet, au cas où le
rapprochement entre les deux chambres échouerait.

**Ce rapprochement n'a pas échoué — il marche à 100 %** (voir
`assemblee-nationale.md`). La stratégie B n'a donc plus de rôle de secours.

Légifrance ne redevient nécessaire que pour une chose : **le texte consolidé
d'une loi une fois promulguée**. C'est utile plus tard, pour l'étape 3 ou
au-delà. Pas pour suivre où en est un texte.

## Ce qu'il faudrait faire, si vous voulez trancher

1. Créer un compte sur `piste.gouv.fr/registration` et obtenir une clé.
2. Interroger un dossier législatif récent, et regarder deux choses :
   **le parcours complet y est-il ?** et **à quelle fraîcheur ?**
3. Comparer au même dossier vu depuis l'open data de l'Assemblée.

Tant que ce n'est pas fait, **ne pas écrire dans le plan que Légifrance
couvre le parcours** : ce n'est pas vérifié.
