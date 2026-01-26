# -- Etapa 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /build

# Instalamos dependencias de compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 1. Creamos el entorno virtual
RUN python -m venv /opt/venv
# 2. "Activamos" el entorno para el resto del builder poniendo el binario primero en el PATH
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

# 3. Instalamos usando el índice de CPU para evitar librerías NVIDIA
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

# -- Etapa 2: Production
FROM python:3.12-slim AS production

WORKDIR /backend

# 4. Copiamos ÚNICAMENTE el entorno virtual ya preparado
COPY --from=builder /opt/venv /opt/venv

# 5. Activamos el entorno en la imagen final
ENV PATH="/opt/venv/bin:$PATH"

# Copiamos tu código
COPY . ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
