"""Le décor des tests du droit consolidé : un article avec ses versions, une loi avec ses renvois.
"""
from __future__ import annotations

import legi


def article(identifiant="LEGIARTI000000000001", numero="L401-1", debut="2026-09-01",
            fin=legi.SANS_FIN, etat="VIGUEUR", texte="<p>Le texte.</p>",
            contexte=None, versions=(), liens=(), nota="", type_article=""):
    """Un fichier d'article LEGI, réduit à ce que le module lit."""
    if contexte is None:
        contexte = ('<TEXTE nature="CODE"><TITRE_TXT c_titre_court="Code de l\'éducation" '
                    f'debut="2000-01-01" fin="{legi.SANS_FIN}">Code de l\'éducation'
                    "</TITRE_TXT></TEXTE>")
    lignes_versions = "".join(
        f'<VERSION etat="{v["etat"]}"><LIEN_ART debut="{v["debut"]}" '
        f'etat="{v["etat"]}" fin="{v["fin"]}" id="{v["id"]}" num="{numero}"/></VERSION>'
        for v in versions)
    return (
        "<?xml version='1.0' encoding='UTF-8'?><ARTICLE>"
        f"<META><META_COMMUN><ID>{identifiant}</ID></META_COMMUN><META_SPEC>"
        f"<META_ARTICLE><NUM>{numero}</NUM><ETAT>{etat}</ETAT>"
        f"<DATE_DEBUT>{debut}</DATE_DEBUT><DATE_FIN>{fin}</DATE_FIN>"
        f"<TYPE>{type_article}</TYPE>"
        "</META_ARTICLE></META_SPEC></META>"
        f"<CONTEXTE>{contexte}</CONTEXTE>"
        f"<VERSIONS>{lignes_versions}</VERSIONS>"
        f"<NOTA><CONTENU>{nota}</CONTENU></NOTA>"
        f"<BLOC_TEXTUEL><CONTENU>{texte}</CONTENU></BLOC_TEXTUEL>"
        f"<LIENS>{''.join(liens)}</LIENS></ARTICLE>")


def version(identifiant, debut, fin, etat="MODIFIE"):
    return {"id": identifiant, "debut": debut, "fin": fin, "etat": etat}


# Un renvoi tel que Légifrance l'écrit : une annonce, puis la liste des
# articles visés dans un `<blockquote>` imbriqué.
RENVOI = ("<p>A modifié les dispositions suivantes :</p>"
          "<blockquote>- Code rural et de la pêche maritime<blockquote>"
          " Art. L230-5-1, Art. L230-5-6</blockquote></blockquote>")


def loi(numero="2026-796", titre=None, nature="LOI", debut="2026-08-20"):
    """Le `CONTEXTE` d'un article porté par une loi, et non par un code."""
    titre = titre or f"LOI n°{numero} du 18 août 2026"
    return (f'<TEXTE nature="{nature}" num="{numero}" nor="AGRS2603566L" '
            f'cid="JORFTEXT000054707007"><TITRE_TXT c_titre_court="{titre}" '
            f'debut="{debut}" fin="{legi.SANS_FIN}">{titre}</TITRE_TXT></TEXTE>')


# Un lien de modification tel que LEGI l'écrit, l'action laissée à remplir.
LIEN = ('<LIEN cidtexte="JORFTEXT000054707332" num="14" numtexte="2026-798" '
            'sens="cible" typelien="{}">LOI n°2026-798 - art. 14</LIEN>')
