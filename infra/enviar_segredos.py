import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

CHAVES = ["GOOGLE_API_KEY", "LANGSMITH_API_KEY", "HF_TOKEN", "API_KEY"]

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

faltando = [c for c in CHAVES if not os.getenv(c)]
if faltando:
    sys.exit(f"Faltam no .env: {', '.join(faltando)}")

segredo = json.dumps({c: os.environ[c] for c in CHAVES})
subprocess.run(
    ["aws", "secretsmanager", "put-secret-value", "--secret-id", "novabyte/app", "--secret-string", segredo],
    check=True,
    stdout=subprocess.DEVNULL,
)
print("Segredos enviados para o Secrets Manager: " + ", ".join(CHAVES))
