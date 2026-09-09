FROM node:22-bookworm-slim AS node
FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm

COPY requirements.txt package.json package-lock.json ./
RUN pip install -r requirements.txt && npm ci --omit=dev

COPY damage_agent/ damage_agent/
COPY frontend/ frontend/
COPY calculator/ calculator/
COPY data/ data/
COPY public/ public/
COPY .chainlit/config.toml .chainlit/config.toml
COPY chainlit_app.py chainlit.md ./

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 10000
CMD ["sh", "-c", "exec chainlit run chainlit_app.py --headless --host 0.0.0.0 --port ${PORT:-10000}"]
