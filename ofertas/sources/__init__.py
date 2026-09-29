from . import amazon, aliexpress, mercadolivre, shopee


def detectar_fonte(url: str):
    """Retorna o módulo da plataforma dona da URL, ou None."""
    for mod in (amazon, aliexpress, shopee, mercadolivre):
        if mod.e_link(url):
            return mod
    return None