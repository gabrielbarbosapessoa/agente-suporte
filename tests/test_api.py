import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from agente import config
from agente.interfaces.api import app
from agente.interfaces.protecao import LimitadorDeUso

CHAVE = "chave-de-teste"


@pytest.fixture
def cliente(monkeypatch):
    monkeypatch.setattr(config, "API_KEY", CHAVE)
    monkeypatch.setattr(config, "DEMO_PUBLICA", False)
    return TestClient(app)


def test_health_nao_exige_chave(cliente):
    assert cliente.get("/health").json() == {"status": "ok"}


def test_sem_chave_recebe_401(cliente):
    assert cliente.post("/conversas").status_code == 401


def test_chave_errada_recebe_401(cliente):
    assert cliente.post("/conversas", headers={"X-API-Key": "errada"}).status_code == 401


def test_cria_conversa_com_chave(cliente):
    resposta = cliente.post("/conversas", headers={"X-API-Key": CHAVE})
    assert resposta.status_code == 201
    assert resposta.json()["thread_id"].startswith("sessao-")


def test_thread_id_fora_do_formato_recebe_422(cliente):
    resposta = cliente.get("/conversas/1", headers={"X-API-Key": CHAVE})
    assert resposta.status_code == 422


def test_mensagem_vazia_recebe_422(cliente):
    thread = "sessao-" + "a" * 32
    resposta = cliente.post(f"/conversas/{thread}/mensagens", json={"mensagem": ""}, headers={"X-API-Key": CHAVE})
    assert resposta.status_code == 422


def test_limite_por_minuto():
    limitador = LimitadorDeUso(por_minuto=2, por_dia=100)
    limitador.registrar("1.1.1.1")
    limitador.registrar("1.1.1.1")
    with pytest.raises(HTTPException) as erro:
        limitador.registrar("1.1.1.1")
    assert erro.value.status_code == 429
    limitador.registrar("2.2.2.2")


def test_limite_diario_vale_para_todos():
    limitador = LimitadorDeUso(por_minuto=10, por_dia=2)
    limitador.registrar("1.1.1.1")
    limitador.registrar("2.2.2.2")
    with pytest.raises(HTTPException) as erro:
        limitador.registrar("3.3.3.3")
    assert "limite" in erro.value.detail


def test_modo_demo_dispensa_chave(cliente, monkeypatch):
    monkeypatch.setattr(config, "DEMO_PUBLICA", True)
    assert cliente.post("/conversas").status_code == 201


def test_pagina_do_chat(cliente):
    resposta = cliente.get("/chat")
    assert resposta.status_code == 200
    assert "text/html" in resposta.headers["content-type"]
