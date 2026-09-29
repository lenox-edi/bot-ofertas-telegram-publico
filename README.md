# Bot de Ofertas para Telegram

Versão pública do projeto para uso independente. Cada instalação deve utilizar seu próprio bot, canal e credenciais.

## 🎯 Objetivo do projeto

Este projeto foi criado para disponibilizar gratuitamente um bot de ofertas para Telegram.

A ideia surgiu porque, ao procurar tutoriais e soluções semelhantes, encontrei muitas opções que envolviam custos ou serviços pagos.

Por isso, este projeto foi disponibilizado publicamente para que outras pessoas possam aprender, instalar, modificar e utilizar o bot sem precisar comprar uma solução pronta.

**Projeto gratuito e aberto para a comunidade.**

> O código é disponibilizado gratuitamente, mas serviços externos, APIs de afiliados, hospedagem e outros recursos de terceiros podem ter suas próprias regras, limites ou custos.

## Implantação no Railway
1. Faça um Fork deste repositório para sua conta GitHub.
2. Acesse https://railway.com/ e escolha **New Project → Deploy from GitHub repo**.
3. Autorize o GitHub e selecione seu fork.
4. Nas variáveis do serviço, configure `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_OWNER_ID`, `PANEL_USER` e `PANEL_PASSWORD`.
5. Configure as credenciais das plataformas de afiliados que pretende utilizar: `ML_ETIQUETA`, `AMAZON_TAG`, `AMAZON_CREDENTIAL_ID`, `AMAZON_CREDENTIAL_SECRET`, `SHOPEE_APP_ID` e `SHOPEE_APP_SECRET`.
6. Faça o deploy e acompanhe os logs. Gere um domínio público nas configurações do serviço para acessar o painel.

Crie seu bot com o [@BotFather](https://t.me/BotFather), adicione-o como administrador do canal e conceda permissão para publicar. Nunca compartilhe tokens ou senhas.

## Executar no Windows
Instale o [uv](https://docs.astral.sh/uv/) (`winget install astral-sh.uv`), baixe o ZIP, extraia e abra o PowerShell na pasta. Copie `.env.example` para `.env`, preencha suas próprias credenciais e execute `uv sync`, `uv run python -m ofertas check` e `uv run python -m ofertas run`. Também há o `PAINEL.bat` para iniciar o painel local.

## Atualizações
Com o Railway conectado ao seu fork e configurado para acompanhar a branch `main`, novos commits podem iniciar deploys automaticamente. Verifique as configurações e os logs do serviço.

## Integração com ChatGPT
Se os conectores estiverem disponíveis na sua conta, abra Configurações → Aplicativos e conecte GitHub ou Railway, autorizando apenas as permissões necessárias. Configure segredos diretamente no Railway.

## Segurança
Não publique `.env`, tokens, senhas, sessões do navegador, bancos de dados ou dados pessoais. Use suas próprias contas e respeite os termos das plataformas e as regras de afiliados. Os preços e cupons podem mudar.
