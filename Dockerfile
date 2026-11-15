# Standalone Mikasa UNO bot. Python 3.14 comes from uv, so no Python packages are needed on the host.
FROM node:22-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_LINK_MODE=copy

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /usr/local/bin/uv

WORKDIR /app
COPY requirements.txt .python-version ./
RUN uv python install --no-bin "$(cat .python-version)" \
 && uv venv --python "$(cat .python-version)" /opt/venv \
 && uv pip install --python /opt/venv/bin/python --no-cache -r requirements.txt
ENV PATH="/opt/venv/bin:${PATH}"

COPY . .
EXPOSE 10000
CMD ["python", "bot.py"]
