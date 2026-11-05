# 🚀 Bemtive SmartTask — Platform & API

Plataforma inteligente de alocação de tarefas e gestão de talentos. O projeto utiliza **FastAPI** no backend, **SQLAlchemy** como ORM, **Supabase (PostgreSQL)** como banco de dados na nuvem e **React + Vite** no frontend.

---

## 🛠️ Tecnologias e Ferramentas

- **Backend:** Python 3.13+, FastAPI, SQLAlchemy 2, Pydantic 2, Uvicorn
- **Banco de Dados:** Supabase PostgreSQL (conexão via Session Pooler com `psycopg2-binary`)
- **Migrações:** Alembic (configurado em modo seguro, sem risco de apagar tabelas)
- **Testes:** Pytest (53 testes automatizados cobrindo todas as rotas)
- **Configuração:** `python-dotenv` (credenciais no arquivo `.env`, fora do Git)
- **Infraestrutura/OS:** Windows 10/11, WSL 2, VS Code
- **Frontend:** React + Vite *(em fase de planejamento e integração)*

---

## 📋 Histórico do Projeto e Resolução de Problemas

Durante o desenvolvimento inicial do ambiente local:

1. **Virtualização & WSL 2:** Foram ativados os componentes do Windows (`wsl --install` e `VirtualMachinePlatform`) para dar suporte à virtualização e containers.
2. **Migração para Supabase Cloud:** Para contornar bloqueios de firmware/BIOS (`Virtualization is disabled in firmware`) sem perder tempo de desenvolvimento, a base de dados foi migrada para o **Supabase PostgreSQL**.
3. **Carga Inicial do Banco:** O dump `01-hackathon.sql` (gerado pelo `pg_dump` 18) não rodava no SQL Editor do Supabase por três motivos, que foram corrigidos sem alterar nenhuma tabela ou dado:
   - os meta-comandos `\restrict` / `\unrestrict` do `psql` causavam `syntax error at or near "restrict"`;
   - os blocos `COPY ... FROM stdin` não são suportados pelo editor web e foram convertidos em `INSERT`;
   - o `SET transaction_timeout` (exclusivo do PostgreSQL 17+) foi removido.

   O arquivo convertido foi dividido em duas partes e executado em ordem. A carga foi validada pela contagem de registros (279 colaboradores, 11.727 skills de colaboradores, 4.744 planejamentos e 300 talentos).
4. **Configuração de Conexão:** O backend se conecta pelo **Session Pooler** do Supabase, porque o endereço direto (`db.[REF].supabase.co`) só funciona via IPv6, indisponível na maioria das redes domésticas. As credenciais ficam no arquivo `.env`, e a URL é montada com `URL.create`, que trata caracteres especiais da senha (como `&` e `/`).
5. **Modelagem e API:** Os models SQLAlchemy foram gerados a partir do schema real `"InHire"`, e foram criadas 29 rotas REST, incluindo a busca inteligente de profissionais.
6. **Testes:** Foi criada uma suíte de 53 testes que roda contra o banco real **sem alterar nenhum dado**: cada teste executa dentro de uma transação desfeita ao final.

---

## 📂 Estrutura do Projeto

```text
bemtive_smartTask/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # Entry point: CORS, tratamento de erros e registro das rotas
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── database.py      # Engine do SQLAlchemy, sessão e conexão com o Supabase
│   │   ├── models/
│   │   │   └── models.py        # Modelos ORM gerados a partir do schema "InHire"
│   │   ├── schemas/
│   │   │   └── schemas.py       # Schemas Pydantic (validação de entrada e saída)
│   │   └── api/
│   │       ├── router.py        # Junta todos os routers
│   │       ├── dominios.py      # Domínios e skills
│   │       ├── colaboradores.py # CRUD de colaboradores + skills
│   │       ├── contratos.py     # Contratos e suas relações
│   │       ├── demandas.py      # CRUD de demandas + skills exigidas
│   │       ├── alocacoes.py     # Alocações e planejamento mensal
│   │       ├── talentos.py      # Banco de talentos externos
│   │       └── ia_search.py     # Busca inteligente de profissionais
│   ├── tests/                   # Testes automatizados (pytest)
│   ├── alembic/                 # Migrações (env.py configurado em modo seguro)
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── requirements.txt         # Dependências da aplicação
│   ├── requirements-dev.txt     # Dependências de desenvolvimento (pytest)
│   ├── .env.example             # Modelo das variáveis de ambiente (sem senha)
│   └── .env                     # Credenciais reais (NÃO vai para o Git)
├── frontend/
└── README.md
```

---

## 🗄️ Banco de Dados

Todas as tabelas ficam no schema **`"InHire"`** (com aspas, pois o nome tem letras maiúsculas).

| Tabela | Descrição |
|---|---|
| `dominios` | Valores de referência (cargo, senioridade, modalidade, nível de conhecimento etc.) |
| `skills` | Catálogo de tecnologias e competências |
| `colaboradores` / `colaborador_skills` | Profissionais internos e suas skills com nível |
| `contratos` | Contratos com clientes |
| `demandas` / `demanda_skills` | Projetos/demandas e as skills que exigem |
| `alocacoes` / `planejamentos` | Quem está em qual demanda e com qual % de dedicação por mês |
| `talentos` / `talento_skills` | Banco de candidatos externos |

O banco também possui funções usadas pela busca inteligente: `buscar_profissionais`, `ranking_skills`, `ranking_talentos`, `disponibilidade_mensal` e `disponibilidade_periodo`, além da view `vw_inconsistencias_dominios`, que aponta registros com domínios inconsistentes.

> **Exclusão lógica:** os registros nunca são apagados; as tabelas usam as colunas `status` e `deletado`.

---

## ⚙️ Configuração do Ambiente Backend

### 1. Requisitos do Sistema
- Python 3.10+ instalado.
- Acesso à internet para conexão com o Supabase.

### 2. Ambiente virtual e dependências
A partir da pasta `backend`:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

O terminal deve mostrar `(venv)` no início da linha.

> Se aparecer o erro *"running scripts is disabled"*, rode uma vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` e ative o venv novamente.

### 3. Variáveis de ambiente (`backend/.env`)
Copie o `.env.example` para `.env` e preencha com os dados do **Session Pooler**. No Supabase, clique em **Connect** e escolha **Session pooler**:

```
DB_USER=postgres.SEU_PROJETO
DB_PASSWORD=sua_senha
DB_HOST=aws-0-sa-east-1.pooler.supabase.com
DB_PORT=5432
DB_NAME=postgres
```

Variáveis opcionais:

```
DB_SSLMODE=require                                   # padrão; use "disable" apenas em banco local
FRONTEND_URLS=http://localhost:3000,http://localhost:5173   # origens liberadas no CORS
```

> ⚠️ **Nunca coloque a senha no código nem envie o `.env` ao Git.** Ele já está listado no `.gitignore`. Se a senha vazar, troque-a em *Project Settings → Database → Reset database password*.

O `app/core/database.py` lê essas variáveis automaticamente e define o `search_path` para o schema `"InHire"`.

---

## 🚦 Como Rodar a Aplicação

A partir da pasta `backend`, com o venv ativo:

```powershell
uvicorn app.main:app --reload
```

Após iniciar o servidor, acesse:
- **Swagger UI (testar as rotas no navegador):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Teste de conexão com o banco:** [http://127.0.0.1:8000/teste-banco](http://127.0.0.1:8000/teste-banco)

---

## 🔌 Endpoints da API

| Grupo | Método | Rota | Descrição |
|---|---|---|---|
| **Status** | GET | `/` | Mensagem de boas-vindas |
| | GET | `/teste-banco` | Verifica a conexão com o Supabase |
| **Domínios** | GET | `/dominios/tipos` | Lista os tipos de domínio |
| | GET | `/dominios?tipo=CARGO` | Lista domínios de um tipo |
| | GET | `/dominios/{id}` | Detalhe de um domínio |
| **Skills** | GET | `/skills?nome=java` | Busca skills por nome ou área |
| **Colaboradores** | GET / POST | `/colaboradores` | Lista (com filtros e paginação) / cria |
| | GET / PATCH / DELETE | `/colaboradores/{id}` | Detalhe (com cargo, senioridade e skills) / edita / exclui |
| | GET / POST | `/colaboradores/{id}/skills` | Lista / adiciona ou atualiza o nível de uma skill |
| | DELETE | `/colaboradores/{id}/skills/{skill_id}` | Remove uma skill |
| **Contratos** | GET | `/contratos`, `/contratos/{id}` | Lista / detalhe |
| | GET | `/contratos/{id}/demandas`, `/contratos/{id}/colaboradores` | Relações do contrato |
| **Demandas** | GET / POST | `/demandas` | Lista / cria (já com as skills exigidas) |
| | GET / PATCH / DELETE | `/demandas/{id}` | Detalhe / edita / exclui |
| | PUT | `/demandas/{id}/skills` | Substitui as skills exigidas (corpo: `[16, 59, 41]`) |
| | GET | `/demandas/{id}/alocacoes` | Alocações da demanda |
| **Alocações** | GET / POST | `/alocacoes` | Lista / aloca um colaborador numa demanda |
| | GET / DELETE | `/alocacoes/{id}` | Detalhe (com planejamentos) / exclui |
| | GET / PUT | `/alocacoes/{id}/planejamentos` | Lista / define a % de dedicação num mês |
| **Talentos** | GET | `/talentos`, `/talentos/{id}` | Banco de candidatos externos |
| **Busca inteligente** | GET | `/busca/profissionais` | Colaboradores com todas as skills e disponibilidade mínima |
| | GET | `/busca/ranking-skills` | Ranking por % de skills atendidas |
| | GET | `/busca/ranking-talentos` | Ranking do banco de talentos externos |
| | GET | `/busca/disponibilidade` | Disponibilidade de cada colaborador no mês |
| | GET | `/busca/disponibilidade-periodo` | Resumo de disponibilidade num período (máx. 61 meses) |
| | GET | `/busca/demandas/{id}/sugestoes` | ⭐ Sugere colaboradores internos e talentos externos para uma demanda |

**Exemplo — sugestões para uma demanda:**

```
GET /busca/demandas/11/sugestoes?ano=2026&mes=11&limit=5
```

A rota lê as skills exigidas pela demanda e devolve os colaboradores mais compatíveis com disponibilidade no mês, além de talentos externos para quando faltar gente interna.

### Regras de negócio
- **Sem sobrealocação:** a soma dos planejamentos de um colaborador num mês não pode passar de 100%. A API recusa com `409` e informa o máximo disponível.
- **Sem alocação duplicada:** um colaborador não pode ser alocado duas vezes na mesma demanda ativa.
- **Validações:** término da demanda ≥ início; mês entre `Jan` e `Dez`; porcentagem entre 0 e 100; nível de skill `BASICO`, `INTERMEDIARIO` ou `AVANCADO`.
- **Exclusão lógica:** `DELETE` marca `deletado = true` em vez de apagar o registro.
- **Erros claros:** violações de chave estrangeira retornam `409`, e erros de validação do banco retornam `400`, com mensagem descritiva.

---

## 🔎 Busca com IA (`POST /api/ia/buscar`)

A busca interpreta o texto por regras e reconhece:
- **Skills** cadastradas (com apelidos como `postgres`, `node`, `k8s`);
- **Cargos** cadastrados, com ou sem acento (ex.: `engenheiro de solucoes`). Quando um cargo contém outro, vale o mais longo ("Analista de Sistemas Desenvolvedor" antes de "Analista de Sistemas"). "Estagiário" e "Trainee" são tratados como senioridade, e palavras comuns que também são cargo (como "contínuo") são ignoradas. Apelidos: `full stack` e `dba`;
- **Senioridade**, **mês** e **urgência**.

Como o resultado é montado:
- Com skills, usa a função `ranking_skills` do banco; com cargo, filtra por ele. Só com cargo, traz as pessoas desse cargo com alguma disponibilidade no mês.
- Mostra os **5 melhores** do Banco Interno e mais até **3 parcialmente disponíveis** (1% a 99% livres) que tenham ficado de fora, com o selo "Parcialmente disponível". Sem isso, os parciais nunca apareciam, porque a função desempata pela maior disponibilidade.
- Se o filtro não encontrar ninguém, relaxa primeiro a senioridade e depois o cargo, e avisa na mensagem.
- O Banco de Talentos é acionado quando há menos de 3 internos com 100% das skills, com o mesmo filtro e o mesmo relaxamento de cargo.

Cada candidato traz o campo `availability` (% livre no mês) e os critérios reconhecidos vêm em `extractedCriteria.roles`.

---

## 📊 Página Utilização (aproveitamento do tempo da equipe)

Mostra quanto da capacidade da equipe está sendo usada e sugere onde encaixar quem tem horas livres. Fica no menu do frontend, logo abaixo do Assistente de IA.

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/utilizacao/indicadores?meses=6` | Ocupação média, horas ociosas, pessoas equivalentes, parciais, livres e sem planejamento, mês a mês |
| GET | `/api/utilizacao/oportunidades?ano=2026&mes=11` | Pessoas com horas livres e as demandas em que elas se encaixam |
| POST | `/api/utilizacao/alocar` | Aloca o colaborador na demanda e lança a % do mês numa única transação |

Filtros úteis em `oportunidades`: `id_demanda` (só encaixes nesta demanda), `apenas_com_sugestao=true`, `sugestoes` (quantas demandas sugerir por pessoa) e `limit`.

Exemplo de corpo do `POST /api/utilizacao/alocar`:

```json
{ "id_colaborador": 12, "id_demanda": 4, "ano": 2026, "mes": 11, "porcentagem": 60 }
```

**Como os números são calculados:**
- **Jornada:** 160 horas por mês (constante `HORAS_MES` em `app/api/utilizacao.py`; mude ali se a empresa usar outro valor).
- **Ocupação de uma pessoa no mês:** soma das porcentagens planejadas, limitada a 100%.
- **Sem planejamento:** colaborador ativo sem nenhum planejamento lançado no mês (nem com 0%). Essas pessoas **não entram** na ocupação média nem nas horas ociosas, porque não dá para saber se estão livres ou se o planejamento só não foi lançado. Elas aparecem num indicador separado, e o gráfico apaga os meses em que mais da metade da equipe está nessa situação.
- **Horas ociosas:** soma do percentual livre de quem tem planejamento, convertido em horas. **Pessoas equivalentes** = horas ociosas ÷ 160.
- **Sugestões de encaixe:** demandas ativas, vigentes no mês e fora dos andamentos `Concluída` e `Cancelada`, que exigem skills que a pessoa tem. A ordem é pela porcentagem das skills exigidas que ela cobre. Demandas em que a pessoa já está alocada não são sugeridas.
- **Alocar:** usa a mesma regra de sobrealocação do `PUT /alocacoes/{id}/planejamentos`. Se passar de 100%, a API devolve `409` e **nada é gravado**. Se a pessoa já estiver na demanda, só o planejamento do mês é atualizado.

A página **Equipes** também mostra um selo com a situação de cada pessoa no mês atual (`Livre`, `Parcial`, `Ocupado` ou `Sem planejamento`) e avisa o primeiro mês, nos próximos seis, em que ela fica sem planejamento lançado. A rota `/api/painel/equipes` devolve isso nos campos `planningStatus` e `unplannedFrom`.

---

## 🧪 Testes Automatizados

A suíte em `backend/tests/` tem **97 testes** que cobrem todas as rotas, os casos de sucesso e os de erro.

```powershell
pip install -r requirements-dev.txt
pytest
```

Resultado esperado: `97 passed`. Como os testes acessam o Supabase pela internet, levam cerca de 1 a 2 minutos.

> 🔒 **Os testes não alteram o banco de produção.** Cada teste roda dentro de uma transação desfeita (rollback) ao final, então colaboradores, demandas e alocações criados durante os testes não ficam gravados. Apenas os contadores de ID (sequences) avançam, o que é normal no PostgreSQL.

Comandos úteis:

```powershell
pytest tests/test_alocacoes.py   # roda um arquivo
pytest tests/test_utilizacao.py  # só os testes da página Utilização
pytest -k sobrealocacao          # roda testes cujo nome contém a palavra
pytest -x                        # para no primeiro erro
```

**Boa prática do time:** rode `pytest` antes de cada commit no backend.

---

## 🔄 Migrações (Alembic)

O `alembic/env.py` lê a conexão do `.env` e foi configurado com proteções:
- só compara o schema `"InHire"`, ignorando os schemas internos do Supabase (`auth`, `storage` etc.);
- **nunca gera `DROP TABLE`** para tabelas que existem no banco mas não nos models;
- ignora as views (`vw_...`).

Para verificar se os models estão sincronizados com o banco:

```powershell
alembic check
```

O esperado é `No new upgrade operations detected.`

> ⚠️ Ao alterar um model, revise sempre o arquivo gerado por `alembic revision --autogenerate` antes de rodar `alembic upgrade head`, pois o banco é de produção.

---

## 📌 Próximas Etapas

- [x] Mapear os modelos SQLAlchemy correspondentes às tabelas do script SQL em `app/models/`.
- [x] Criar Schemas Pydantic em `app/schemas/` para validação dos dados de entrada e saída.
- [x] Desenvolver as rotas RESTful para gerenciamento e alocação inteligente de tarefas.
- [x] Criar testes automatizados para todas as rotas.
- [ ] Conectar o frontend em React/Vite com a API FastAPI.
- [ ] Adicionar autenticação (ex.: Supabase Auth ou JWT) antes de expor a API publicamente.
- [ ] Corrigir os registros com domínios inconsistentes apontados pela view `vw_inconsistencias_dominios`.# bemteviproject.vint
Projeto de Automatização e Gerenciamento de skills. 
