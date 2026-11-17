FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/modelos

WORKDIR /app

RUN pip install --index-url https://download.pytorch.org/whl/cpu torch

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN useradd --create-home agente && mkdir -p /modelos && chown agente /modelos
USER agente

COPY --chown=agente agente ./agente
COPY --chown=agente data ./data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=300s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "agente.interfaces.api:app", "--host", "0.0.0.0", "--port", "8000"]
