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
  return normalizarPessoa(await request(`/colaboradores/${id}`));
}

// Detalhe do talento externo (GET /talentos/{id}).
export async function obterTalento(id) {
  return normalizarPessoa(await request(`/talentos/${id}`));
}

function normalizarPessoa(c) {
  const skills = comoLista(pegar(c, 'skills', 'colaborador_skills', 'talento_skills') || []).map((s) =>
    typeof s === 'string'
      ? { nome: s, nivel: '' }
      : {
          nome: texto(pegar(s, 'skill', 'nome', 'name', 'nome_skill')),
          nivel: texto(pegar(s, 'nivel', 'nivel_conhecimento', 'level')),
        }
  );
  return {
    id: pegar(c, 'id', 'id_colaborador', 'id_talento'),
    nome: texto(pegar(c, 'nome', 'name')),
    email: texto(pegar(c, 'email', 'e_mail')),
    telefone: texto(pegar(c, 'telefone', 'celular', 'phone')),
    linkedin: texto(pegar(c, 'linkedin', 'url_linkedin')),
    cargo: texto(pegar(c, 'cargo', 'role')),
    senioridade: texto(pegar(c, 'senioridade', 'seniority')),
    modalidade: texto(pegar(c, 'modalidade')),
    skills: skills.filter((s) => s.nome),
  };
}

// ---------------------------------------------------------------------------
// Disponibilidade mês a mês (GET /busca/disponibilidade?ano=&mes=)
// ---------------------------------------------------------------------------

// Aceita só número de verdade (ou texto numérico); ignora booleanos e textos.
function numeroDe(valor) {
  if (typeof valor === 'number' && Number.isFinite(valor)) return valor;
  if (typeof valor === 'string' && /^\s*\d+(\.\d+)?\s*$/.test(valor)) return Number(valor);
  return null;
}

// Procura um campo numérico cujo nome combine com o padrão (ex.: "percentual_disponivel").
function numeroPorNome(obj, padrao) {
  for (const [chave, valor] of Object.entries(obj || {})) {
    if (/^(id|ano|mes)/i.test(chave)) continue;
    if (padrao.test(chave)) {
      const n = numeroDe(valor);
      if (n !== null) return n;
    }
  }
  return null;
}

function percentualLivre(linha) {
  for (const chave of ['disponivel', 'disponibilidade', 'percentual_livre', 'percentual_disponivel', 'livre', 'availability']) {
    const n = numeroDe(linha?.[chave]);
    if (n !== null) return n;
  }
  const porNome = numeroPorNome(linha, /dispon|livre|free|avail/i);
  if (porNome !== null) return porNome;
  // Se a API só informar quanto está ocupado, converte para % livre
  const ocupado = numeroPorNome(linha, /ocupa|aloca|planej|usad|engaj/i);
  return ocupado !== null ? Math.max(0, 100 - ocupado) : null;
}

// Disponibilidade de todos os colaboradores num mês: Map(id → % livre).
export async function disponibilidadeDoMes(ano, mes) {
  let resposta;
  try {
    resposta = await request(comParametros('/busca/disponibilidade', { ano, mes, limit: 1000 }));
  } catch {
    resposta = await request(comParametros('/busca/disponibilidade', { ano, mes }));
  }
  const mapa = new Map();
  for (const linha of comoLista(resposta, 'colaboradores', 'disponibilidade')) {
    const id = pegar(linha, 'id_colaborador', 'colaborador_id', 'colaboradorId', 'id');
    const livre = percentualLivre(linha);
    if (id !== undefined && livre !== null) mapa.set(String(id), Math.max(0, Math.min(100, livre)));
  }
  return mapa;
}

export function proximosMeses(quantidade, base = new Date()) {
  return Array.from({ length: quantidade }, (_, i) => {
    const d = new Date(base.getFullYear(), base.getMonth() + i, 1);
    return { ano: d.getFullYear(), mes: d.getMonth() + 1 };
  });
}

// Projeção dos próximos meses para todos os colaboradores, com uma chamada por mês.
// Retorna { meses: [{ano, mes}], mapas: [Map | null] }.
export async function projecaoDisponibilidade(quantidade = 4) {
  const meses = proximosMeses(quantidade);
  const mapas = await Promise.all(meses.map((m) => disponibilidadeDoMes(m.ano, m.mes).catch(() => null)));
  return { meses, mapas };
}

// % livre de um colaborador num mês. Retorna null quando não há planejamento.
export async function disponibilidadeNoMes(idColaborador, ano, mes) {
  const mapa = await disponibilidadeDoMes(ano, mes);
  return mapa.has(String(idColaborador)) ? mapa.get(String(idColaborador)) : null;
}

export const enviarEmail = ({ para, cc = [], assunto, mensagem }) =>
  request('/api/email/enviar', { method: 'POST', body: JSON.stringify({ para, cc, assunto, mensagem }) });
