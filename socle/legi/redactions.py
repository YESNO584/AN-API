"""Les rédactions successives d'un article : laquelle est « d'avant », ce que chaque loi lui a fait, quand cela prend effet — et tout ce qu'on retient d'une rédaction.
"""
from __future__ import annotations

from legi.ajouts import est_un_ajout, loi_qui_porte, sans_les_renvois
from legi.balises import _LIEN, _LIEN_ART, _TITRE_TXT, attributs, champ, nettoyer, normaliser
from legi.etats import CHANGEMENTS, SANS_DATE, SANS_FIN


def versions(xml: str) -> list[dict[str, str]]:
    """Toutes les rédactions de l'article, telles que le fichier les liste.

    **La liste n'est pas dans l'ordre chronologique** et contient des rédactions
    qui ne sont jamais entrées en vigueur.
    """
    return [attributs(balise) for balise in _LIEN_ART.findall(champ(xml, "VERSIONS"))]


def est_mort_ne(etat: str) -> bool:
    """Une rédaction votée mais jamais appliquée (`MODIFIE_MORT_NE`, `ABROGE_MORT_NE`)."""
    return etat.endswith("MORT_NE")


def version_precedente(toutes: list[dict[str, str]], debut: str,
                       soi: str | None = None) -> str | None:
    """La rédaction d'« avant » : celle qui se termine quand la nôtre commence.

    C'est **la** règle du module, et la règle évidente est fausse. Prendre
    « celle d'avant dans la liste » désigne parfois une rédaction mort-née :
    sur l'article 6 de la loi n° 2004-575, elle renvoyait à une version datée
    du 22 février 2222, jamais appliquée. La comparaison tombait alors à 13 %
    de texte commun — un avant/après spectaculaire et faux. Avec la règle
    ci-dessous : 97 %, et rien ne change pour les six autres articles de la
    même loi (mesuré le 2026-09-01).

    Deux autres pièges, trouvés le 2026-09-03 en cherchant les articles propres
    des lois. Les deux viennent de la date sentinelle `2999-01-01` :

    - **elle n'est pas une frontière.** Un article dont l'entrée en vigueur
      n'est pas encore fixée la porte en `debut` *et* en `fin`. « Celle qui
      finit quand la nôtre commence » désigne alors n'importe quelle rédaction
      encore en vigueur — or une rédaction qui n'a pas commencé n'a pas d'avant ;
    - **un article n'est pas sa propre rédaction d'avant.** Dans ce même cas,
      la liste des versions contient l'article lui-même, avec `fin == debut`.
      Sans le contrôle `soi`, **61 des 130 articles** des lois d'août 2026 se
      donnaient eux-mêmes pour leur « avant ».

    `soi` est l'identifiant de l'article dont on cherche l'avant. Il est
    facultatif pour ne pas casser les appels qui ne l'ont pas, mais
    `lire_article` le passe toujours.
    """
    if debut == SANS_FIN:
        return None
    for version in toutes:
        if (version.get("fin") == debut and version.get("id") != soi
                and not est_mort_ne(version.get("etat", ""))):
            return version.get("id")
    return None


def changements(xml: str) -> list[dict[str, str]]:
    """Les textes qui ont agi sur cet article, et ce qu'ils lui ont fait.

    Seuls les liens `sens="cible"` disent « ce texte a agi sur moi » ; les
    liens `sens="source"` disent l'inverse et ne nous concernent pas.
    """
    trouves = []
    for balise in _LIEN.findall(champ(xml, "LIENS")):
        lien = attributs(balise)
        if (lien.get("sens") == "cible" and lien.get("typelien") in CHANGEMENTS
                and lien.get("numtexte")):
            trouves.append({"loi": lien["numtexte"], "quoi": lien["typelien"],
                            "article_loi": lien.get("num", "")})
    return trouves


def ou_se_trouve(xml: str, debut: str) -> str:
    """Le code ou la loi qui porte cet article, en clair (« Code de l'éducation »).

    Le fichier propose plusieurs intitulés, valables sur des périodes
    différentes, dont un daté de la sentinelle `2999-01-01` qui n'est pas le
    bon. On garde celui qui couvre la date d'entrée en vigueur.
    """
    titres = [attributs(balise) for balise in _TITRE_TXT.findall(champ(xml, "CONTEXTE"))]
    for titre in titres:
        if titre.get("debut", SANS_FIN) <= debut < titre.get("fin", SANS_FIN):
            return titre.get("c_titre_court", "")
    return titres[-1].get("c_titre_court", "") if titres else ""


def lire_article(xml: str) -> dict:
    """Tout ce qu'on retient d'une rédaction d'article."""
    debut = champ(xml, "DATE_DEBUT")
    identifiant = champ(champ(xml, "META_COMMUN"), "ID")
    precedent = version_precedente(versions(xml), debut, identifiant)
    bloc = champ(xml, "BLOC_TEXTUEL")
    ajout = est_un_ajout(xml, precedent)
    return {
        "id": identifiant,
        "numero": normaliser(champ(xml, "NUM")),
        "ou": ou_se_trouve(xml, debut),
        "etat": champ(xml, "ETAT"),
        "debut": debut,
        "fin": champ(xml, "DATE_FIN"),
        # Un article que la loi a écrit se montre sans ses renvois ; un article
        # de code se montre entier, parce qu'il sera comparé.
        "texte": sans_les_renvois(bloc) if ajout else nettoyer(bloc),
        "nota": nettoyer(champ(xml, "NOTA")),
        "precedent": precedent,
        "changements": changements(xml),
        # La loi dont cet article **est** un article — à ne pas confondre avec
        # celles qui l'ont changé, qui sont dans `changements`.
        "loi_porteuse": loi_qui_porte(xml),
        "ajout": ajout,
    }


def date_d_effet(quoi: str, debut: str | None, fin: str | None) -> str | None:
    """Quand ce changement prend effet — la date qui intéresse le lecteur.

    Ce n'est pas la même selon ce que la loi fait. Une modification crée une
    rédaction, et c'est son **début** qui compte. Une abrogation, elle, ne crée
    rien : elle met **fin** à une rédaction, et c'est cette fin qui est la date
    de l'abrogation.

    Prendre le début dans les deux cas donnait des absurdités : l'article 1700
    du code général des impôts, abrogé par la loi de finances de 2025,
    s'affichait comme entrant en vigueur le 1er juillet **1979** — la date à
    laquelle le texte abrogé avait commencé à s'appliquer.

    Avec cette règle, sur 2 261 changements datés, seuls 34 (1,5 %) prennent
    effet avant la promulgation de leur loi — et ce sont de vraies
    rétroactivités : une loi de finances votée en février abroge des taxes au
    1er janvier. C'est un fait à montrer, pas une anomalie à masquer.

    Rend `None` quand la date n'est **pas encore fixée** (`SANS_DATE`) : la loi
    renvoie à un décret qui n'est pas paru. Afficher « 22 février 2222 » serait
    absurde ; le dire est utile.
    """
    date = fin if quoi == "ABROGE" else debut
    return None if not date or date in (SANS_DATE, SANS_FIN) else date


def etat_du_precedent(precedent: str | None, texte_avant: str | None) -> str:
    """Dit **pourquoi** il n'y a pas de comparaison, quand il n'y en a pas.

    Trois cas, qu'il serait malhonnête de confondre :

    - `connu` — on a la rédaction d'avant, on peut superposer ;
    - `aucun` — l'article n'en avait pas : la loi vient de le créer ;
    - `manquant` — il en avait une, et nous ne l'avons pas retrouvée dans les
      archives lues. C'est un trou dans nos données, pas un fait sur la loi,
      et l'afficher comme un « texte nouveau » ferait mentir l'application.
    """
    if texte_avant:
        return "connu"
    return "manquant" if precedent else "aucun"
