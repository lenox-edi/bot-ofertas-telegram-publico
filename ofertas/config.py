
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

os.environ.setdefault(
    "PLAYWRIGHT_BROWSERS_PATH",
    str(DATA_DIR / "pw-browsers"),
)

# No Railway, a configuração salva pelo painel fica em DATA_DIR,
# que é montado em um Volume persistente. O arquivo antigo na raiz
# continua sendo aceito para manter compatibilidade local.
load_dotenv(BASE_DIR / ".env")
load_dotenv(DATA_DIR / ".env", override=True)


def _ler_yaml() -> dict:
    caminho = BASE_DIR / "config.yaml"

    if not caminho.exists():
        return {}

    with open(caminho, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class Config:

    def __init__(self):
        y = _ler_yaml()

        geral = y.get("geral") or {}
        filtros = y.get("filtros") or {}

        self.bot_token: str = os.getenv(
            "TELEGRAM_BOT_TOKEN",
            "",
        ).strip()

        self.chat_id: str = os.getenv(
            "TELEGRAM_CHAT_ID",
            "",
        ).strip()

        self.owner_id: int = int(
            os.getenv(
                "TELEGRAM_OWNER_ID",
                "0",
            ).strip()
            or 0
        )

        self.amazon_tag: str = os.getenv(
            "AMAZON_TAG",
            "",
        ).strip()

        self.amazon_credential_id: str = os.getenv(
            "AMAZON_CREDENTIAL_ID",
            "",
        ).strip()

        self.amazon_credential_secret: str = os.getenv(
            "AMAZON_CREDENTIAL_SECRET",
            "",
        ).strip()

        self.ml_etiqueta: str = os.getenv(
            "ML_ETIQUETA",
            "",
        ).strip()

        self.shopee_app_id: str = os.getenv(
            "SHOPEE_APP_ID",
            "",
        ).strip()

        self.shopee_app_secret: str = os.getenv(
            "SHOPEE_APP_SECRET",
            "",
        ).strip()

        self.intervalo_minutos: int = int(
            geral.get(
                "intervalo_minutos",
                45,
            )
        )

        self.max_posts_por_ciclo: int = int(
            geral.get(
                "max_posts_por_ciclo",
                3,
            )
        )

        self.espacamento_segundos: int = int(
            geral.get(
                "espacamento_segundos",
                120,
            )
        )

        self.nao_repetir_dias: int = int(
            geral.get(
                "nao_repetir_dias",
                7,
            )
        )

        self.horario_ativo: str = str(
            geral.get(
                "horario_ativo",
                "",
            )
            or ""
        ).strip()

        self.desconto_minimo: int = int(
            filtros.get(
                "desconto_minimo",
                0,
            )
        )

        self.preco_minimo: float = float(
            filtros.get(
                "preco_minimo",
                0,
            )
        )

        self.preco_maximo: float = float(
            filtros.get(
                "preco_maximo",
                0,
            )
        )

        self.palavras_bloqueadas: list[str] = [
            str(p).lower()
            for p in (
                filtros.get("palavras_bloqueadas")
                or []
            )
        ]

        fontes = y.get("fontes") or {}

        self.fonte_ml: dict = (
            fontes.get("mercadolivre")
            or {"ativa": False}
        )

        self.fonte_shopee: dict = (
            fontes.get("shopee")
            or {"ativa": False}
        )

        self.fonte_amazon: dict = (
            fontes.get("amazon")
            or {"ativa": False}
        )

        self.fonte_aliexpress: dict = (
            fontes.get("aliexpress")
            or {"ativa": False}
        )

        cupons = y.get("cupons") or {}
        self.cupons_ativa: bool = bool(cupons.get("ativa", True))
        self.cupons_intervalo_minutos: int = int(
            cupons.get("intervalo_minutos", 30)
        )
        self.cupons_max_posts: int = int(
            cupons.get("max_posts_por_ciclo", 3)
        )
        self.cupons_espacamento_segundos: int = int(
            cupons.get("espacamento_segundos", 20)
        )
        self.cupons_nao_repetir_dias: int = int(
            cupons.get("nao_repetir_dias", 3)
        )

        # Seleção de nichos feita no painel
        # (data/nichos.json).
        #
        # Se houver seleção, ela substitui
        # categorias/departamentos/buscas do config.yaml.
        #
        # Nenhum nicho selecionado mantém o config.yaml.

        self.nichos: list[str] = []

        try:
            from .nichos import expandir, ler_selecao

            self.nichos = ler_selecao()

            if self.nichos:
                exp = expandir(self.nichos)

                self.fonte_ml = {
                    **self.fonte_ml,
                    "categorias": exp["ml"],
                }

                self.fonte_amazon = {
                    **self.fonte_amazon,
                    "departamentos": exp["amazon_dep"],
                    "buscas": exp["amazon_buscas"],
                }

                self.fonte_shopee = {
                    **self.fonte_shopee,
                    "buscas": exp["shopee"],
                }

        except Exception:
            pass


config = Config()


def dentro_do_horario(agora: datetime | None = None) -> bool:

    if not config.horario_ativo:
        return True

    if agora is None:
        agora = datetime.now(ZoneInfo("America/Manaus"))
    elif agora.tzinfo is None:
        # Horário informado sem fuso:
        # considera-se o horário de Manaus.
        agora = agora.replace(
            tzinfo=ZoneInfo("America/Manaus")
        )
    else:
        # Converte horários com fuso para Manaus.
        agora = agora.astimezone(
            ZoneInfo("America/Manaus")
        )

    try:
        inicio, fim = config.horario_ativo.split(
            "-",
            1,
        )

        h_inicio, m_inicio = map(
            int,
            inicio.split(":"),
        )

        h_fim, m_fim = map(
            int,
            fim.split(":"),
        )

        minutos_agora = (
            agora.hour * 60
            + agora.minute
        )

        minutos_inicio = (
            h_inicio * 60
            + m_inicio
        )

        minutos_fim = (
            h_fim * 60
            + m_fim
        )

        if minutos_inicio <= minutos_fim:
            return (
                minutos_inicio
                <= minutos_agora
                <= minutos_fim
            )

        # Horário atravessando meia-noite.
        return (
            minutos_agora >= minutos_inicio
            or minutos_agora <= minutos_fim
        )

    except Exception:
        return True


def verificar() -> list[str]:

    pendencias = []

    if not config.bot_token:
        pendencias.append(
            "TELEGRAM_BOT_TOKEN não configurado"
        )

    if not config.chat_id:
        pendencias.append(
            "TELEGRAM_CHAT_ID não configurado"
        )

    if not config.owner_id:
        pendencias.append(
            "TELEGRAM_OWNER_ID não configurado"
        )

    # Amazon:
    # A coleta pública pode funcionar sem afiliado.
    # AMAZON_TAG continua sendo necessário apenas
    # para recursos de afiliado/conversão.

    if config.fonte_amazon.get("ativa"):
        if not config.amazon_tag:
            pendencias.append(
                "AMAZON_TAG não configurado "
                "(necessário para links de afiliado)"
            )

        if not (
            config.amazon_credential_id
            and config.amazon_credential_secret
        ):
            pendencias.append(
                "AMAZON_CREDENTIAL_ID / "
                "AMAZON_CREDENTIAL_SECRET "
                "não configurados "
                "(necessários para a API oficial)"
            )

    # Shopee:
    # As credenciais continuam sendo necessárias
    # para a API oficial e para gerar links de afiliado.

    if config.fonte_shopee.get("ativa"):
        if not (
            config.shopee_app_id
            and config.shopee_app_secret
        ):
            pendencias.append(
                "SHOPEE_APP_ID / "
                "SHOPEE_APP_SECRET "
                "não configurados "
                "(necessários para a API de afiliados)"
            )

    # Mercado Livre:
    # ML_ETIQUETA é necessária somente para
    # geração de links de afiliado.

    if config.fonte_ml.get("ativa"):
        if not config.ml_etiqueta:
            pendencias.append(
                "ML_ETIQUETA não configurado "
                "(necessário para links de afiliado)"
            )

    # AliExpress não exige credenciais para
    # a coleta pública implementada no projeto.

    return pendencias