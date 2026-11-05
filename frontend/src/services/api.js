// Comunicação com o backend FastAPI.
// O endereço vem do arquivo .env (VITE_API_URL); se não existir, usa o backend local.
const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
  } catch {
    throw new Error(
      `Não foi possível conectar à API em ${API_URL}. Verifique se o backend está rodando (uvicorn app.main:app --reload).`
    );
  }

  if (!response.ok) {
    let detail = `Erro ${response.status} ao chamar a API`;
    try {
      const body = await response.json();
      if (typeof body.detail === 'string') detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail.map((d) => d.msg).join('; ');
    } catch {
      /* resposta sem JSON */
    }
    throw new Error(detail);
  }
  return response.json();
}

function comParametros(path, params = {}) {
  const query = new URLSearchParams(
    Object.entries(params).filter(([, valor]) => valor !== undefined && valor !== null && valor !== '')
  ).toString();
  return query ? `${path}?${query}` : path;
}

export const buscarComIA = (prompt) =>
  request('/api/ia/buscar', { method: 'POST', body: JSON.stringify({ prompt }) });

export const listarProjetos = (params) => request(comParametros('/api/painel/projetos', params));
export const listarEquipes = (params) => request(comParametros('/api/painel/equipes', params));
export const listarTalentos = (params) => request(comParametros('/api/painel/talentos', params));

// Página Utilização
export const obterIndicadores = (params) => request(comParametros('/api/utilizacao/indicadores', params));
export const listarOportunidades = (params) => request(comParametros('/api/utilizacao/oportunidades', params));
export const alocarColaborador = (dados) =>
  request('/api/utilizacao/alocar', { method: 'POST', body: JSON.stringify(dados) });

// ---------------------------------------------------------------------------
// Perfil e Alocação
// ---------------------------------------------------------------------------

// Lê o primeiro campo existente entre vários nomes possíveis.
function pegar(obj, ...chaves) {
  if (!obj) return undefined;
  for (const chave of chaves) {
    if (obj[chave] !== undefined && obj[chave] !== null) return obj[chave];
  }
  return undefined;
}

// Domínios (cargo, senioridade, nível) podem vir como texto ou como objeto.
function texto(valor) {
  if (valor === undefined || valor === null) return '';
  if (typeof valor === 'object') return pegar(valor, 'nome', 'descricao', 'valor', 'name', 'label') ?? '';
  return String(valor);
}

function comoLista(resposta, ...chaves) {
  if (Array.isArray(resposta)) return resposta;
  const lista = pegar(resposta, ...chaves, 'items', 'itens', 'data', 'results', 'resultados');
  return Array.isArray(lista) ? lista : [];
}

// Detalhe do colaborador (GET /colaboradores/{id}): e-mail e skills com nível.
export async function obterColaborador(id) {
  const c = await request(`/colaboradores/${id}`);
  const skills = comoLista(pegar(c, 'skills', 'colaborador_skills') || []).map((s) =>
    typeof s === 'string'
      ? { nome: s, nivel: '' }
      : {
          nome: texto(pegar(s, 'skill', 'nome', 'name', 'nome_skill')),
          nivel: texto(pegar(s, 'nivel', 'nivel_conhecimento', 'level')),
        }
  );
  return {
    id: pegar(c, 'id', 'id_colaborador'),
    nome: texto(pegar(c, 'nome', 'name')),
    email: texto(pegar(c, 'email', 'e_mail')),
    cargo: texto(pegar(c, 'cargo', 'role')),
    senioridade: texto(pegar(c, 'senioridade', 'seniority')),
    modalidade: texto(pegar(c, 'modalidade')),
    skills: skills.filter((s) => s.nome),
  };
}

// % livre de um colaborador num mês (GET /busca/disponibilidade).
// Retorna null quando o colaborador não aparece (sem planejamento).
export async function disponibilidadeNoMes(idColaborador, ano, mes) {
  const r = await request(comParametros('/busca/disponibilidade', { ano, mes, limit: 1000 }));
  const linha = comoLista(r, 'colaboradores', 'disponibilidade').find(
    (l) => String(pegar(l, 'id_colaborador', 'id', 'colaboradorId')) === String(idColaborador)
  );
  if (!linha) return null;
  const valor = Number(pegar(linha, 'disponivel', 'disponibilidade', 'percentual_livre', 'livre', 'availability'));
  return Number.isFinite(valor) ? valor : null;
}

export const enviarEmail = ({ para, cc = [], assunto, mensagem }) =>
  request('/api/email/enviar', { method: 'POST', body: JSON.stringify({ para, cc, assunto, mensagem }) });
