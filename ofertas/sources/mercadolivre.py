
"""Mercado Livre: scraping de ofertas + links de afiliado."""

import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from bs4 import BeautifulSoup

from ..config import DATA_DIR, config
from ..models import Oferta
from ..utils import USER_AGENT, parse_preco_br, sessao

log = logging.getLogger("ofertas.ml")

URL_OFERTAS = "https://www.mercadolivre.com.br/ofertas"
URL_LINKBUILDER = "https://www.mercadolivre.com.br/afiliados/linkbuilder"
API_CREATELINK = "https://www.mercadolivre.com.br/affiliate-program/api/v2/affiliates/createLink"

PERFIL_DIR = DATA_DIR / "ml_profile"

_RE_ID = re.compile(r"(MLB-?\d{6,})")


def e_link(url: str) -> bool:
    return any(
        d in url
        for d in (
            "mercadolivre.com",
            "mercadolibre.com",
            "meli.la/",
        )
    )


def tem_sessao() -> bool:
    return PERFIL_DIR.exists() and any(PERFIL_DIR.iterdir())


def _categorias() -> dict[str, str]:
    cats = config.fonte_ml.get("categorias") or {}

    return (
        dict(cats)
        if isinstance(cats, dict)
        else {str(c): str(c) for c in cats}
    )


def buscar_ofertas() -> list[Oferta]:
    paginas = max(
        1,
        int(config.fonte_ml.get("paginas", 1)),
    )

    categorias = _categorias() or {"": "todas"}

    s = sessao()
    ofertas: dict[str, Oferta] = {}

    for cat_id, nome in categorias.items():

        for pagina in range(1, paginas + 1):

            params = {}

            if cat_id:
                params["category"] = cat_id

            if pagina > 1:
                params["page"] = pagina

            r = s.get(
                URL_OFERTAS,
                params=params or None,
                timeout=30,
            )

            r.raise_for_status()

            achadas = _parse_pagina(r.text)

            for o in achadas:
                ofertas.setdefault(
                    o.id_produto,
                    o,
                )

            log.info(
                "Mercado Livre %s: %d ofertas",
                nome,
                len(achadas),
            )

            time.sleep(1)

    log.info(
        "Mercado Livre: %d ofertas coletadas",
        len(ofertas),
    )

    return list(ofertas.values())


def _preco_de(card, seletor_base: str) -> float | None:

    fracao = card.select_one(
        f"{seletor_base} .andes-money-amount__fraction"
    )

    if not fracao:
        return None

    centavos = card.select_one(
        f"{seletor_base} .andes-money-amount__cents"
    )

    texto = fracao.get_text(strip=True)

    if centavos:
        texto += "," + centavos.get_text(strip=True)

    return parse_preco_br(texto)


def _parse_card(card) -> Oferta | None:

    a = card.select_one(
        "a.poly-component__title"
    )

    if not (a and a.get("href")):
        return None

    titulo = a.get_text(strip=True)

    url = (
        a["href"]
        .split("#")[0]
        .split("?")[0]
    )

    m = _RE_ID.search(a["href"])

    if m:
        id_produto = m.group(1).replace("-", "")
    else:
        id_produto = (
            url.rstrip("/")
            .rsplit("/", 1)[-1][:40]
        )

    preco = _preco_de(
        card,
        ".poly-price__current",
    )

    preco_original = _preco_de(
        card,
        "s.andes-money-amount--previous",
    )

    desconto = None

    selo = card.select_one(
        ".poly-price__discount-polylabel, "
        ".andes-money-amount__discount"
    )

    if selo:

        m = re.search(
            r"(\d+)\s*%",
            selo.get_text(),
        )

        desconto = (
            int(m.group(1))
            if m
            else None
        )

    img = card.select_one(
        "img.poly-component__picture"
    )

    imagem = (
        img.get("data-src")
        or img.get("src")
    ) if img else None

    if imagem and imagem.startswith("data:"):
        imagem = None

    partes = []

    review = card.select_one(
        ".poly-component__review-compacted"
    )

    if review:
        partes.append(
            "? "
            + re.sub(
                r"\s*\|\s*",
                " · ",
                review.get_text(
                    " ",
                    strip=True,
                ),
            )
        )

    if "Frete grátis" in card.get_text():
        partes.append("?? Frete grátis")

    pix = card.select_one(
        ".poly-price__unit-description"
    )

    if pix and "pix" in pix.get_text().lower():
        partes.append("?? preço no Pix")

    return Oferta(
        plataforma="mercadolivre",
        id_produto=id_produto,
        titulo=titulo,
        url_afiliado="",
        url_produto=url,
        preco=preco,
        preco_original=preco_original,
        desconto_pct=desconto,
        imagem=imagem,
        extra=" · ".join(partes) or None,
    )


def _parse_pagina(html: str) -> list[Oferta]:

    soup = BeautifulSoup(
        html,
        "lxml",
    )

    cards = soup.select(
        "div.poly-card"
    )

    ofertas = [
        o
        for o in (
            _parse_card(c)
            for c in cards
        )
        if o
    ]

    if cards and not ofertas:
        log.warning(
            "Página de ofertas do ML mudou de layout? "
            "%d cards, 0 parseados",
            len(cards),
        )

    return ofertas


def _abrir_contexto(pw, headless: bool):

    is_railway = bool(
        os.environ.get("RAILWAY_ENVIRONMENT")
        or os.environ.get("RAILWAY_PROJECT_ID")
    )

    if is_railway:
        os.environ["DISPLAY"] = ":99"

        log.info(
            "DISPLAY configurado para o Chrome: %s",
            os.environ["DISPLAY"],
        )

    kwargs = dict(
        headless=headless,
        locale="pt-BR",
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-gpu",
            "--window-size=1920,1080",
        ],
        ignore_default_args=[
            "--enable-automation"
        ],
    )

    if is_railway:
        try:
            return pw.chromium.launch_persistent_context(
                str(PERFIL_DIR),
                channel="chrome",
                **kwargs,
            )

        except Exception as exc:

            log.warning(
                "Google Chrome não iniciou (%s). "
                "Tentando Chromium do Playwright.",
                type(exc).__name__,
            )

    return pw.chromium.launch_persistent_context(
        str(PERFIL_DIR),
        **kwargs,
    )


def _achar_chrome() -> str:

    import shutil

    candidatos: list[str] = []

    if sys.platform == "win32":

        try:

            import winreg

            for hive in (
                winreg.HKEY_CURRENT_USER,
                winreg.HKEY_LOCAL_MACHINE,
            ):

                try:

                    chave = (
                        r"SOFTWARE\Microsoft\Windows"
                        r"\CurrentVersion\App Paths\chrome.exe"
                    )

                    with winreg.OpenKey(
                        hive,
                        chave,
                    ) as k:

                        candidatos.append(
                            winreg.QueryValueEx(
                                k,
                                None,
                            )[0]
                        )

                except OSError:
                    continue

        except ImportError:
            pass

        for base in (
            os.environ.get(
                "ProgramFiles",
                r"C:\Program Files",
            ),
            os.environ.get(
                "ProgramFiles(x86)",
                r"C:\Program Files (x86)",
            ),
            os.environ.get(
                "LOCALAPPDATA",
                "",
            ),
        ):

            if base:

                candidatos.append(
                    str(
                        Path(base)
                        / "Google/Chrome/Application/chrome.exe"
                    )
                )

    elif sys.platform == "darwin":

        candidatos += [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            str(
                Path.home()
                / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            ),
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]

    else:

        for nome in (
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
            "brave-browser",
            "microsoft-edge",
        ):

            achado = shutil.which(nome)

            if achado:
                candidatos.append(achado)

        candidatos += [
            "/usr/bin/google-chrome",
            "/usr/bin/chromium",
            "/snap/bin/chromium",
            "/usr/bin/chromium-browser",
        ]

    for c in candidatos:

        if c and Path(c).exists():
            return c

    raise RuntimeError(
        "Google Chrome não encontrado — "
        "instale o Google Chrome e tente de novo."
    )


def ml_login() -> None:

    is_railway = bool(
        os.environ.get("RAILWAY_ENVIRONMENT")
        or os.environ.get("RAILWAY_PROJECT_ID")
    )

    # IMPORTANTE:
    # O DISPLAY precisa existir antes de iniciar o Playwright.
    if is_railway:
        os.environ["DISPLAY"] = ":99"

    PERFIL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ==========================================
    # LOGIN NORMAL NO COMPUTADOR
    # ==========================================

    if not is_railway:

        chrome = _achar_chrome()

        print("")
        print(
            "?? Vai abrir um Chrome normal "
            "com o perfil do bot."
        )

        print(
            "1. Faça login no Mercado Livre."
        )

        print(
            "2. Confira que o Linkbuilder "
            "carrega logado."
        )

        print(
            "3. FECHE o navegador para terminar."
        )

        print("")

        proc = subprocess.Popen(
            [
                chrome,
                f"--user-data-dir={PERFIL_DIR}",
                "--no-first-run",
                "--no-default-browser-check",
                URL_LINKBUILDER,
            ]
        )

        proc.wait()

        print("")
        print(
            f"? Perfil salvo em {PERFIL_DIR}"
        )

        print(
            "O bot poderá usar essa sessão "
            "automaticamente."
        )

        return

    # ==========================================
    # LOGIN REMOTO NO RAILWAY
    # ==========================================

    dominio = os.environ.get(
        "RAILWAY_PUBLIC_DOMAIN",
        "",
    )

    if dominio:

        remote_url = (
            f"https://{dominio}/vnc/vnc.html"
            "?autoconnect=true"
            "&path=websockify"
            "&resize=scale"
        )

    else:

        remote_url = (
            "Abra o domínio público do Railway "
            "e acrescente "
            "/vnc/vnc.html"
            "?autoconnect=true"
            "&path=websockify"
            "&resize=scale"
        )

    print("")
    print("=" * 55)
    print("?? LOGIN DO MERCADO LIVRE NO RAILWAY")
    print("=" * 55)
    print("")
    print(
        "Abra este endereço para visualizar o Chrome:"
    )
    print("")
    print(remote_url)
    print("")
    print(
        "Faça o login no Mercado Livre."
    )
    print(
        "Depois feche a janela do Chrome "
        "dentro do noVNC."
    )
    print("")
    print(
        "A sessão ficará salva em:"
    )
    print(PERFIL_DIR)
    print("")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:

        ctx = _abrir_contexto(
            pw,
            headless=False,
        )

        page = (
            ctx.pages[0]
            if ctx.pages
            else ctx.new_page()
        )

        page.goto(
            URL_LINKBUILDER,
            wait_until="domcontentloaded",
            timeout=120000,
        )

        try:

            while True:

                try:
                    pages = ctx.pages
                except Exception:
                    break

                if not pages:
                    break

                if all(
                    p.is_closed()
                    for p in pages
                ):
                    break

                time.sleep(2)

        except KeyboardInterrupt:
            pass

        except Exception as e:

            log.warning(
                "Navegador encerrado: %s",
                e,
            )

        try:
            ctx.close()
        except Exception:
            pass

    print("")
    print(
        "? Login do Mercado Livre encerrado."
    )
    print(
        "? Sessão salva em data/ml_profile."
    )
    print("")


def _criar_links_api(
    page,
    urls: list[str],
    etiqueta: str,
) -> list[str]:

    r = page.evaluate(
        """async ({api, urls, tag}) => {
            const resp = await fetch(api, {
                method: 'POST',
                headers: {'content-type': 'application/json'},
                body: JSON.stringify({urls, tag}),
            });

            const corpo = await resp.text();

            try {
                return {
                    http: resp.status,
                    dados: JSON.parse(corpo)
                };
            }

            catch (e) {
                return {
                    http: resp.status,
                    texto: corpo.slice(0, 300)
                };
            }
        }""",
        {
            "api": API_CREATELINK,
            "urls": urls,
            "tag": etiqueta,
        },
    )

    if r.get("http") != 200 or not r.get("dados"):

        raise RuntimeError(
            f"createLink respondeu HTTP "
            f"{r.get('http')}: "
            f"{r.get('texto', '')}"
        )

    itens = (
        r["dados"].get("urls")
        or []
    )

    links = [
        i.get("short_url") or ""
        for i in itens
    ]

    if (
        len(links) != len(urls)
        or not all(links)
    ):

        raise RuntimeError(
            f"createLink devolveu "
            f"{sum(1 for l in links if l)} links "
            f"para {len(urls)} URLs: "
            f"{r['dados']}"
        )

    return links


def gerar_links_afiliado(
    ofertas: list[Oferta],
) -> None:

    from playwright.sync_api import sync_playwright

    if not tem_sessao():

        raise RuntimeError(
            "Sessão do ML não encontrada — "
            "rode: uv run python -m ofertas ml-login"
        )

    if not config.ml_etiqueta:

        raise RuntimeError(
            "ML_ETIQUETA não configurada no .env "
            "(é a 'Etiqueta em uso' do Linkbuilder "
            "no painel de afiliados)"
        )

    pendentes = [
        o
        for o in ofertas
        if not o.url_afiliado
        and o.url_produto
    ]

    if not pendentes:
        return

    is_railway = bool(
        os.environ.get("RAILWAY_ENVIRONMENT")
        or os.environ.get("RAILWAY_PROJECT_ID")
    )

    if is_railway:
        os.environ["DISPLAY"] = ":99"

    with sync_playwright() as pw:

        ctx = _abrir_contexto(
            pw,
            headless=True,
        )

        page = (
            ctx.pages[0]
            if ctx.pages
            else ctx.new_page()
        )

        try:

            page.goto(
                URL_LINKBUILDER,
                wait_until="domcontentloaded",
            )

            if (
                "login" in page.url
                or "registration" in page.url
            ):

                raise RuntimeError(
                    "Sessão do ML expirou — "
                    "rode de novo: "
                    "uv run python -m ofertas ml-login"
                )

            page.wait_for_timeout(1500)

            for i in range(
                0,
                len(pendentes),
                10,
            ):

                lote = pendentes[
                    i:i + 10
                ]

                links = _criar_links_api(
                    page,
                    [
                        o.url_produto
                        for o in lote
                    ],
                    config.ml_etiqueta,
                )

                for o, link in zip(
                    lote,
                    links,
                ):
                    o.url_afiliado = link

            log.info(
                "Mercado Livre: %d links "
                "de afiliado gerados",
                len(pendentes),
            )

        finally:
            ctx.close()


def converter(url: str) -> Oferta:

    url = url.split("#")[0]

    if "meli.la/" in url:

        try:

            url = (
                sessao()
                .get(
                    url,
                    allow_redirects=True,
                    timeout=20,
                )
                .url
                .split("#")[0]
            )

        except Exception as e:

            log.warning(
                "Não consegui expandir "
                "o link meli.la: %s",
                e,
            )

    titulo = None
    preco = None
    preco_original = None
    imagem = None

    try:

        r = sessao().get(
            url,
            timeout=25,
        )

        soup = BeautifulSoup(
            r.text,
            "lxml",
        )

        el = soup.select_one(
            "h1.ui-pdp-title"
        )

        titulo = (
            el.get_text(strip=True)
            if el
            else None
        )

        el = soup.select_one(
            'meta[property="og:image"]'
        )

        imagem = (
            el.get("content")
            if el
            else None
        )

        el = soup.select_one(
            'meta[itemprop="price"]'
        )

        if el and el.get("content"):

            preco = float(
                el["content"]
            )

        else:

            el = soup.select_one(
                ".ui-pdp-price__second-line "
                ".andes-money-amount__fraction"
            )

            preco = (
                parse_preco_br(
                    el.get_text()
                )
                if el
                else None
            )

        el = soup.select_one(
            "s.andes-money-amount--previous "
            ".andes-money-amount__fraction"
        )

        preco_original = (
            parse_preco_br(
                el.get_text()
            )
            if el
            else None
        )

    except Exception as e:

        log.warning(
            "Não consegui ler a página "
            "do produto: %s",
            e,
        )

    m = _RE_ID.search(url)

    oferta = Oferta(
        plataforma="mercadolivre",
        id_produto=(
            m.group(1).replace("-", "")
            if m
            else url.rstrip("/")
            .rsplit("/", 1)[-1][:40]
        ),
        titulo=titulo or "Oferta Mercado Livre",
        url_afiliado="",
        url_produto=url.split("?")[0],
        preco=preco,
        preco_original=preco_original,
        imagem=imagem,
    )

    gerar_links_afiliado(
        [oferta]
    )

    if not oferta.url_afiliado:

        raise RuntimeError(
            "Linkbuilder não devolveu "
            "o link de afiliado"
        )

    return oferta
