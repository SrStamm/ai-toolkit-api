# -- Etapa 1: Builder
FROM python:3.12-slim AS builder

# Instala uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /build

# Copia e instala las dependencias
COPY app/requirements.txt .
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache \
        --index-strategy unsafe-best-match \
        torch==2.11.0 \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        -r requirements.txt && \
    rm -rf /opt/venv/nvidia /opt/venv/torch/lib/libcuda* /opt/venv/triton

# -- Etapa 2: Production
FROM python:3.12-slim AS production

WORKDIR /backend

# Crea el usuario y directorio primero
RUN useradd -m appuser && \
    mkdir -p /home/appuser/.cache/huggingface && \
    mkdir -p /backend/api_data && \
    chown -R appuser:appuser /home/appuser /backend/api_data

# Evita warnings
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

# Copia ÚNICAMENTE el entorno virtual ya preparado
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiamos código
COPY --chown=appuser:appuser ./app ./app

ENV PATH="/usr/local/bin:$PATH"

# Usuario no root
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--workers", "1", "--host", "0.0.0.0", "--port", "8000"]
