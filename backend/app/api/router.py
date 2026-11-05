from fastapi import APIRouter

from app.api import alocacoes, colaboradores, contratos, demandas, dominios, ia_search, talentflow, talentos, utilizacao

api_router = APIRouter()
api_router.include_router(dominios.router)
api_router.include_router(dominios.skills_router)
api_router.include_router(colaboradores.router)
api_router.include_router(contratos.router)
api_router.include_router(demandas.router)
api_router.include_router(alocacoes.router)
api_router.include_router(talentos.router)
api_router.include_router(ia_search.router)
api_router.include_router(talentflow.router)
api_router.include_router(utilizacao.router)

from app.api import email as email_api
api_router.include_router(email_api.router)
