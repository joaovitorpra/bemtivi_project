"""Envio de e-mail (ex.: aviso de alocação) via SMTP.

Configuração no backend/.env:
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587                # 587 = STARTTLS, 465 = SSL
    SMTP_USER=seu_email@gmail.com
    SMTP_PASSWORD=senha_de_app
    SMTP_FROM=Alocação <seu_email@gmail.com>   # opcional; padrão = SMTP_USER

Atenção: a API ainda não tem autenticação. Antes de publicá-la na internet,
proteja esta rota, senão qualquer pessoa poderá enviar e-mails pela sua conta.
"""

import os
import re
import smtplib
import ssl
from email.message import EmailMessage

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/email", tags=["E-mail"])

EMAIL_RE = re.compile(r"^[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+$")


class EmailEntrada(BaseModel):
    para: str = Field(min_length=3, max_length=254)
    cc: list[str] = Field(default_factory=list, max_length=10)
    assunto: str = Field(min_length=1, max_length=200)
    mensagem: str = Field(min_length=1, max_length=10000)


def _configuracao():
    host = os.getenv("SMTP_HOST")
    usuario = os.getenv("SMTP_USER")
    senha = os.getenv("SMTP_PASSWORD")
    if not (host and usuario and senha):
        raise HTTPException(
            status_code=503,
            detail="Envio de e-mail não configurado: defina SMTP_HOST, SMTP_USER e SMTP_PASSWORD no .env do backend.",
        )
    try:
        porta = int(os.getenv("SMTP_PORT", "587"))
    except ValueError:
        raise HTTPException(status_code=503, detail="SMTP_PORT inválida no .env.")
    remetente = os.getenv("SMTP_FROM") or usuario
    return host, porta, usuario, senha, remetente


def _validar_enderecos(dados: EmailEntrada) -> list[str]:
    enderecos = [dados.para.strip(), *[c.strip() for c in dados.cc if c.strip()]]
    invalidos = [e for e in enderecos if not EMAIL_RE.match(e)]
    if invalidos:
        raise HTTPException(status_code=422, detail=f"E-mail inválido: {', '.join(invalidos)}")
    if "\n" in dados.assunto or "\r" in dados.assunto:
        raise HTTPException(status_code=422, detail="O assunto não pode ter quebra de linha.")
    return enderecos


@router.post("/enviar")
def enviar_email(dados: EmailEntrada):
    enderecos = _validar_enderecos(dados)
    host, porta, usuario, senha, remetente = _configuracao()

    msg = EmailMessage()
    msg["From"] = remetente
    msg["To"] = enderecos[0]
    if len(enderecos) > 1:
        msg["Cc"] = ", ".join(enderecos[1:])
    msg["Subject"] = dados.assunto.strip()
    msg.set_content(dados.mensagem)

    contexto = ssl.create_default_context()
    try:
        if porta == 465:
            with smtplib.SMTP_SSL(host, porta, context=contexto, timeout=20) as smtp:
                smtp.login(usuario, senha)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, porta, timeout=20) as smtp:
                smtp.starttls(context=contexto)
                smtp.login(usuario, senha)
                smtp.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(
            status_code=502,
            detail="O servidor de e-mail recusou o login. Confira SMTP_USER e SMTP_PASSWORD (no Gmail, use uma senha de app).",
        )
    except (smtplib.SMTPException, OSError) as erro:
        raise HTTPException(status_code=502, detail=f"Não foi possível enviar o e-mail: {erro}")

    return {"enviado": True, "para": enderecos[0], "cc": enderecos[1:]}
