FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV PANEL_PORT=8481

WORKDIR /app

RUN apt-get update && apt-get install -y \
    wget \
    curl \
    ca-certificates \
    xvfb \
    x11vnc \
    fluxbox \
    novnc \
    websockify \
    nginx \
    apache2-utils \
    gettext-base \
    fonts-liberation \
    fonts-dejavu \
    libnss3 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm1 \
    libasound2 \
    libxss1 \
    libxshmfence1 \
    libu2f-udev \
    libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

# Instala o Google Chrome para o login do Mercado Livre
RUN wget -q -O /tmp/google-chrome.deb \
      https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y /tmp/google-chrome.deb \
    && rm -f /tmp/google-chrome.deb \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Corrige arquivos criados no Windows com quebra de linha CRLF
RUN sed -i 's/\r$//' /app/start_railway.sh /app/nginx.conf.template \
    && chmod +x /app/start_railway.sh

RUN pip install --no-cache-dir uv

RUN uv sync

RUN uv run playwright install chromium

RUN mkdir -p /app/data /ms-playwright /tmp/.X11-unix

COPY nginx.conf.template /etc/nginx/templates/default.conf.template

EXPOSE 8080

CMD ["/app/start_railway.sh"]