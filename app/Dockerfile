# -- Etapa 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /build

# Instala dependencias de compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libopenblas-dev \
    gfortran \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Crea venv y lo pone en el PATH
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copia e instala las dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir \
       --extra-index-url https://download.pytorch.org/whl/cpu \
       -r requirements.txt

# -- Etapa 2: Production
FROM python:3.12-slim AS production

WORKDIR /backend

# Evita warnings
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

# Copia ÚNICAMENTE el entorno virtual ya preparado
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiamos código
COPY . ./app/

ENV PATH="/usr/local/bin:$PATH"

# Usuario no root
RUN useradd -m appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--workers", "1", "--host", "0.0.0.0", "--port", "8000"]
