import io
import logging
import re
from html import escape

from PIL import Image, ImageDraw, ImageFont
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.constants import ParseMode

from .cupons import Cupom

log = logging.getLogger("ofertas.cupom_poster")


IMAGENS_CUPOM = {
    "aliexpress": "https://www.melhorescartoes.com.br/wp-content/uploads/2026/05/novos-cupons-aliexpress-1-1536x806.jpg",
    "mercado livre": "https://www.melhorescartoes.com.br/wp-content/uploads/2026/04/novos-cupons-mercado-livre-capa-01-1536x806.jpg",
    "amazon": "https://www.melhorescartoes.com.br/wp-content/uploads/2026/04/cupom-amazon-capa-01-1536x806.jpg",
}


def _font(size: int, bold: bool = False):
    caminhos = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for caminho in caminhos:
        try:
            return ImageFont.truetype(caminho, size)
        except Exception:
            pass
    return ImageFont.load_default()


def criar_arte(cupom: Cupom) -> io.BytesIO:
    largura, altura = 1200, 675
    imagem = Image.new("RGB", (largura, altura), "white")
    draw = ImageDraw.Draw(imagem)

    draw.rectangle((0, 0, largura, 150), fill="black")
    draw.text((60, 42), cupom.plataforma.upper(), fill="white", font=_font(58, True))
    draw.text((60, 185), "CUPOM DE DESCONTO", fill="black", font=_font(44, True))

    if cupom.desconto:
        draw.text((60, 260), cupom.desconto.upper(), fill="black", font=_font(54, True))

    draw.rounded_rectangle((60, 350, 1140, 490), radius=24, outline="black", width=4)
    draw.text((95, 390), cupom.codigo, fill="black", font=_font(54, True))

    draw.text((60, 525), "VÁLIDO PARA BRASIL • CONFIRA AS CONDIÇÕES NO CHECKOUT",
              fill="black", font=_font(24, True))

    buffer = io.BytesIO()
    imagem.save(buffer, format="JPEG", quality=92)
    buffer.seek(0)
    return buffer


def imagem_url(cupom: Cupom) -> str | None:
    plataforma = re.sub(r"\s+", " ", (cupom.plataforma or "").strip().lower())
    return IMAGENS_CUPOM.get(plataforma)


def teclado(cupom: Cupom) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎟️ PEGAR CUPOM", url=cupom.url)]
    ])


def _formatar_valor(valor: str) -> str:
    valor = valor.strip().replace("R$", "").strip()
    return f"R$ {valor}"


def _resumo_condicao(cupom: Cupom) -> list[str]:
    texto = re.sub(r"\s+", " ", cupom.condicao or "").strip()
    if not texto:
        return []

    linhas = []

    minimo = re.search(r"compra\s+a\s+partir\s+de\s+R\$\s*([\d.,]+)", texto, re.I)
    if minimo:
        linhas.append(f"🛒 Compras a partir de {_formatar_valor(minimo.group(1))}")

    maximo = re.search(r"desconto\s+m[aá]ximo\s+de\s+R\$\s*([\d.,]+)", texto, re.I)
    if maximo:
        linhas.append(f"💵 Desconto máximo de {_formatar_valor(maximo.group(1))}")

    if re.search(r"itens\s+eleg[ií]veis", texto, re.I):
        linhas.append("📦 Válido para itens elegíveis")

    if not linhas:
        texto_curto = re.sub(r"https?://\S+|www\.\S+|mercadolivre\.com\.br/\S+", "", texto, flags=re.I)
        texto_curto = re.sub(r"\s+", " ", texto_curto).strip(" .")
        if texto_curto:
            linhas.append(f"🛒 {texto_curto[:180]}")

    return linhas


def caption(cupom: Cupom) -> str:
    partes = [
        f"🚨 <b>NOVO CUPOM {escape(cupom.plataforma.upper())}!</b> 🔥",
        "",
        f"🎟️ <b>{escape(cupom.codigo)}</b>",
    ]

    if cupom.desconto:
        desconto = cupom.desconto.strip()
        if re.match(r"até\s+", desconto, re.I):
            desconto = re.sub(r"^até\s+", "Até ", desconto, flags=re.I)
        partes.append(f"💰 <b>{escape(desconto)} OFF</b>")

    partes.extend(escape(linha) for linha in _resumo_condicao(cupom))

    partes += [
        "",
        "🇧🇷 <b>Válido para Brasil</b>",
        "",
        "⚠️ Cupom sujeito a limite de uso e condições. Confira a disponibilidade no checkout.",
    ]

    return "\n".join(partes)


async def postar_cupom(bot: Bot, cupom: Cupom, chat_id: str | int) -> Message:
    try:
        foto = imagem_url(cupom)
        if foto:
            return await bot.send_photo(
                chat_id,
                photo=foto,
                caption=caption(cupom),
                parse_mode=ParseMode.HTML,
                reply_markup=teclado(cupom),
            )

        return await bot.send_photo(
            chat_id,
            photo=criar_arte(cupom),
            caption=caption(cupom),
            parse_mode=ParseMode.HTML,
            reply_markup=teclado(cupom),
        )
    except Exception as e:
        log.warning("Falha ao enviar imagem externa do cupom: %s", e)

        try:
            return await bot.send_photo(
                chat_id,
                photo=criar_arte(cupom),
                caption=caption(cupom),
                parse_mode=ParseMode.HTML,
                reply_markup=teclado(cupom),
            )
        except Exception as e2:
            log.warning("Falha ao enviar arte de fallback do cupom: %s", e2)
            return await bot.send_message(
                chat_id,
                caption(cupom),
                parse_mode=ParseMode.HTML,
                reply_markup=teclado(cupom),
                disable_web_page_preview=True,
            )
