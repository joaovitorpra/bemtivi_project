# Novas telas: Início, Perfil e Alocar com e-mail

## 1. Copiar os arquivos

Copie as pastas `frontend` e `backend` deste zip para dentro de `bemteviproject.vint-main`,
mesclando com as que já existem. Nenhum arquivo existente é substituído; todos são novos:

- frontend/src/services/talentflowApi.js
- frontend/src/styles/talentflow.css
- frontend/src/components/CandidatoCard.jsx
- frontend/src/pages/Home.jsx, Perfil.jsx, Alocar.jsx
- backend/app/api/email.py
- backend/tests/test_email.py

## 2. Registrar a rota de e-mail no backend

Em `backend/app/api/router.py`, onde os outros routers são incluídos, adicione:

```python
from app.api import email
...
<nome_do_router_principal>.include_router(email.router)
```

## 3. Configurar o e-mail no `backend/.env`

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu_email@gmail.com
SMTP_PASSWORD=senha_de_app
```

No Gmail, gere a senha de app em Conta Google → Segurança → Senhas de app.

## 4. Rotas no React

Se o projeto ainda não usa react-router-dom: `npm install react-router-dom`.

No arquivo de rotas (normalmente `src/App.jsx`):

```jsx
import Home from './pages/Home';
import Perfil from './pages/Perfil';
import Alocar from './pages/Alocar';

<Route path="/" element={<Home />} />
<Route path="/colaboradores/:id" element={<Perfil />} />
<Route path="/colaboradores/:id/alocar" element={<Alocar />} />
```

## 5. Testar

```bash
cd backend
venv/bin/python -m pytest tests/test_email.py -v   # 5 testes, não enviam e-mail de verdade
```

Se algum dado aparecer vazio nas telas, o nome do campo na sua API é diferente:
ajuste só as funções `normalizar...` em `talentflowApi.js`.
