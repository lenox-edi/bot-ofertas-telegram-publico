import asyncio
import logging
import re

from telegram import Bot

from . import db
from .config import config, dentro_do_horario
from .models import Oferta
from .sources import amazon, aliexpress, mercadolivre, shopee
from .telegram_poster import postar_oferta

log = logging.getLogger("ofertas.pipeline")


def coletar() -> list[Oferta]:
    """Busca ofertas nas fontes automáticas ativas."""

    todas: list[Oferta] = []

    # Mercado Livre
    if config.fonte_ml.get("ativa"):
        try:
            todas += mercadolivre.buscar_ofertas()
        except Exception as e:
            log.error(
                "Mercado Livre: %s",
                e,
            )

    # Amazon
    if config.fonte_amazon.get("ativa"):
        try:
            if config.amazon_tag:
                todas += amazon.buscar_ofertas()
            else:
                log.warning(
                    "Amazon ativa, mas AMAZON_TAG "
                    "não está configurada — pulando"
                )
        except Exception as e:
            log.error(
                "Amazon: %s",
                e,
            )

    # Shopee
    if config.fonte_shopee.get("ativa"):
        try:
            ofertas_shopee = shopee.buscar_ofertas(
                int(
                    config.fonte_shopee.get(
                        "limite",
                        30,
                    )
                )
            )

            todas += ofertas_shopee

        except Exception as e:
            log.error(
                "Shopee: %s",
                e,
            )

    # AliExpress
    if config.fonte_aliexpress.get("ativa"):
        try:
            ofertas_aliexpress = (
                aliexpress.buscar_ofertas(
                    int(
                        config.fonte_aliexpress.get(
                            "limite",
                            30,
                        )
                    )
                )
            )

            todas += ofertas_aliexpress

        except Exception as e:
            log.error(
                "AliExpress: %s",
                e,
            )

    return todas


def filtrar(
    ofertas: list[Oferta],
) -> list[Oferta]:
    """Aplica os filtros definidos no config.yaml."""

    aprovadas: list[Oferta] = []

    for o in ofertas:

        if not o.titulo:
            continue

        if db.ja_postada(
            o.uid,
            config.nao_repetir_dias,
        ):
            continue

        if (
            config.desconto_minimo
            and (
                o.desconto or 0
            ) < config.desconto_minimo
        ):
            continue

        if o.preco is not None:

            if (
                config.preco_minimo
                and o.preco
                < config.preco_minimo
            ):
                continue

            if (
                config.preco_maximo
                and o.preco
                > config.preco_maximo
            ):
                continue

        titulo = o.titulo.lower()

        if any(
            palavra.lower() in titulo
            for palavra in config.palavras_bloqueadas
        ):
            continue

        aprovadas.append(o)

    return aprovadas


def _chave_similar(
    titulo: str,
) -> str:
    """
    Gera uma chave simples para evitar
    produtos muito parecidos no mesmo ciclo.
    """

    return " ".join(
        re.findall(
            r"\w+",
            titulo.lower(),
        )[:5]
    )


def escolher(
    ofertas: list[Oferta],
    n: int,
) -> list[Oferta]:
    """
    Escolhe até N ofertas, priorizando desconto
    e alternando entre plataformas.
    """

    filas: dict[
        str,
        list[Oferta],
    ] = {}

    def chave_prioridade(oferta: Oferta) -> tuple[int, int]:
        texto = " ".join(
            [
                oferta.titulo or "",
                oferta.extra or "",
            ]
        ).lower()

        termos_relampago = (
            "oferta relâmpago",
            "oferta relampago",
            "relâmpago",
            "relampago",
            "flash sale",
        )

        relampago = int(
            any(
                termo in texto
                for termo in termos_relampago
            )
        )

        return (
            relampago,
            oferta.desconto or 0,
        )

    for o in sorted(
        ofertas,
        key=chave_prioridade,
        reverse=True,
    ):
        filas.setdefault(
            o.plataforma,
            [],
        ).append(o)

    ordem = sorted(
        filas.values(),
        key=lambda fila: (
            fila[0].desconto or 0
        ),
        reverse=True,
    )

    escolhidas: list[Oferta] = []

    vistas: set[str] = set()

    while (
        len(escolhidas) < n
        and any(ordem)
    ):

        adicionou = False

        for fila in ordem:

            while fila:

                o = fila.pop(0)

                chave = _chave_similar(
                    o.titulo
                )

                if chave in vistas:
                    continue

                vistas.add(chave)

                escolhidas.append(o)

                adicionou = True

                break

            if len(escolhidas) >= n:
                break

        if not adicionou:
            break

    return escolhidas


def preparar_link(
    oferta: Oferta,
) -> None:
    """
    Garante que toda oferta selecionada tenha
    um link utilizável.

    Se não houver link de afiliado, usa o
    link público normal do produto.
    """

    if oferta.url_afiliado:
        return

    if oferta.url_produto:
        oferta.url_afiliado = (
            oferta.url_produto
        )


async def avisar_dono(
    bot: Bot,
    texto: str,
) -> None:
    """Manda aviso no privado do dono, se configurado."""

    if not config.owner_id:
        return

    try:
        await bot.send_message(
            config.owner_id,
            texto,
        )

    except Exception as e:
        log.warning(
            "Não consegui avisar o dono: %s",
            e,
        )


async def executar_ciclo(
    bot: Bot,
) -> int:
    """
    Ciclo completo:

    coletar
    ?
    filtrar
    ?
    escolher até 5
    ?
    preparar links
    ?
    postar no Telegram
    """

    if not dentro_do_horario():

        log.info(
            "Fora do horário ativo (%s) "
            "— ciclo pulado",
            config.horario_ativo,
        )

        return 0

    log.info(
        "Iniciando ciclo automático..."
    )

    # Coleta em thread para não bloquear
    # o loop do Telegram.
    brutas = await asyncio.to_thread(
        coletar
    )

    log.info(
        "Coleta concluída: %d ofertas",
        len(brutas),
    )

    boas = filtrar(
        brutas
    )

    log.info(
        "Após filtros: %d ofertas",
        len(boas),
    )

    escolhidas = escolher(
        boas,
        config.max_posts_por_ciclo,
    )

    log.info(
        "Selecionadas: %d ofertas",
        len(escolhidas),
    )

    postadas = 0

    for oferta in escolhidas:

        preparar_link(
            oferta
        )

        if not oferta.url_afiliado:

            log.warning(
                "Sem link, pulando: %s",
                oferta.titulo[:60],
            )

            continue

        try:

            await postar_oferta(
                bot,
                oferta,
                config.chat_id,
            )

        except Exception as e:

            log.error(
                "Falha ao postar '%s': %s",
                oferta.titulo[:60],
                e,
            )

            continue

        db.registrar(
            oferta
        )

        postadas += 1

        log.info(
            "Postada %d/%d: %s [%s] -%s%%",
            postadas,
            len(escolhidas),
            oferta.titulo[:60],
            oferta.plataforma,
            oferta.desconto or 0,
        )

        # Espaçamento entre publicações.
        if (
            postadas < len(escolhidas)
            and config.espacamento_segundos > 0
        ):
            await asyncio.sleep(
                config.espacamento_segundos
            )

    log.info(
        "Ciclo finalizado: "
        "%d coletadas, "
        "%d aprovadas, "
        "%d selecionadas, "
        "%d postadas",
        len(brutas),
        len(boas),
        len(escolhidas),
        postadas,
    )

    return postadas