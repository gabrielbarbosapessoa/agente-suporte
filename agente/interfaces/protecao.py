import hmac
import threading
import time
from collections import defaultdict, deque
from datetime import date

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from agente import config

esquema_chave = APIKeyHeader(name="X-API-Key", auto_error=False)


def exigir_chave(chave: str | None = Security(esquema_chave)) -> None:
    if not chave or not config.API_KEY or not hmac.compare_digest(chave, config.API_KEY):
        raise HTTPException(status_code=401, detail="Chave de API inválida ou ausente")


class LimitadorDeUso:
    def __init__(self, por_minuto: int, por_dia: int):
        self.por_minuto = por_minuto
        self.por_dia = por_dia
        self._janelas: dict[str, deque] = defaultdict(deque)
        self._dia = date.today()
        self._total_hoje = 0
        self._trava = threading.Lock()

    def registrar(self, cliente: str) -> None:
        agora = time.monotonic()
        with self._trava:
            if date.today() != self._dia:
                self._dia = date.today()
                self._total_hoje = 0
                self._janelas.clear()
            if self._total_hoje >= self.por_dia:
                raise HTTPException(status_code=429, detail="A demo atingiu o limite de mensagens de hoje")
            janela = self._janelas[cliente]
            while janela and agora - janela[0] > 60:
                janela.popleft()
            if len(janela) >= self.por_minuto:
                raise HTTPException(
                    status_code=429,
                    detail="Muitas mensagens em pouco tempo. Aguarde um minuto.",
                    headers={"Retry-After": "60"},
                )
            janela.append(agora)
            self._total_hoje += 1


limitador = LimitadorDeUso(config.LIMITE_POR_MINUTO, config.LIMITE_DIARIO_MENSAGENS)


def limitar_uso(request: Request) -> None:
    cliente = request.client.host if request.client else "desconhecido"
    limitador.registrar(cliente)
