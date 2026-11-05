"""Testes da rota de e-mail. Não enviam e-mail de verdade: o SMTP é substituído por um falso."""

import smtplib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import email as email_api

app = FastAPI()
app.include_router(email_api.router)
cliente = TestClient(app)

CORPO = {
    "para": "colaborador@empresa.com",
    "cc": ["gestor@empresa.com"],
    "assunto": "Você foi alocado(a) em Projeto X",
    "mensagem": "Olá!\n\nVocê foi alocado(a).",
}


class SMTPFalso:
    enviados = []

    def __init__(self, host, porta, **kwargs):
        self.host, self.porta = host, porta

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self, context=None):
        pass

    def login(self, usuario, senha):
        if senha == "errada":
            raise smtplib.SMTPAuthenticationError(535, b"auth failed")

    def send_message(self, msg):
        SMTPFalso.enviados.append(msg)


@pytest.fixture
def smtp_configurado(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.teste.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "remetente@empresa.com")
    monkeypatch.setenv("SMTP_PASSWORD", "senha")
    monkeypatch.delenv("SMTP_FROM", raising=False)
    monkeypatch.setattr(email_api.smtplib, "SMTP", SMTPFalso)
    SMTPFalso.enviados = []


def test_envia_email(smtp_configurado):
    r = cliente.post("/api/email/enviar", json=CORPO)
    assert r.status_code == 200
    assert r.json() == {"enviado": True, "para": "colaborador@empresa.com", "cc": ["gestor@empresa.com"]}
    msg = SMTPFalso.enviados[0]
    assert msg["To"] == "colaborador@empresa.com"
    assert msg["Cc"] == "gestor@empresa.com"
    assert msg["From"] == "remetente@empresa.com"
    assert msg["Subject"] == CORPO["assunto"]


def test_sem_configuracao_retorna_503(monkeypatch):
    for var in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"):
        monkeypatch.delenv(var, raising=False)
    r = cliente.post("/api/email/enviar", json=CORPO)
    assert r.status_code == 503
    assert "SMTP_HOST" in r.json()["detail"]


def test_email_invalido_retorna_422(smtp_configurado):
    r = cliente.post("/api/email/enviar", json={**CORPO, "para": "nao-e-email"})
    assert r.status_code == 422
    assert SMTPFalso.enviados == []


def test_assunto_com_quebra_de_linha_retorna_422(smtp_configurado):
    r = cliente.post("/api/email/enviar", json={**CORPO, "assunto": "Oi\nBcc: outro@x.com"})
    assert r.status_code == 422


def test_login_recusado_retorna_502(smtp_configurado, monkeypatch):
    monkeypatch.setenv("SMTP_PASSWORD", "errada")
    r = cliente.post("/api/email/enviar", json=CORPO)
    assert r.status_code == 502
    assert "senha de app" in r.json()["detail"]
