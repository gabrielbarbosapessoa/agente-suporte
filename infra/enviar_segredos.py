import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

CHAVES = ["GOOGLE_API_KEY", "LANGSMITH_API_KEY", "HF_TOKEN", "API_KEY"]
REGIAO = os.getenv("AWS_REGIAO", "us-east-1")
SEGREDO = "novabyte/app"

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

faltando = [c for c in CHAVES if not os.getenv(c)]
if faltando:
    sys.exit(f"Faltam no .env: {', '.join(faltando)}")

segredo = json.dumps({c: os.environ[c] for c in CHAVES})
resultado = subprocess.run(
    ["aws", "secretsmanager", "put-secret-value", "--region", REGIAO, "--secret-id", SEGREDO, "--secret-string", segredo],
    capture_output=True,
    text=True,
)
if resultado.returncode != 0:
    sys.exit(f"Falha ao enviar os segredos para {SEGREDO} em {REGIAO}:\n{resultado.stderr.strip()}")
print(f"Segredos enviados para {SEGREDO} em {REGIAO}: " + ", ".join(CHAVES))
