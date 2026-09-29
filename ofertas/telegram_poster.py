import io
import logging

import httpx
from PIL import Image
from telegram import (
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from telegram.constants import ParseMode

from .formatter import montar_caption
from .models import Oferta

log = logging.getLogger("ofertas.poster")


def _imagem_valida(
    imagem: str | None,
) -> bool:
    """Verifica se a URL da imagem é válida."""

    if not imagem:
        return False

    imagem = imagem.strip()

    return (
        imagem.startswith("https://")
        or imagem.startswith("http://")
    )


async def _baixar_imagem(
    url: str,
) -> io.BytesIO | None:
    """
    Baixa uma imagem e converte para JPEG.

    Isso resolve principalmente imagens AVIF
    fornecidas pelo AliExpress.
    """

    try:

        headers = {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/153.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "image/avif,image/webp,"
                "image/apng,image/*,*/*;q=0.8"
            ),
            "Referer": (
                "https://pt.aliexpress.com/"
            ),
        }

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30,
            headers=headers,
        ) as client:

            resposta = await client.get(
                url
            )

            resposta.raise_for_status()

            imagem = Image.open(
                io.BytesIO(
                    resposta.content
                )
            )

            # Converte para RGB para garantir
            # compatibilidade com JPEG.
            if imagem.mode not in (
                "RGB",
                "L",
            ):
                imagem = imagem.convert(
                    "RGB"
                )

            elif imagem.mode == "L":
                imagem = imagem.convert(
                    "RGB"
                )

            buffer = io.BytesIO()

            imagem.save(
                buffer,
                format="JPEG",
                quality=90,
                optimize=True,
            )

            buffer.seek(0)

            return buffer

    except Exception as e:

        log.warning(
            "Não foi possível baixar/converter "
            "a imagem: %s",
            e,
        )

        return None


def teclado_oferta(
    o: Oferta,
) -> InlineKeyboardMarkup:
    """
    Cria o botão da oferta.

    O texto é escrito usando Unicode escapado
    para evitar problemas de codificação.
    """

    texto_botao = (
        "\U0001F6D2 Pegar oferta"
    )

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    texto_botao,
                    url=o.url_afiliado,
                )
            ]
        ]
    )


async def postar_oferta(
    bot: Bot,
    oferta: Oferta,
    chat_id: str | int,
    teclado: InlineKeyboardMarkup | None = None,
) -> Message:

    caption = montar_caption(
        oferta
    )

    markup = (
        teclado
        or teclado_oferta(oferta)
    )

    # ==================================================
    # TENTA ENVIAR A IMAGEM
    # ==================================================

    if _imagem_valida(
        oferta.imagem
    ):

        # Primeiro tenta baixar e converter.
        arquivo = await _baixar_imagem(
            oferta.imagem
        )

        if arquivo:

            try:

                return await bot.send_photo(
                    chat_id,
                    photo=arquivo,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=markup,
                )

            except Exception as e:

                log.warning(
                    "Envio da imagem convertida "
                    "falhou (%s), tentando URL",
                    e,
                )

        # ==================================================
        # FALLBACK: TENTA A URL DIRETAMENTE
        # ==================================================

        try:

            return await bot.send_photo(
                chat_id,
                oferta.imagem,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=markup,
            )

        except Exception as e:

            log.warning(
                "send_photo por URL falhou "
                "(%s), enviando como texto",
                e,
            )

    # ==================================================
    # FALLBACK FINAL: TEXTO
    # ==================================================

    return await bot.send_message(
        chat_id,
        caption,
        parse_mode=ParseMode.HTML,
        reply_markup=markup,
        disable_web_page_preview=True,
    )