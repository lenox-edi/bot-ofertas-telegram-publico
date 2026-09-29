import asyncio
import logging

from telegram import Bot

from .config import config, dentro_do_horario
from .cupons import preparar_cupons, registrar
from .cupom_poster import postar_cupom

log = logging.getLogger("ofertas.cupom_pipeline")


async def executar_ciclo(bot: Bot) -> int:
    if not config.cupons_ativa or not dentro_do_horario():
        return 0

    cupons = await asyncio.to_thread(
        preparar_cupons,
        config.cupons_max_posts,
        config.cupons_nao_repetir_dias,
    )

    log.info("Cupons: %d selecionados para publicação", len(cupons))
    postadas = 0

    for cupom in cupons:
        try:
            await postar_cupom(bot, cupom, config.chat_id)
            registrar(cupom)
            postadas += 1
        except Exception as e:
            log.error("Falha ao publicar cupom %s: %s", cupom.codigo, e)

        if postadas < len(cupons) and config.cupons_espacamento_segundos > 0:
            await asyncio.sleep(config.cupons_espacamento_segundos)

    return postadas
