"""Coleta e publica cupons de desconto ativos para o Brasil."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from . import db

log = logging.getLogger("ofertas.cupons")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/153.0.0.0 Safari/537.36"
)

FONTES = {
    "mercadolivre": "https://www.mercadolivre.com.br/l/promocoes",
    "amazon": "https://www.pelando.com.br/cupons-de-descontos/amazon?hideExpired=true&sort=popular",
    "aliexpress": "https://www.couponinsta.com/pt-br/stores/aliexpress?offer_country=br&view=list",
}


@dataclass
class Cupom:
    plataforma: str
    titulo: str
    codigo: str
    url: str
    condicao: str = ""
    desconto: str = ""
    validade: str = ""
    fonte: str = ""

    @property
    def uid(self) -> str:
        return f"cupom:{self.plataforma}:{self.codigo.upper()}"


def _baixar(url: str) -> str:
    resposta = requests.get(
        url,
        headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"},
        timeout=30,
    )
    resposta.raise_for_status()
    return resposta.text


def _linhas(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    texto = soup.get_text("\n")
    return [re.sub(r"\s+", " ", x).strip() for x in texto.splitlines() if x.strip()]


def _codigo_valido(codigo: str) -> bool:
    codigo = codigo.strip()
    if not 4 <= len(codigo) <= 32:
        return False
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]*", codigo, re.I):
        return False
    palavras = {
        "COPIAR", "CUPOM", "DESCONTO", "BRASIL", "BRAZIL",
        "AMAZON", "ALIEXPRESS", "MERCADO", "LIVRE", "VERIFICADO",
    }
    return codigo.upper() not in palavras


def _primeira_frase(linhas: list[str], i: int) -> str:
    for j in range(max(0, i - 5), i):
        texto = linhas[j]
        if (
            len(texto) >= 12
            and "copiar" not in texto.lower()
            and "pegar cupom" not in texto.lower()
            and not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{3,32}", texto, re.I)
        ):
            return texto
    return "Cupom de desconto"


def _amazon(html: str) -> list[Cupom]:
    linhas = _linhas(html)
    cupons: list[Cupom] = []

    for i, linha in enumerate(linhas):
        if not linha.upper().endswith(" COPIAR"):
            continue
        codigo = linha[:-7].strip()
        if not _codigo_valido(codigo):
            continue

        titulo = _primeira_frase(linhas, i)
        bloco = " ".join(linhas[max(0, i - 5):i + 2])
        if "expirad" in bloco.lower() or "expired" in bloco.lower():
            continue

        desconto = ""
        m = re.search(r"(\d{1,3}%\s*OFF|R\$\s*\d+[\d.,]*\s*OFF)", bloco, re.I)
        if m:
            desconto = m.group(1)

        validade = ""
        m = re.search(
            r"(?:válido|valido|até|ate)\s+(.{0,90}?)(?:\.|$)",
            bloco,
            re.I,
        )
        if m:
            validade = m.group(0).strip()

        cupons.append(
            Cupom(
                plataforma="Amazon",
                titulo=titulo[:180],
                codigo=codigo,
                url="https://www.amazon.com.br/",
                condicao=bloco[:300],
                desconto=desconto,
                validade=validade,
                fonte="Pelando",
            )
        )

    return cupons


def _aliexpress(html: str) -> list[Cupom]:
    linhas = _linhas(html)
    cupons: list[Cupom] = []

    for i, linha in enumerate(linhas):
        if linha.lower() not in {"clique para copiar", "copiar"}:
            continue
        if i == 0:
            continue

        codigo = linhas[i - 1].strip()
        if not _codigo_valido(codigo):
            continue

        bloco = " ".join(linhas[max(0, i - 7):i + 2])
        if "expirad" in bloco.lower() or "expired" in bloco.lower():
            continue
        if "válido em brazil" not in bloco.lower() and "brazil" not in bloco.lower():
            continue

        titulo = _primeira_frase(linhas, i - 1)
        desconto = ""
        m = re.search(r"(R\$\s*\d+[\d.,]*|\d{1,3}%)(?:\s*DESC)?", bloco, re.I)
        if m:
            desconto = m.group(1)

        cupons.append(
            Cupom(
                plataforma="AliExpress",
                titulo=titulo[:180],
                codigo=codigo,
                url="https://pt.aliexpress.com/",
                condicao=bloco[:300],
                desconto=desconto,
                fonte="CouponInsta",
            )
        )

    return cupons


def _mercadolivre(html: str) -> list[Cupom]:
    linhas = _linhas(html)
    cupons: list[Cupom] = []

    for i, linha in enumerate(linhas):
        m = re.fullmatch(r"Cupom\s+([A-Z0-9][A-Z0-9_-]{3,32})", linha, re.I)
        if not m:
            continue

        codigo = m.group(1).upper()
        if not _codigo_valido(codigo):
            continue

        bloco = " ".join(linhas[i:min(i + 4, len(linhas))])
        if "expirad" in bloco.lower() or "expired" in bloco.lower():
            continue

        titulo = "Cupom Mercado Livre"
        desconto = ""
        mdesc = re.search(r"(até\s+\d{1,3}%|\d{1,3}%|R\$\s*[\d.,]+)", bloco, re.I)
        if mdesc:
            desconto = mdesc.group(1)

        validade = ""
        mv = re.search(r"(Cupom válido[^.]*\.)", bloco, re.I)
        if mv:
            validade = mv.group(1)

        cupons.append(
            Cupom(
                plataforma="Mercado Livre",
                titulo=titulo,
                codigo=codigo,
                url="https://www.mercadolivre.com.br/l/promocoes",
                condicao=bloco[:300],
                desconto=desconto,
                validade=validade,
                fonte="Mercado Livre",
            )
        )

    return cupons


def coletar() -> list[Cupom]:
    """Busca cupons nas páginas configuradas e retorna apenas códigos encontrados."""
    todos: list[Cupom] = []

    for nome, url in FONTES.items():
        try:
            html = _baixar(url)
            if nome == "amazon":
                encontrados = _amazon(html)
            elif nome == "aliexpress":
                encontrados = _aliexpress(html)
            else:
                encontrados = _mercadolivre(html)

            log.info("%s: %d cupons encontrados", nome, len(encontrados))
            todos.extend(encontrados)
        except Exception as e:
            log.error("%s: falha ao coletar cupons: %s", nome, e)

    # Remove duplicados e limita a uma seleção enxuta por rodada.
    unicos: dict[str, Cupom] = {}
    for cupom in todos:
        unicos.setdefault(cupom.uid, cupom)

    return list(unicos.values())


def escolher(cupons: list[Cupom], limite: int, dias: int) -> list[Cupom]:
    candidatos = [
        c for c in cupons
        if not db.ja_postado_cupom(c.uid, dias)
    ]
    # Alterna plataformas para não concentrar a rodada em uma só.
    grupos: dict[str, list[Cupom]] = {}
    for c in candidatos:
        grupos.setdefault(c.plataforma, []).append(c)

    escolhidos: list[Cupom] = []
    while len(escolhidos) < limite and any(grupos.values()):
        for plataforma in list(grupos):
            if len(escolhidos) >= limite:
                break
            fila = grupos[plataforma]
            if fila:
                escolhidos.append(fila.pop(0))

    return escolhidos


def preparar_cupons(limite: int = 3, dias: int = 3) -> list[Cupom]:
    cupons = coletar()
    return escolher(cupons, max(1, limite), max(1, dias))


def registrar(cupom: Cupom) -> None:
    db.registrar_cupom(cupom)
