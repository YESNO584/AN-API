# Légifrance — ce qu'on peut en tirer, et ce qu'on ne peut pas

**Deux constats, à deux dates.** L'API (compte PISTE) reste **non
vérifiée** — c'est la première partie, du 2026-08-31. L'onglet « comparer
les versions » du site, lui, est **mesuré** — c'est la seconde partie, du
2026-09-01, et elle conclut.

# L'API Légifrance (PISTE) — non vérifié

## Pourquoi cette partie ne conclut pas

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

---

# L'onglet « Comparer les versions » de Légifrance

**Mesuré le 2026-09-01.** Réponse courte : **il compare deux versions du droit
déjà en vigueur, et il n'est pas exploitable par un programme — mais il ne
montre rien que nous ne sachions déjà calculer nous-mêmes, gratuitement.**

## Ce qu'il compare — et ce qu'il ne compare pas

L'onglet est présent sur les pages d'**article de code ou de texte
consolidé**. Il propose la liste des rédactions successives de cet article et
en superpose deux, avec un code couleur.

Vérifié sur la page de l'article : les versions y sont désignées par un
identifiant `LEGIARTI…` et une date, et l'adresse d'une version a la forme
`legifrance.gouv.fr/codes/article_lc/<LEGIARTI…>/<date>`.

**Il ne compare pas les versions successives d'un texte en cours de navette.**
Les dossiers législatifs de Légifrance renvoient d'ailleurs désormais
(redirection 302) vers `vie-publique.fr`, qui ne propose pas non plus de
comparaison : seulement des liens vers les documents de l'Assemblée et du
Sénat. La question « qu'est-ce que les parlementaires ont changé ? » reste donc
traitée par `monalisa.md` et `textes-pdf-assemblee.md`, pas par Légifrance.

## Atteignable d'ici ? Non

| Ce qui a été essayé | Résultat |
|---|---|
| `curl` sur `legifrance.gouv.fr`, **`robots.txt` compris** | **403**, en-têtes `server: cloudflare` et `cf-mitigated: challenge`, corps « Just a moment… » |
| Les dossiers législatifs | redirection 302 vers `vie-publique.fr` |
| `curl` sur `vie-publique.fr` | 200, mais un corps de 232 octets : « This website requires JS enabled and cookies » |
| API PISTE, `…/consult/getArticle` | **405** — le point d'entrée existe, il attend une requête d'un autre type et un jeton |
| Description publique de l'API (swagger) sans compte | **400** partout |

Le refus vient bien du site, pas de notre réseau : c'est le pare-feu
anti-robots de Cloudflare. Le franchir demanderait de résoudre son défi
automatiquement — ce que ce projet ne fait pas.

L'API officielle reste inaccessible pour la raison déjà notée plus haut : elle
demande un compte et une clé, qu'une session Claude Code ne peut pas créer.

## Pourquoi ce n'est pas grave

**Le fonds que cet onglet affiche est publié en libre accès, sans compte, sous
le nom LEGI.** La fiche officielle du jeu de données le dit :

> « Les versions modifiées ou abrogées sont présentes dans le fonds
> documentaire au même titre que les versions en vigueur. »

Et les paires avant/après que nous avons déjà calculées sont désignées par les
**mêmes identifiants `LEGIARTI…`** que les pages de Légifrance — les deux
regardent le même fonds.

| | Légifrance | Ce que nous avons déjà |
|---|---|---|
| Ce qu'on obtient | une comparaison à l'écran, deux versions à la fois | **2 446 paires avant/après**, calculées d'un coup |
| Accès | bloqué aux robots | fichiers en libre accès |
| Compte, clé | oui pour l'API | aucun |
| Mise en forme | choisie par Légifrance | la nôtre |

Voir [`droit-consolide.md`](droit-consolide.md) pour la mesure complète.

**À retenir : Légifrance est une façon de *regarder* ces données, pas une
source supplémentaire.** Il n'y a rien à en tirer que LEGI ne donne pas.
