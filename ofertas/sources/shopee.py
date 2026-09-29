"""
Shopee: coleta de ofertas públicas e, quando disponível,
gera links de afiliado pela Open API oficial.

A coleta automática não depende de credenciais de afiliado.
As credenciais ficam disponíveis apenas para geração de links
de afiliado e consulta pela API oficial.
"""

import hashlib
import json
import logging
import re
import time

import requests

from ..config import config
from ..models import Oferta
from ..utils import sessao

log = logging.getLogger("ofertas.shopee")

ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"

SORT_TYPE = 2

BASE_URL = "https://shopee.com.br"

CATEGORIAS_PUBLICAS = [
    "https://shopee.com.br/search?keyword=eletronicos",
    "https://shopee.com.br/search?keyword=celular",
    "https://shopee.com.br/search?keyword=computador",
    "https://shopee.com.br/search?keyword=fone",
    "https://shopee.com.br/search?keyword=acessorios",
]


def e_link(url: str) -> bool:
    """Identifica links da Shopee."""

    url = (url or "").lower()

    return any(
        dominio in url
        for dominio in (
            "shopee.com.br",
            "s.shopee.",
            "shp.ee/",
        )
    )


def _tem_api() -> bool:
    """Verifica se as credenciais da API de afiliados estão disponíveis."""

    return bool(
        config.shopee_app_id
        and config.shopee_app_secret
    )


def _chamar_api(query: str) -> dict:
    """
    Executa uma consulta autenticada na API oficial da Shopee.

    Esta função só é usada quando existem credenciais.
    """

    if not _tem_api():
        raise RuntimeError(
            "SHOPEE_APP_ID e SHOPEE_APP_SECRET não configurados"
        )

    payload = json.dumps(
        {"query": query},
        separators=(",", ":"),
    )

    ts = str(int(time.time()))

    fator = (
        config.shopee_app_id
        + ts
        + payload
        + config.shopee_app_secret
    )

    assinatura = hashlib.sha256(
        fator.encode()
    ).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "Authorization": (
            f"SHA256 Credential={config.shopee_app_id}, "
            f"Timestamp={ts}, "
            f"Signature={assinatura}"
        ),
    }

    resposta = requests.post(
        ENDPOINT,
        data=payload,
        headers=headers,
        timeout=30,
    )

    resposta.raise_for_status()

    dados = resposta.json()

    if dados.get("errors"):
        raise RuntimeError(
            f"Shopee API: {dados['errors']}"
        )

    return dados.get("data") or {}


_CAMPOS = (
    "itemId "
    "productName "
    "priceMin "
    "priceMax "
    "priceDiscountRate "
    "imageUrl "
    "offerLink "
    "productLink "
    "sales "
    "ratingStar "
    "shopName"
)


def _node_para_oferta(n: dict) -> Oferta:
    """Converte um produto da API em Oferta."""

    preco = float(
        n.get("priceMin") or 0
    ) or None

    desconto = int(
        n.get("priceDiscountRate") or 0
    ) or None

    preco_original = None

    if (
        preco
        and desconto
        and desconto < 100
    ):
        preco_original = round(
            preco / (1 - desconto / 100),
            2,
        )

    partes = []

    if n.get("ratingStar"):
        try:
            partes.append(
                f"? {float(n['ratingStar']):.1f}"
            )
        except (TypeError, ValueError):
            pass

    if n.get("sales"):
        partes.append(
            f"{n['sales']} vendidos"
        )

    return Oferta(
        plataforma="shopee",
        id_produto=str(
            n.get("itemId")
            or ""
        ),
        titulo=n.get("productName") or "",
        url_afiliado=n.get("offerLink") or "",
        url_produto=n.get("productLink") or "",
        preco=preco,
        preco_original=preco_original,
        desconto_pct=desconto,
        imagem=n.get("imageUrl"),
        extra=" · ".join(partes) or None,
    )


def _buscar_keyword_api(
    termo: str,
    limite: int,
) -> list[Oferta]:
    """Busca produtos usando a API oficial."""

    query = (
        f'{{productOfferV2('
        f'keyword:"{termo}",'
        f'sortType:{SORT_TYPE},'
        f'page:1,'
        f'limit:{limite}'
        f'){{nodes{{{_CAMPOS}}}}}}}'
    )

    data = _chamar_api(query)

    nodes = (
        data.get("productOfferV2") or {}
    ).get("nodes") or []

    return [
        _node_para_oferta(n)
        for n in nodes
    ]


def _buscar_api(
    limite: int,
) -> list[Oferta]:
    """Coleta usando a API oficial quando disponível."""

    termos = (
        config.fonte_shopee.get("buscas")
        or []
    )

    if not termos:
        query = (
            f"{{productOfferV2("
            f"listType:0,"
            f"sortType:{SORT_TYPE},"
            f"page:1,"
            f"limit:{limite}"
            f"){{nodes{{{_CAMPOS}}}}}}}"
        )

        data = _chamar_api(query)

        nodes = (
            data.get("productOfferV2") or {}
        ).get("nodes") or []

        ofertas = [
            _node_para_oferta(n)
            for n in nodes
        ]

        log.info(
            "Shopee API: %d ofertas",
            len(ofertas),
        )

        return ofertas

    por_termo = max(
        5,
        limite // len(termos),
    )

    ofertas: dict[str, Oferta] = {}

    for termo in termos:
        try:
            encontrados = _buscar_keyword_api(
                str(termo),
                por_termo,
            )

            for oferta in encontrados:
                ofertas[
                    oferta.id_produto
                ] = oferta

        except Exception as e:
            log.error(
                "Shopee API '%s': %s",
                termo,
                e,
            )

    resultado = list(
        ofertas.values()
    )

    log.info(
        "Shopee API: %d ofertas",
        len(resultado),
    )

    return resultado


def _numero(texto: str) -> float | None:
    """Extrai um número de preço do texto."""

    if not texto:
        return None

    texto = (
        texto
        .replace("R$", "")
        .replace("\xa0", " ")
        .strip()
    )

    encontrados = re.findall(
        r"\d+(?:[.,]\d{1,2})?",
        texto,
    )

    if not encontrados:
        return None

    valor = encontrados[0]

    try:
        if "," in valor:
            valor = valor.replace(
                ".",
                "",
            ).replace(
                ",",
                ".",
            )

        return float(valor)

    except ValueError:
        return None


def _extrair_desconto(
    texto: str,
) -> int | None:
    """Extrai descontos como 25%, -30% ou 40% OFF."""

    if not texto:
        return None

    encontrados = re.findall(
        r"(\d{1,2})\s*%",
        texto,
    )

    if not encontrados:
        return None

    for valor in encontrados:
        try:
            desconto = int(valor)

            if 0 < desconto < 100:
                return desconto

        except ValueError:
            pass

    return None


def _extrair_produtos_publicos(
    page,
    limite: int,
) -> list[Oferta]:
    """
    Tenta extrair produtos diretamente da página pública.

    A Shopee altera frequentemente o HTML,
    por isso usamos vários seletores de fallback.
    """

    produtos: list[Oferta] = []
    vistos: set[str] = set()

    seletores = [
        'a[href*="-i."]',
        'a[href*="/product/"]',
        'a[data-sqe="link"]',
        'a[href*=".html"]',
    ]

    elementos = []

    for seletor in seletores:
        try:
            encontrados = page.locator(
                seletor
            ).all()

            elementos.extend(
                encontrados
            )

        except Exception:
            continue

        if len(elementos) >= limite * 5:
            break

    for elemento in elementos:
        if len(produtos) >= limite:
            break

        try:
            href = elemento.get_attribute(
                "href"
            )

            if not href:
                continue

            if href.startswith("//"):
                href = "https:" + href

            elif href.startswith("/"):
                href = BASE_URL + href

            if "shopee.com.br" not in href:
                continue

            texto = elemento.inner_text(
                timeout=1000
            ).strip()

            if not texto:
                continue

            titulo = texto.split("\n")[0].strip()

            if len(titulo) < 5:
                continue

            if href in vistos:
                continue

            vistos.add(href)

            desconto = _extrair_desconto(
                texto
            )

            preco = None
            precos = re.findall(
                r"R\$\s*[\d.,]+",
                texto,
            )

            if precos:
                preco = _numero(
                    precos[0]
                )

            imagem = None

            try:
                imagem = elemento.locator(
                    "img"
                ).first.get_attribute(
                    "src"
                )
            except Exception:
                pass

            produtos.append(
                Oferta(
                    plataforma="shopee",
                    id_produto=(
                        href
                        .rstrip("/")
                        .split("/")[-1][:100]
                    ),
                    titulo=titulo,
                    url_afiliado="",
                    url_produto=href,
                    preco=preco,
                    preco_original=None,
                    desconto_pct=desconto,
                    imagem=imagem,
                )
            )

        except Exception:
            continue

    return produtos


def _buscar_publico(
    url: str,
    limite: int,
) -> list[Oferta]:
    """
    Busca ofertas usando a página pública da Shopee.

    Não exige login nem credenciais de afiliado.
    """

    try:
        from playwright.sync_api import (
            sync_playwright,
        )

    except Exception as e:
        raise RuntimeError(
            f"Playwright não está disponível: {e}"
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

        page = browser.new_page(
            viewport={
                "width": 1920,
                "height": 1080,
            },
            locale="pt-BR",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )

        try:
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            page.wait_for_timeout(
                6000
            )

            ofertas = (
                _extrair_produtos_publicos(
                    page,
                    limite,
                )
            )

        finally:
            browser.close()

    log.info(
        "Shopee pública: %d ofertas em %s",
        len(ofertas),
        url,
    )

    return ofertas


def buscar_ofertas(
    limite: int = 30,
) -> list[Oferta]:
    """
    Busca ofertas da Shopee.

    Se as credenciais da API existirem,
    usa a API oficial.

    Caso contrário, tenta a coleta pública
    usando Playwright.
    """

    if _tem_api():
        try:
            return _buscar_api(
                limite
            )

        except Exception as e:
            log.warning(
                "API da Shopee falhou; "
                "tentando coleta pública: %s",
                e,
            )

    todas: list[Oferta] = []
    vistos: set[str] = set()

    por_categoria = max(
        5,
        limite // len(CATEGORIAS_PUBLICAS),
    )

    for categoria in CATEGORIAS_PUBLICAS:

        if len(todas) >= limite:
            break

        try:
            ofertas = _buscar_publico(
                categoria,
                por_categoria,
            )

            for oferta in ofertas:

                chave = (
                    oferta.url_produto
                    or oferta.id_produto
                )

                if chave in vistos:
                    continue

                vistos.add(chave)
                todas.append(oferta)

                if len(todas) >= limite:
                    break

        except Exception as e:
            log.error(
                "Shopee pública '%s': %s",
                categoria,
                e,
            )

    log.info(
        "Shopee pública: %d ofertas coletadas",
        len(todas),
    )

    return todas


_RE_IDS = re.compile(
    r"-?i\.(\d+)\.(\d+)|/product/(\d+)/(\d+)"
)


def converter(url: str) -> Oferta:
    """
    Link de produto/short link -> Oferta.

    Se houver API de afiliados configurada,
    tenta gerar o link de afiliado.

    Caso contrário, retorna o link público
    normal da Shopee.
    """

    url_original = url

    if (
        "s.shopee." in url
        or "shp.ee/" in url
    ):
        try:
            url = sessao().get(
                url,
                allow_redirects=True,
                timeout=20,
            ).url

        except Exception as e:
            log.warning(
                "Não consegui expandir o link curto "
                "da Shopee: %s",
                e,
            )

    m = _RE_IDS.search(url)

    item_id = (
        (m.group(2) or m.group(4))
        if m
        else None
    )

    # Se temos API, tentamos gerar
    # o link de afiliado normalmente.
    if _tem_api():

        if item_id:
            try:
                data = _chamar_api(
                    f"{{productOfferV2("
                    f"itemId:{item_id}"
                    f"){{nodes{{{_CAMPOS}}}}}}}"
                )

                nodes = (
                    data.get(
                        "productOfferV2"
                    ) or {}
                ).get(
                    "nodes"
                ) or []

                if nodes:
                    return _node_para_oferta(
                        nodes[0]
                    )

            except Exception as e:
                log.warning(
                    "Não consegui consultar "
                    "o produto na API da Shopee: %s",
                    e,
                )

        try:
            origin = json.dumps(
                url.split("?")[0]
            )

            data = _chamar_api(
                f'mutation{{generateShortLink('
                f'input:{{originUrl:{origin},'
                f'subIds:["telegram"]'
                f'}}){{shortLink}}}}'
            )

            short = (
                data.get(
                    "generateShortLink"
                ) or {}
            ).get(
                "shortLink"
            )

            if short:
                return Oferta(
                    plataforma="shopee",
                    id_produto=(
                        item_id
                        or url.split("?")[0]
                        .rstrip("/")
                        .rsplit("/", 1)[-1][:60]
                    ),
                    titulo="Oferta Shopee",
                    url_afiliado=short,
                    url_produto=url,
                )

        except Exception as e:
            log.warning(
                "Não consegui gerar "
                "link de afiliado Shopee: %s",
                e,
            )

    # Sem API ou se a API falhar,
    # usa o link público normal.
    return Oferta(
        plataforma="shopee",
        id_produto=(
            item_id
            or url.split("?")[0]
            .rstrip("/")
            .rsplit("/", 1)[-1][:60]
            or "shopee"
        ),
        titulo="Oferta Shopee",
        url_afiliado=url,
        url_produto=url_original,
    )