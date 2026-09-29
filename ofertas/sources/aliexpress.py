import html
import logging
import re
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode

from ..models import Oferta

log = logging.getLogger("ofertas.aliexpress")


# ============================================================
# CONFIGURAÇÃO BRASIL
# ============================================================

BASE_URL = "https://pt.aliexpress.com"

PAIS = "BR"
MOEDA = "BRL"
IDIOMA = "pt_BR"
TIMEZONE = "America/Manaus"

CATEGORIAS = [
    "https://pt.aliexpress.com/w/wholesale-electronics.html",
    "https://pt.aliexpress.com/w/wholesale-cell-phone.html",
    "https://pt.aliexpress.com/w/wholesale-computer.html",
    "https://pt.aliexpress.com/w/wholesale-home.html",
]


def e_link(url: str) -> bool:
    """Identifica links do AliExpress."""

    url = (url or "").lower()

    return any(
        dominio in url
        for dominio in (
            "aliexpress.com",
            "a.aliexpress.com",
        )
    )


def _url_brasil(url: str) -> str:
    """
    Converte um link do AliExpress para a versão
    direcionada ao Brasil.

    Mantém os parâmetros existentes e força:
    - país: BR
    - moeda: BRL
    - idioma: pt_BR
    """

    if not url:
        return ""

    url = html.unescape(url).strip()

    if url.startswith("//"):
        url = "https:" + url

    if url.startswith("/"):
        url = urljoin(BASE_URL, url)

    if not e_link(url):
        return url

    try:
        partes = urlsplit(url)

        netloc = "pt.aliexpress.com"

        parametros = dict(
            parse_qsl(
                partes.query,
                keep_blank_values=True,
            )
        )

        parametros["shipTo"] = PAIS
        parametros["currency"] = MOEDA
        parametros["locale"] = IDIOMA
        parametros["gatewayAdapt"] = "glo2bra"

        query = urlencode(
            parametros,
            doseq=True,
        )

        return urlunsplit(
            (
                "https",
                netloc,
                partes.path,
                query,
                "",
            )
        )

    except Exception as e:
        log.debug(
            "Falha ao converter URL para Brasil: %s",
            e,
        )
        return url


def _numero(texto: str) -> float | None:
    """Extrai o primeiro número de preço de um texto."""

    if not texto:
        return None

    texto = html.unescape(texto)

    encontrados = re.findall(
        r"\d+(?:[.,]\d{1,2})?",
        texto,
    )

    if not encontrados:
        return None

    try:
        valor = encontrados[0].replace(",", ".")
        return float(valor)

    except ValueError:
        return None


def _extrair_desconto(
    preco: float | None,
    preco_original: float | None,
) -> int | None:
    """Calcula o percentual de desconto."""

    if (
        preco is None
        or preco_original is None
        or preco_original <= preco
        or preco_original <= 0
    ):
        return None

    desconto = round(
        100 * (1 - preco / preco_original)
    )

    if 0 < desconto < 100:
        return desconto

    return None


def _normalizar_url(url: str) -> str:
    """Transforma uma URL relativa em absoluta."""

    if not url:
        return ""

    url = html.unescape(url).strip()

    if url.startswith("//"):
        return "https:" + url

    if url.startswith("/"):
        return urljoin(BASE_URL, url)

    return url


def _imagem_valida(url: str | None) -> str | None:
    """
    Valida e normaliza uma URL de imagem.

    Só aceita endereços HTTP/HTTPS.
    """

    if not url:
        return None

    url = html.unescape(url).strip()

    if "," in url:
        url = url.split(",")[0].strip()

    url = re.sub(
        r"\s+\d+(?:\.\d+)?x$",
        "",
        url,
    ).strip()

    url = re.sub(
        r"\s+\d+w$",
        "",
        url,
    ).strip()

    url = _normalizar_url(url)

    if not (
        url.startswith("https://")
        or url.startswith("http://")
    ):
        return None

    if len(url) < 15:
        return None

    return url


def _extrair_imagem(img) -> str | None:
    """
    Tenta obter a imagem de várias formas.

    O AliExpress pode colocar a imagem em:
    - src
    - data-src
    - data-lazy-src
    - data-original
    - data-image
    - srcset
    """

    atributos = [
        "src",
        "data-src",
        "data-lazy-src",
        "data-original",
        "data-image",
        "data-img",
        "data-image-url",
        "srcset",
    ]

    for atributo in atributos:
        try:
            valor = img.get_attribute(atributo)
        except Exception:
            continue

        imagem = _imagem_valida(valor)

        if imagem:
            return imagem

    return None


def _limpar_texto(texto: str) -> str:
    """Limpa espaços e quebras de linha."""

    if not texto:
        return ""

    texto = html.unescape(texto)

    texto = re.sub(
        r"\s+",
        " ",
        texto,
    )

    return texto.strip()


def _extrair_preco_da_url(
    url: str,
) -> tuple[float | None, float | None]:
    """
    Tenta extrair os preços presentes no parâmetro
    pdp_npi da URL do AliExpress.

    Exemplo:

    BRL!861.90!369.23

    Primeiro valor = preço original
    Segundo valor = preço atual
    """

    if not url:
        return None, None

    url = html.unescape(url)

    match = re.search(
        r"pdp_npi=[^&]*?BRL%21([^%]+)%21([^%]+)",
        url,
        flags=re.I,
    )

    if not match:
        match = re.search(
            r"pdp_npi=[^&]*?BRL!([^!]+)!([^!]+)",
            url,
            flags=re.I,
        )

    if not match:
        return None, None

    try:
        preco_original = float(
            match.group(1).replace(",", ".")
        )

        preco = float(
            match.group(2).replace(",", ".")
        )

        if (
            preco_original <= 0
            or preco <= 0
        ):
            return None, None

        return (
            preco,
            preco_original,
        )

    except ValueError:
        return None, None


def _extrair_id(url: str) -> str:
    """Extrai o ID do produto do endereço."""

    match = re.search(
        r"/item/(\d+)",
        url,
        flags=re.I,
    )

    if match:
        return match.group(1)

    partes = url.rstrip("/").split("/")

    if partes:
        return partes[-1][:100]

    return url[:100]


def _await_count(locator) -> int:
    """
    Retorna a quantidade de elementos do locator.
    """

    try:
        return locator.count()
    except Exception:
        return 0


def _extrair_cards_playwright(
    page,
    limite: int,
) -> list[dict]:
    """
    Extrai produtos diretamente do DOM renderizado
    pelo navegador.

    Usa vários caminhos de fallback para título,
    imagem e preço.
    """

    resultados: list[dict] = []

    vistos: set[str] = set()

    links = page.locator(
        'a[href*="/item/"]'
    )

    quantidade = min(
        links.count(),
        max(
            limite * 5,
            50,
        ),
    )

    for i in range(quantidade):

        if len(resultados) >= limite:
            break

        try:
            link = links.nth(i)

            href = link.get_attribute("href")

            if not href:
                continue

            url = _normalizar_url(href)

            if "/item/" not in url.lower():
                continue

            # Converte o link para Brasil.
            url = _url_brasil(url)

            produto_id = _extrair_id(url)

            if produto_id in vistos:
                continue

            vistos.add(produto_id)

            # ==================================================
            # TÍTULO
            # ==================================================

            titulo = ""

            try:
                titulo = (
                    link.get_attribute("title")
                    or ""
                )
            except Exception:
                pass

            if not titulo:
                try:
                    titulo = (
                        link.inner_text(
                            timeout=1000
                        )
                        or ""
                    )
                except Exception:
                    pass

            # ==================================================
            # IMAGEM
            # ==================================================

            imagem = None

            try:
                img = link.locator("img").first

                if _await_count(img) > 0:

                    titulo_img = (
                        img.get_attribute("alt")
                        or ""
                    )

                    if not titulo:
                        titulo = titulo_img

                    imagem = _extrair_imagem(img)

            except Exception as e:
                log.debug(
                    "Falha ao extrair imagem "
                    "do produto %s: %s",
                    produto_id,
                    e,
                )

            # ==================================================
            # TEXTO DO CONTEXTO
            # ==================================================

            texto_contexto = ""

            try:
                texto_contexto = (
                    link.locator(
                        "xpath=.."
                    ).inner_text(
                        timeout=1000
                    )
                    or ""
                )
            except Exception:
                pass

            if len(texto_contexto) < 20:
                try:
                    texto_contexto = (
                        link.locator(
                            "xpath=../.."
                        ).inner_text(
                            timeout=1000
                        )
                        or ""
                    )
                except Exception:
                    pass

            texto_contexto = _limpar_texto(
                texto_contexto
            )

            titulo = _limpar_texto(titulo)

            # ==================================================
            # FALLBACK DO TÍTULO
            # ==================================================

            if (
                not titulo
                or len(titulo) < 5
                or titulo.lower()
                in {
                    "produto",
                    "oferta",
                    "aliexpress",
                }
            ):
                if (
                    texto_contexto
                    and len(texto_contexto) >= 10
                ):
                    titulo = texto_contexto

            if len(titulo) > 180:
                titulo = titulo[:180].strip()

            # ==================================================
            # PREÇOS
            # ==================================================

            preco, preco_original = (
                _extrair_preco_da_url(url)
            )

            if preco is None:

                numeros = re.findall(
                    r"(?:R\$\s*)?"
                    r"(\d{1,6}(?:[.,]\d{1,2})?)",
                    texto_contexto,
                )

                valores = []

                for numero in numeros:
                    try:
                        valor = float(
                            numero.replace(
                                ".",
                                "",
                            ).replace(
                                ",",
                                ".",
                            )
                        )

                        if valor > 0:
                            valores.append(valor)

                    except ValueError:
                        continue

                if len(valores) >= 2:

                    preco_original = max(
                        valores[:4]
                    )

                    preco = min(
                        valores[:4]
                    )

                elif len(valores) == 1:

                    preco = valores[0]

            desconto = _extrair_desconto(
                preco,
                preco_original,
            )

            if not titulo:
                titulo = (
                    "Oferta AliExpress "
                    f"{produto_id}"
                )

            imagem = _imagem_valida(imagem)

            resultados.append(
                {
                    "id": produto_id,
                    "url": url,
                    "titulo": titulo,
                    "preco": preco,
                    "preco_original": preco_original,
                    "desconto": desconto,
                    "imagem": imagem,
                }
            )

        except Exception as e:
            log.debug(
                "Falha ao extrair produto %d: %s",
                i,
                e,
            )
            continue

    return resultados


def _criar_contexto_brasil(browser):
    """
    Cria um contexto do Playwright configurado
    explicitamente para o Brasil.

    Isso ajuda o AliExpress a interpretar:
    - país: Brasil
    - moeda: Real brasileiro
    - idioma: Português do Brasil
    - região: Amazonas
    """

    context = browser.new_context(
        viewport={
            "width": 1920,
            "height": 1080,
        },
        locale="pt-BR",
        timezone_id=TIMEZONE,
        extra_http_headers={
            "Accept-Language": (
                "pt-BR,pt;q=0.9,en;q=0.8"
            ),
        },
    )

    try:
        context.add_cookies(
            [
                {
                    "name": "aep_usuc_f",
                    "value": (
                        "site=glo"
                        "&c_tp=BRL"
                        "&region=BR"
                        "&b_locale=pt_BR"
                    ),
                    "domain": ".aliexpress.com",
                    "path": "/",
                }
            ]
        )

    except Exception as e:
        log.debug(
            "Falha ao configurar cookie regional "
            "do AliExpress: %s",
            e,
        )

    return context


def _buscar_com_playwright(
    url: str,
    limite: int,
) -> list[Oferta]:
    """
    Abre uma página pública do AliExpress
    usando Playwright.

    Configurado para Brasil.
    """

    try:
        from playwright.sync_api import (
            sync_playwright,
        )
    except Exception as e:
        raise RuntimeError(
            "Playwright não está disponível: "
            f"{e}"
        )

    ofertas: list[Oferta] = []

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context = _criar_contexto_brasil(browser)

        page = context.new_page()

        try:
            log.info(
                "Abrindo AliExpress em região BR: %s",
                url,
            )

            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            page.wait_for_timeout(7000)

            try:
                page.mouse.wheel(
                    0,
                    2500,
                )

                page.wait_for_timeout(3000)

            except Exception:
                pass

            cards = _extrair_cards_playwright(
                page,
                limite,
            )

            for card in cards:

                ofertas.append(
                    Oferta(
                        plataforma="aliexpress",
                        id_produto=card["id"],
                        titulo=card["titulo"],
                        url_afiliado=card["url"],
                        url_produto=card["url"],
                        preco=card["preco"],
                        preco_original=card[
                            "preco_original"
                        ],
                        desconto_pct=card[
                            "desconto"
                        ],
                        imagem=card["imagem"],
                    )
                )

                if len(ofertas) >= limite:
                    break

        except Exception as e:
            log.error(
                "Erro ao acessar AliExpress "
                "em região BR: %s",
                e,
            )

        finally:
            try:
                context.close()
            except Exception:
                pass

            try:
                browser.close()
            except Exception:
                pass

    return ofertas


def buscar_ofertas(
    limite: int = 30,
) -> list[Oferta]:
    """
    Busca ofertas públicas do AliExpress.

    Configurado para:
    - Brasil
    - BRL
    - Português do Brasil
    """

    todas: list[Oferta] = []

    vistos: set[str] = set()

    por_categoria = max(
        5,
        limite // len(CATEGORIAS),
    )

    for categoria in CATEGORIAS:

        try:
            ofertas = _buscar_com_playwright(
                categoria,
                por_categoria,
            )

            for oferta in ofertas:

                if oferta.id_produto in vistos:
                    continue

                vistos.add(
                    oferta.id_produto
                )

                todas.append(oferta)

                if len(todas) >= limite:
                    break

        except Exception as e:
            log.error(
                "AliExpress '%s': %s",
                categoria,
                e,
            )

        if len(todas) >= limite:
            break

    log.info(
        "AliExpress BR: %d ofertas coletadas",
        len(todas),
    )

    return todas


def converter(
    url: str,
) -> Oferta:
    """
    Converte um link público do AliExpress
    em uma Oferta direcionada ao Brasil.
    """

    url = _normalizar_url(url)

    if not e_link(url):
        raise ValueError(
            "URL não pertence ao AliExpress."
        )

    # Força o link para o Brasil.
    url = _url_brasil(url)

    produto_id = _extrair_id(url)

    preco, preco_original = (
        _extrair_preco_da_url(url)
    )

    desconto = _extrair_desconto(
        preco,
        preco_original,
    )

    return Oferta(
        plataforma="aliexpress",
        id_produto=produto_id,
        titulo=(
            "Oferta AliExpress "
            f"{produto_id}"
        ),
        url_afiliado=url,
        url_produto=url,
        preco=preco,
        preco_original=preco_original,
        desconto_pct=desconto,
        imagem=None,
    )