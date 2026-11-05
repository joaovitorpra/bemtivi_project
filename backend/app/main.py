import os

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.api.router import api_router
from app.core.database import get_db

app = FastAPI(
    title="Bemtive SmartTask API",
    description="Gestão de colaboradores, demandas, alocações e busca inteligente de profissionais.",
    version="1.0.0",
)

# Libera o frontend para chamar a API (ajuste FRONTEND_URLS no .env se precisar)
origens = os.getenv("FRONTEND_URLS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origens],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Erros do banco viram respostas claras em vez de "500 Internal Server Error"
@app.exception_handler(IntegrityError)
def erro_integridade(request: Request, exc: IntegrityError):
    detalhe = str(exc.orig).split("\n")[0]
    return JSONResponse(status_code=409, content={"detail": f"Violação de integridade: {detalhe}"})


@app.exception_handler(DBAPIError)
def erro_banco(request: Request, exc: DBAPIError):
    codigo = getattr(exc.orig, "pgcode", None)
    mensagem = str(exc.orig).split("\n")[0]
    if codigo and codigo.startswith("22"):  # dados inválidos (ex.: RAISE ... ERRCODE='22023')
        return JSONResponse(status_code=400, content={"detail": mensagem})
    return JSONResponse(status_code=500, content={"detail": "Erro no banco de dados"})


app.include_router(api_router)


@app.get("/", tags=["Status"])
def read_root():
    return {"message": "Bem-vindo ao Bemtive SmartTask API!", "docs": "/docs"}


@app.get("/teste-banco", tags=["Status"])
def teste_banco(db: Session = Depends(get_db)):
    total = db.execute(text('SELECT count(*) FROM "InHire".colaboradores')).scalar()
    ranking = db.execute(text(
        "SELECT * FROM \"InHire\".ranking_skills(2026, 10, ARRAY['Java','React']) LIMIT 3"
    )).mappings().all()
    return {"colaboradores": total, "ranking": ranking}