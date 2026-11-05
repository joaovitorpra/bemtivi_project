import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Users,
  Briefcase,
  Building2,
  X,
  Send,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Gauge,
  UserRound
} from 'lucide-react';
import { buscarComIA, listarProjetos, listarEquipes, listarTalentos, projecaoDisponibilidade } from './services/api';
import { useApi } from './hooks/useApi';
import { Avatar, EstadoDaPagina } from './components/Comum';
import Utilizacao from './pages/Utilizacao';
import Perfil from './pages/Perfil';
import Alocar from './pages/Alocar';
import Contatar from './pages/Contatar';
import ProximosMeses from './components/ProximosMeses';

const TITULOS_PAGINA = {
  ia: 'Assistente de IA',
  utilizacao: 'Utilização',
  projetos: 'Projetos',
  equipes: 'Equipes',
  talentos: 'Talentos',
  perfil: 'Perfil do profissional',
  alocar: 'Alocar profissional',
  contatar: 'Contatar talento'
};

// Selo da situação do planejamento de cada colaborador no mês atual
const SELOS_PLANEJAMENTO = {
  livre: { texto: 'Livre', classe: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' },
  parcial: { texto: 'Parcial', classe: 'bg-amber-500/15 text-amber-300 border-amber-500/30' },
  ocupado: { texto: 'Ocupado', classe: 'bg-rose-500/15 text-rose-300 border-rose-500/30' },
  sem_planejamento: { texto: 'Sem planejamento', classe: 'bg-slate-500/15 text-slate-300 border-slate-500/30' }
};

// LOGO OFICIAL TALENTFLOW (Ícone em degradê X + texto)
function TalentFlowLogo({ showText = false }) {
  return (
    <div className="flex items-center gap-3 select-none">
      <svg
        width="34"
        height="34"
        viewBox="0 0 40 40"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0 drop-shadow-[0_0_12px_rgba(168,85,247,0.45)]"
      >
        <defs>
          <linearGradient id="tf_grad_cyan_purple" x1="6" y1="34" x2="34" y2="6" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#06B6D4" />
            <stop offset="45%" stopColor="#7C3AED" />
            <stop offset="100%" stopColor="#C084FC" />
          </linearGradient>
          <linearGradient id="tf_grad_purple" x1="6" y1="6" x2="34" y2="34" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#9333EA" />
            <stop offset="100%" stopColor="#A855F7" />
          </linearGradient>
        </defs>
        <path d="M9 31L31 9" stroke="url(#tf_grad_cyan_purple)" strokeWidth="8.5" strokeLinecap="round" />
        <path d="M9 9L31 31" stroke="url(#tf_grad_purple)" strokeWidth="8.5" strokeLinecap="round" opacity="0.92" />
      </svg>
      {showText && (
        <span className="text-2xl tracking-tight leading-none flex items-center">
          <strong className="font-extrabold text-white">talent</strong>
          <span className="font-medium bg-gradient-to-r from-purple-400 to-fuchsia-400 bg-clip-text text-transparent">
            flow
          </span>
        </span>
      )}
    </div>
  );
}

// Funções de carga (fora do componente para não recriar a cada render)
const carregarProjetos = () => listarProjetos();
const carregarEquipes = () => listarEquipes({ limit: 60 });
const carregarTalentos = () => listarTalentos({ limit: 60 });

const MESES_CURTOS = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

// SUGESTÕES RÁPIDAS
const QUICK_SUGGESTIONS = [
  'Dev Python sênior disponível agora com foco em backend e banco de dados',
  'Especialista Java para microsserviços em nuvem',
  'Front-end React e Tailwind com disponibilidade imediata',
  'Product Designer para estruturação de Design System no Figma'
];

export default function App() {
  const [currentPage, setCurrentPage] = useState('ia'); // 'ia' | 'utilizacao' | 'projetos' | 'equipes' | 'talentos'
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [mousePos, setMousePos] = useState({ x: 600, y: 380 });

  // Estados de Busca com IA
  const [searchQuery, setSearchQuery] = useState('');
  const [hasSearched, setHasSearched] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [actionFeedback, setActionFeedback] = useState(null); // { tipo: 'ok' | 'aviso', texto }
  const [searchError, setSearchError] = useState(null);

  // Perfil e alocação: guarda o candidato escolhido na busca
  const [pessoaSelecionada, setPessoaSelecionada] = useState(null);
  const [paginaDeOrigem, setPaginaDeOrigem] = useState('ia'); // para onde o "Voltar" leva
  const [resumoMes, setResumoMes] = useState([]);
  const [projecao, setProjecao] = useState(null); // disponibilidade dos próximos meses (todos os colaboradores)

  // Dados das páginas (carregados da API ao abrir cada página)
  const projetos = useApi(carregarProjetos, currentPage === 'projetos');
  const equipes = useApi(carregarEquipes, currentPage === 'equipes');
  const talentos = useApi(carregarTalentos, currentPage === 'talentos');

  // Sombra fluida acompanhando o mouse
  useEffect(() => {
    const handleMouseMove = (e) => setMousePos({ x: e.clientX, y: e.clientY });
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  // Resumo do mês: usa as mesmas rotas das páginas Equipes, Projetos e Talentos.
  // Cada número que falhar ao carregar simplesmente não aparece.
  useEffect(() => {
    const hoje = new Date();
    const mesAtual = `${MESES_CURTOS[hoje.getMonth()]}/${hoje.getFullYear()}`;
    const contarLista = (r) => (Array.isArray(r) ? r : []);
    // Tenta trazer todos; se a API recusar um limite alto, usa o padrão.
    const carregarTodos = (fn) => fn({ limit: 1000 }).catch(() => fn({}));

    Promise.allSettled([carregarTodos(listarEquipes), listarProjetos(), carregarTodos(listarTalentos)]).then(
      ([equipesR, projetosR, talentosR]) => {
        const cards = [];
        if (equipesR.status === 'fulfilled') {
          const equipe = contarLista(equipesR.value);
          cards.push({ rotulo: `Livres em ${mesAtual}`, valor: equipe.filter((e) => e.planningStatus === 'livre').length, cor: 'text-emerald-300' });
          cards.push({ rotulo: 'Parcialmente disponíveis', valor: equipe.filter((e) => e.planningStatus === 'parcial').length, cor: 'text-amber-300' });
        }
        if (projetosR.status === 'fulfilled') {
          const abertos = contarLista(projetosR.value).filter((p) => !/conclu|cancel/i.test(p.status || ''));
          cards.push({ rotulo: 'Demandas abertas', valor: abertos.length, cor: 'text-white' });
        }
        if (talentosR.status === 'fulfilled') {
          cards.push({ rotulo: 'Talentos externos', valor: contarLista(talentosR.value).length, cor: 'text-white' });
        }
        setResumoMes(cards);
      }
    );
  }, []);

  // Critérios que a IA entendeu, mostrados ao lado do título dos resultados
  const criterios = analysisResult?.extractedCriteria;
  const criteriosTexto = [
    criterios?.skills?.join(', '),
    criterios?.roles?.join(', '),
    criterios?.seniority,
    criterios?.urgency,
    criterios?.period
  ].filter(Boolean).join(' · ');

  // Projeção dos próximos 4 meses (mês atual + 3). Carregada na primeira busca
  // e recarregada depois de cada alocação.
  const carregarProjecao = () => {
    projecaoDisponibilidade(4)
      .then((p) => setProjecao(p.mapas.some((m) => m && m.size > 0) ? p : { indisponivel: true }))
      .catch(() => setProjecao({ indisponivel: true }));
  };

  // % livre de um candidato no mês atual (talento sem número = 100%, pois está no mercado)
  const livreAgora = (person) => {
    if (typeof person.availability === 'number') return person.availability;
    return person.source === 'INTERNO' ? null : 100;
  };

  // Linha do tempo de um colaborador interno: [{ano, mes, livre}] ou null se não houver dados
  const mesesDoCandidato = (person) => {
    if (person.source !== 'INTERNO' || !projecao?.meses) return null;
    return projecao.meses.map((m, i) => {
      if (i === 0 && typeof person.availability === 'number') return { ...m, livre: person.availability };
      const mapa = projecao.mapas[i];
      return { ...m, livre: mapa && mapa.has(String(person.id)) ? mapa.get(String(person.id)) : null };
    });
  };

  // Resumo calculado só com os profissionais encontrados pela IA (os dois bancos)
  const resumoDaBusca = (() => {
    const candidatos = analysisResult?.candidates;
    if (!hasSearched || isLoading || !candidatos?.length) return null;
    const internos = candidatos.filter((c) => c.source === 'INTERNO');
    const talentos = candidatos.filter((c) => c.source !== 'INTERNO');
    const ehParcial = (v) => v !== null && v > 0 && v < 100;

    const livres = candidatos.filter((c) => livreAgora(c) >= 100);
    const parciais = candidatos.filter((c) => ehParcial(livreAgora(c)));
    const mediaLivreParciais = parciais.length
      ? Math.round(parciais.reduce((soma, c) => soma + livreAgora(c), 0) / parciais.length)
      : null;

    const linhas = internos.map(mesesDoCandidato).filter(Boolean);
    let mediaParciaisFuturo = null;
    let liberamEmBreve = null;
    if (linhas.length) {
      const talentosParciais = talentos.filter((c) => ehParcial(livreAgora(c))).length;
      const futuros = [1, 2, 3].filter((i) => i < linhas[0].length);
      const porMes = futuros.map((i) => linhas.filter((l) => ehParcial(l[i].livre)).length + talentosParciais);
      mediaParciaisFuturo = porMes.length ? porMes.reduce((a, b) => a + b, 0) / porMes.length : null;
      liberamEmBreve = linhas.filter((l) => (l[0].livre ?? 0) < 100 && l.slice(1).some((m) => m.livre !== null && m.livre >= 100)).length;
    }

    const fmt = (n) => n.toLocaleString('pt-BR', { maximumFractionDigits: 1 });
    return [
      {
        rotulo: 'Livres agora',
        valor: livres.length,
        detalhe: `${livres.filter((c) => c.source === 'INTERNO').length} internos · ${livres.filter((c) => c.source !== 'INTERNO').length} talentos`,
        cor: 'text-emerald-300'
      },
      {
        rotulo: 'Parcialmente disponíveis',
        valor: parciais.length,
        detalhe: [
          mediaLivreParciais !== null ? `${mediaLivreParciais}% livre em média` : null,
          mediaParciaisFuturo !== null ? `média de ${fmt(mediaParciaisFuturo)}/mês nos próximos 3 meses` : null
        ].filter(Boolean).join(' · ') || 'nos dois bancos',
        cor: 'text-amber-300'
      },
      liberamEmBreve !== null && {
        rotulo: 'Ficam livres em breve',
        valor: liberamEmBreve,
        detalhe: 'internos que chegam a 100% livre nos próximos 3 meses',
        cor: 'text-cyan-300'
      },
      {
        rotulo: 'Banco de Talentos',
        valor: talentos.length,
        detalhe: talentos.length ? 'externos compatíveis com a busca' : 'não foi preciso acionar',
        cor: 'text-white'
      }
    ].filter(Boolean);
  })();

  const cardsResumo = resumoDaBusca || resumoMes;

  // Execução da Busca Inteligente
  const executeSearch = async (queryText) => {
    const query = queryText || searchQuery;
    if (!query.trim()) return;

    setIsLoading(true);
    setHasSearched(true);
    setSearchError(null);

    try {
      // Chamada para a API Python (backend FastAPI)
      const data = await buscarComIA(query);
      setAnalysisResult(data);
      if (!projecao) carregarProjecao();
    } catch (err) {
      setAnalysisResult(null);
      setSearchError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const mostrarFeedback = (feedback) => {
    setActionFeedback(feedback);
    setTimeout(() => setActionFeedback(null), 6000);
  };


  const navigateTo = (page) => {
    setCurrentPage(page);
    setIsSidebarOpen(false);
    window.scrollTo({ top: 0 });
  };

  const lembrarOrigem = () => {
    if (['ia', 'talentos', 'equipes'].includes(currentPage)) setPaginaDeOrigem(currentPage);
  };

  const voltar = () => navigateTo(paginaDeOrigem);

  const abrirPerfil = (person) => {
    lembrarOrigem();
    setPessoaSelecionada(person);
    navigateTo('perfil');
  };

  const abrirAlocacao = (person) => {
    lembrarOrigem();
    setPessoaSelecionada(person);
    navigateTo('alocar');
  };

  const abrirContato = (person) => {
    lembrarOrigem();
    setPessoaSelecionada(person);
    navigateTo('contatar');
  };

  // Depois de enviar o convite a um talento, volta aos resultados com o aviso
  const concluirContato = (feedback) => {
    navigateTo(paginaDeOrigem);
    mostrarFeedback(feedback);
  };

  // Ao terminar a alocação, volta para os resultados da busca com o aviso
  const concluirAlocacao = (feedback) => {
    navigateTo(paginaDeOrigem);
    mostrarFeedback(feedback);
    if (paginaDeOrigem === 'ia' && searchQuery.trim()) executeSearch(searchQuery); // atualiza a disponibilidade nos cards
    carregarProjecao();
  };

  return (
    <div className="min-h-screen bg-[#070412] text-slate-100 flex flex-col font-sans relative overflow-x-hidden selection:bg-purple-600 selection:text-white">
      {/* Sombra Esfumaçada Dinâmica */}
      <div
        className="pointer-events-none fixed inset-0 z-0 transition-opacity duration-300"
        style={{
          background: `radial-gradient(550px circle at ${mousePos.x}px ${mousePos.y}px, rgba(139, 92, 246, 0.22), rgba(6, 182, 212, 0.08) 45%, transparent 80%)`
        }}
      />

      {/* Overlay do Menu Suspenso */}
      {isSidebarOpen && (
        <div onClick={() => setIsSidebarOpen(false)} className="fixed inset-0 bg-black/60 backdrop-blur-xs z-40" />
      )}

      {/* MENU LATERAL SUSPENSO COM OS 4 ITENS */}
      <aside
        className={`fixed top-3 left-3 bottom-3 w-72 bg-[#0E0821]/95 backdrop-blur-xl text-white rounded-2xl shadow-[0_0_50px_rgba(124,58,237,0.25)] border border-purple-500/20 flex flex-col justify-between z-50 select-none transition-transform duration-300 ease-in-out ${
          isSidebarOpen ? 'translate-x-0' : '-translate-x-[115%]'
        }`}
      >
        <div>
          <div className="px-6 py-6 flex items-center justify-between border-b border-white/10">
            <TalentFlowLogo showText={true} />
            <button onClick={() => setIsSidebarOpen(false)} className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition cursor-pointer">
              <X className="w-5 h-5" />
            </button>
          </div>

          <nav className="px-3 space-y-2 mt-6">
            <button
              onClick={() => navigateTo('ia')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-medium text-sm transition cursor-pointer ${
                currentPage === 'ia'
                  ? 'bg-gradient-to-r from-purple-900/60 to-indigo-900/40 text-purple-200 border border-purple-500/30'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <Sparkles className="w-4 h-4 text-purple-400" />
              Assistente de IA
            </button>

            <button
              onClick={() => navigateTo('utilizacao')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-medium text-sm transition cursor-pointer ${
                currentPage === 'utilizacao'
                  ? 'bg-gradient-to-r from-purple-900/60 to-indigo-900/40 text-purple-200 border border-purple-500/30'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <Gauge className="w-4 h-4 text-purple-400" />
              Utilização
            </button>

            <button
              onClick={() => navigateTo('projetos')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-medium text-sm transition cursor-pointer ${
                currentPage === 'projetos'
                  ? 'bg-gradient-to-r from-purple-900/60 to-indigo-900/40 text-purple-200 border border-purple-500/30'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <Briefcase className="w-4 h-4 text-purple-400" />
              Projetos
            </button>

            <button
              onClick={() => navigateTo('equipes')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-medium text-sm transition cursor-pointer ${
                currentPage === 'equipes'
                  ? 'bg-gradient-to-r from-purple-900/60 to-indigo-900/40 text-purple-200 border border-purple-500/30'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <Building2 className="w-4 h-4 text-purple-400" />
              Equipes
            </button>

            <button
              onClick={() => navigateTo('talentos')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-medium text-sm transition cursor-pointer ${
                currentPage === 'talentos'
                  ? 'bg-gradient-to-r from-purple-900/60 to-indigo-900/40 text-purple-200 border border-purple-500/30'
                  : 'text-slate-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <Users className="w-4 h-4 text-purple-400" />
              Talentos
            </button>
          </nav>
        </div>

        <div className="p-4 border-t border-white/10">
          <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-white/5 border border-white/5">
            <div className="w-8 h-8 rounded-full bg-purple-600/40 border border-purple-400/40 flex items-center justify-center text-xs font-bold text-purple-200">
              VG
            </div>
            <div className="text-xs leading-tight">
              <p className="font-semibold text-white">Vint Global</p>
              <p className="text-slate-400">People & Tech Ops</p>
            </div>
          </div>
        </div>
      </aside>

      {/* TOPBAR */}
      <header className="h-16 bg-[#070412]/70 backdrop-blur-md border-b border-white/5 px-6 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setIsSidebarOpen(true)}
            className="p-2 rounded-xl bg-[#120A2A] hover:bg-[#1C103F] border border-purple-500/25 transition cursor-pointer"
            title="Abrir menu TalentFlow"
          >
            <TalentFlowLogo showText={false} />
          </button>
          <div className="flex items-center gap-2 text-xs font-medium text-purple-300/80">
            <span>vint global • TalentFlow</span>
            <span className="text-slate-600">/</span>
            <span className="text-slate-300">{TITULOS_PAGINA[currentPage]}</span>
          </div>
        </div>

        {currentPage === 'ia' && hasSearched && (
          <button
            onClick={() => { setHasSearched(false); setSearchQuery(''); setAnalysisResult(null); setSearchError(null); }}
            className="text-xs font-medium text-purple-300 bg-purple-950/60 hover:bg-purple-900/70 border border-purple-500/30 px-3 py-1.5 rounded-lg transition cursor-pointer"
          >
            Nova Pesquisa
          </button>
        )}
      </header>

      {/* Aviso flutuante (quando a ação termina fora da página do Assistente) */}
      {actionFeedback && currentPage !== 'ia' && (
        <div
          role="status"
          className={`fixed bottom-6 right-6 left-6 sm:left-auto sm:max-w-md z-50 p-4 rounded-xl flex items-center gap-3 text-sm font-medium border shadow-2xl ${
            actionFeedback.tipo === 'aviso'
              ? 'bg-amber-950/95 border-amber-500/40 text-amber-200'
              : 'bg-emerald-950/95 border-emerald-500/40 text-emerald-200'
          }`}
        >
          {actionFeedback.tipo === 'aviso'
            ? <AlertCircle className="w-5 h-5 text-amber-400 shrink-0" />
            : <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />}
          <span>{actionFeedback.texto}</span>
        </div>
      )}

      {/* ÁREA PRINCIPAL */}
      <main className="flex-1 w-full max-w-6xl mx-auto px-6 relative z-10 py-10 md:py-14 space-y-10">
        {/* PÁGINA 1: ASSISTENTE DE IA (modelo A — busca em destaque) */}
        {currentPage === 'ia' && (
          <>
            <section className="flex flex-col items-center text-center gap-5">
              <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-purple-300">
                <Sparkles className="w-3.5 h-3.5" />
                Assistente de alocação
              </span>
              <h1 className="text-3xl md:text-5xl font-semibold tracking-tight text-white max-w-3xl leading-tight">
                Quem você precisa para o próximo projeto?
              </h1>
              <p className="text-sm md:text-base text-slate-400 max-w-2xl leading-relaxed">
                Descreva o perfil com suas palavras. A IA cruza skills, senioridade e disponibilidade no Banco Interno e no Banco de Talentos.
              </p>

              <form
                role="search"
                onSubmit={(e) => { e.preventDefault(); executeSearch(); }}
                className="w-full max-w-3xl flex flex-col sm:flex-row gap-2 p-2 bg-[#15101F] border border-[#3A2D57] rounded-2xl focus-within:border-purple-400/70 transition"
              >
                <label htmlFor="busca-ia" className="sr-only">Descreva o profissional</label>
                <input
                  id="busca-ia"
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Ex.: Dev Python sênior disponível agora, foco em backend e banco de dados"
                  className="flex-1 min-w-0 bg-transparent text-base text-white placeholder-slate-500 focus:outline-none px-3.5 py-3"
                />
                <button
                  type="submit"
                  disabled={isLoading}
                  className="min-h-12 px-6 rounded-xl bg-[#8B5CF6] hover:bg-[#7C4DEE] text-white text-[15px] font-semibold inline-flex items-center justify-center gap-2 transition cursor-pointer disabled:opacity-60"
                >
                  {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                  {isLoading ? 'Buscando…' : 'Buscar'}
                </button>
              </form>

              <div className="flex flex-wrap justify-center gap-2 max-w-3xl">
                {QUICK_SUGGESTIONS.map((text) => (
                  <button
                    key={text}
                    type="button"
                    onClick={() => { setSearchQuery(text); executeSearch(text); }}
                    className="min-h-11 px-4 rounded-full border border-[#2E2445] bg-[#120D1C] hover:border-[#3A2D57] hover:text-white text-sm text-[#D9D2E6] transition cursor-pointer"
                  >
                    {text}
                  </button>
                ))}
              </div>
            </section>

            {/* RESUMO: geral antes da busca, da busca depois de pesquisar */}
            {cardsResumo.length > 0 && (
              <section aria-label={resumoDaBusca ? 'Resumo desta busca' : 'Resumo do mês'} className="space-y-3">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h2 className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
                    {resumoDaBusca ? 'Resumo desta busca' : 'Resumo geral do mês'}
                  </h2>
                  {resumoDaBusca && projecao?.indisponivel && (
                    <span className="text-[11px] text-slate-500">Projeção dos próximos meses indisponível</span>
                  )}
                </div>
                <div className={`grid grid-cols-2 gap-4 ${cardsResumo.length === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-4'}`}>
                  {cardsResumo.map((k) => (
                    <div key={k.rotulo} className="p-5 bg-[#15101F] border border-[#241C36] rounded-2xl flex flex-col gap-1.5">
                      <span className="text-[13px] text-slate-400">{k.rotulo}</span>
                      <span className={`text-3xl font-semibold ${k.cor}`}>{k.valor}</span>
                      {k.detalhe && <span className="text-[11px] text-slate-500 leading-snug">{k.detalhe}</span>}
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Aviso depois de alocar */}
            {actionFeedback && (
              <div
                role="status"
                className={`p-4 rounded-xl flex items-center gap-3 text-sm font-medium border ${
                  actionFeedback.tipo === 'aviso'
                    ? 'bg-amber-950/60 border-amber-500/40 text-amber-200'
                    : 'bg-emerald-950/70 border-emerald-500/40 text-emerald-200'
                }`}
              >
                {actionFeedback.tipo === 'aviso'
                  ? <AlertCircle className="w-5 h-5 text-amber-400 shrink-0" />
                  : <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />}
                <span>{actionFeedback.texto}</span>
              </div>
            )}

            {/* RESULTADOS DA BUSCA INTELIGENTE */}
            {hasSearched && (
              <div className="space-y-5">
                {searchError && (
                  <div className="p-4 rounded-xl bg-red-950/60 border border-red-500/40 text-red-200 flex items-center gap-3 text-sm">
                    <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
                    <span>{searchError}</span>
                  </div>
                )}

                {analysisResult?.message && (
                  <div className="p-4 rounded-xl bg-amber-950/50 border border-amber-500/40 text-amber-200 flex items-center gap-3 text-sm">
                    <AlertCircle className="w-5 h-5 text-amber-400 shrink-0" />
                    <span>{analysisResult.message}</span>
                  </div>
                )}

                {isLoading && (
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4" aria-busy="true">
                    {[0, 1, 2].map((i) => (
                      <div key={i} className="h-56 rounded-2xl bg-[#15101F] border border-[#241C36] animate-pulse" />
                    ))}
                  </div>
                )}

                <div className={`space-y-4 ${isLoading ? 'hidden' : ''}`}>
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <h2 className="text-xl font-semibold text-white">
                      {(analysisResult?.candidates?.length || 0) === 1
                        ? '1 profissional compatível'
                        : `${analysisResult?.candidates?.length || 0} profissionais compatíveis`}
                    </h2>
                    {criteriosTexto && <span className="text-sm text-slate-400">{criteriosTexto}</span>}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    {analysisResult?.candidates?.map((person) => {
                      const isInternal = person.source === 'INTERNO';
                      const livre = typeof person.availability === 'number' ? person.availability : null;
                      return (
                        <article
                          key={`${person.source}-${person.id}`}
                          className="bg-[#110B22]/90 rounded-2xl p-5 border border-purple-500/20 hover:border-purple-400/40 transition flex flex-col gap-4"
                        >
                          <div className="flex items-center gap-3">
                            <Avatar name={person.name} src={person.avatar} className="border border-purple-500/30" />
                            <div className="flex-1 min-w-0">
                              <h3 className="font-bold text-white text-sm truncate">{person.name}</h3>
                              <p className="text-xs text-slate-400 truncate">{person.role}</p>
                            </div>
                            <span className="text-lg font-extrabold text-purple-300" title="Compatibilidade com o pedido">
                              {person.matchScore}%
                            </span>
                          </div>

                          <div className="flex flex-wrap gap-1.5">
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide ${isInternal ? 'bg-purple-500/20 text-purple-300' : 'bg-cyan-500/20 text-cyan-300'}`}>
                              {isInternal ? 'Banco Interno' : 'Banco de Talentos'}
                            </span>
                            {isInternal && livre !== null && (
                              <span
                                className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                                  livre >= 100
                                    ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                                    : 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                                }`}
                              >
                                {livre}% livre
                              </span>
                            )}
                            {person.skills.map((skill) => (
                              <span key={skill} className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-white/5 text-slate-300 border border-white/10">
                                ✓ {skill}
                              </span>
                            ))}
                          </div>

                          <div className="text-xs space-y-1 bg-[#1A1133] px-3 py-2 rounded-lg border border-white/5">
                            <p className="text-slate-400">Projeto atual: <strong className="text-white">{person.currentProject}</strong></p>
                            <p className="text-slate-400">Disponibilidade: <strong className="text-emerald-400">{person.freeDate}</strong></p>
                          </div>

                          {isInternal && mesesDoCandidato(person) && <ProximosMeses meses={mesesDoCandidato(person)} />}

                          {person.reason && (
                            <p className="text-xs text-slate-400 leading-relaxed">
                              <strong className="text-purple-300">Análise da IA:</strong> {person.reason}
                            </p>
                          )}

                          <div className="flex gap-2 mt-auto">
                            {isInternal ? (
                              <>
                                <button
                                  onClick={() => abrirPerfil(person)}
                                  className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-200 border border-purple-500/30 hover:bg-white/5 transition cursor-pointer"
                                >
                                  <UserRound className="w-3.5 h-3.5" />
                                  Ver perfil
                                </button>
                                <button
                                  onClick={() => abrirAlocacao(person)}
                                  className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-white bg-[#8B3DFF] hover:bg-[#7C2AE8] transition cursor-pointer"
                                >
                                  <Send className="w-3.5 h-3.5" />
                                  Alocar
                                </button>
                              </>
                            ) : (
                              <>
                                <button
                                  onClick={() => abrirPerfil(person)}
                                  className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-slate-200 border border-cyan-500/30 hover:bg-white/5 transition cursor-pointer"
                                >
                                  <UserRound className="w-3.5 h-3.5" />
                                  Ver perfil
                                </button>
                                <button
                                  onClick={() => abrirContato(person)}
                                  className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 transition cursor-pointer"
                                >
                                  <Send className="w-3.5 h-3.5" />
                                  Contatar
                                </button>
                              </>
                            )}
                          </div>
                        </article>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {/* PÁGINA: UTILIZAÇÃO (indicadores, evolução e oportunidades de encaixe) */}
        {currentPage === 'utilizacao' && <Utilizacao />}

        {/* PÁGINA: PERFIL DO PROFISSIONAL */}
        {currentPage === 'perfil' && pessoaSelecionada && (
          <Perfil
            pessoa={pessoaSelecionada}
            onVoltar={voltar}
            onAlocar={abrirAlocacao}
            onContatar={abrirContato}
          />
        )}

        {/* PÁGINA: ALOCAR COM E-MAIL */}
        {currentPage === 'alocar' && pessoaSelecionada && (
          <Alocar pessoa={pessoaSelecionada} onVoltar={voltar} onConcluido={concluirAlocacao} />
        )}

        {/* PÁGINA: CONTATAR TALENTO EXTERNO (e-mail de convite) */}
        {currentPage === 'contatar' && pessoaSelecionada && (
          <Contatar pessoa={pessoaSelecionada} onVoltar={voltar} onConcluido={concluirContato} />
        )}

        {/* PÁGINA 2: PROJETOS */}
        {currentPage === 'projetos' && (
          <div className="space-y-6">
            <div>
              <h1 className="text-2xl font-bold text-white">Projetos em Andamento</h1>
              <p className="text-xs text-slate-400">Visão consolidada de todas as iniciativas cadastradas</p>
            </div>
            <EstadoDaPagina loading={projetos.loading} error={projetos.error} vazio={projetos.data?.length === 0} onRetry={projetos.reload} />
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {(projetos.data || []).map((p) => (
                <div key={p.id} className="bg-[#110B22]/90 rounded-2xl p-6 border border-purple-500/20 space-y-4">
                  <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    {p.status}
                  </span>
                  <div>
                    <h3 className="text-base font-bold text-white">{p.name}</h3>
                    <p className="text-xs text-slate-400">{p.client} • Entrega: {p.deadline}</p>
                    <p className="text-xs text-slate-500">Equipe: {p.teamSize} {p.teamSize === 1 ? 'pessoa' : 'pessoas'} • Prazo decorrido: {p.progress}%</p>
                  </div>
                  <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-purple-500 to-cyan-400" style={{ width: `${p.progress}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* PÁGINA 3: EQUIPES */}
        {currentPage === 'equipes' && (
          <div className="space-y-6">
            <div>
              <h1 className="text-2xl font-bold text-white">Equipes & Funcionários Internos</h1>
              <p className="text-xs text-slate-400">Todos os colaboradores da empresa e sua disponibilidade atual</p>
            </div>
            <EstadoDaPagina loading={equipes.loading} error={equipes.error} vazio={equipes.data?.length === 0} onRetry={equipes.reload} />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {(equipes.data || []).map((emp) => (
                <div key={emp.id} className="bg-[#110B22]/90 rounded-2xl p-5 border border-purple-500/20 space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-4">
                      <Avatar name={emp.name} src={emp.avatar} />
                      <div>
                        <h3 className="font-bold text-white text-sm">{emp.name}</h3>
                        <p className="text-xs text-slate-400">{emp.role}{emp.seniority ? ` • ${emp.seniority}` : ''}</p>
                      </div>
                    </div>
                    {SELOS_PLANEJAMENTO[emp.planningStatus] && (
                      <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full border shrink-0 ${SELOS_PLANEJAMENTO[emp.planningStatus].classe}`}>
                        {SELOS_PLANEJAMENTO[emp.planningStatus].texto}
                      </span>
                    )}
                  </div>
                  <div className="bg-[#1A1133] p-3 rounded-xl text-xs space-y-1">
                    <div className="flex justify-between"><span className="text-slate-400">Projeto atual:</span><span className="text-white">{emp.currentProject}</span></div>
                    {emp.planningStatus === 'sem_planejamento' ? (
                      <>
                        <div className="flex justify-between"><span className="text-slate-400">Engajamento:</span><span className="text-slate-400">Não lançado</span></div>
                        <div className="flex justify-between"><span className="text-slate-400">Liberação:</span><span className="text-slate-400">Aguardando planejamento</span></div>
                      </>
                    ) : (
                      <>
                        <div className="flex justify-between"><span className="text-slate-400">Engajamento:</span><span className={emp.engagement === 0 ? 'text-emerald-400' : 'text-amber-400'}>{emp.engagement}%</span></div>
                        <div className="flex justify-between"><span className="text-slate-400">Liberação:</span><span className="text-emerald-400 font-semibold">{emp.freeDate}</span></div>
                      </>
                    )}
                  </div>
                  {emp.unplannedFrom && emp.planningStatus !== 'sem_planejamento' && (
                    <p className="text-[11px] text-amber-300/90 flex items-center gap-1.5">
                      <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                      Sem planejamento a partir de {emp.unplannedFrom}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* PÁGINA 4: TALENTOS */}
        {currentPage === 'talentos' && (
          <div className="space-y-6">
            <div>
              <h1 className="text-2xl font-bold text-white">Banco de Talentos Externo</h1>
              <p className="text-xs text-slate-400">Profissionais aprovados no banco de dados para contratação</p>
            </div>
            <EstadoDaPagina loading={talentos.loading} error={talentos.error} vazio={talentos.data?.length === 0} onRetry={talentos.reload} />
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {(talentos.data || []).map((t) => (
                <div key={t.id} className="bg-[#110B22]/90 rounded-2xl p-5 border border-purple-500/20 space-y-4 flex flex-col justify-between">
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <Avatar name={t.name} src={t.avatar} />
                      <div>
                        <h3 className="font-bold text-white text-sm">{t.name}</h3>
                        <p className="text-xs text-slate-400">{t.role}{t.seniority ? ` • ${t.seniority}` : ''}</p>
                      </div>
                    </div>
                    <p className="text-xs text-slate-400">Disponibilidade: <strong className="text-emerald-400">{t.freeDate}</strong></p>
                    <div className="flex flex-wrap gap-1">
                      {t.skills.map((s) => (
                        <span key={s} className="text-[10px] bg-white/5 border border-white/10 px-2 py-0.5 rounded text-slate-300">{s}</span>
                      ))}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => abrirPerfil({ ...t, source: 'TALENTO' })}
                      className="flex-1 border border-cyan-500/30 hover:bg-white/5 text-slate-200 py-2 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition cursor-pointer"
                    >
                      <UserRound className="w-3.5 h-3.5" />
                      Ver perfil
                    </button>
                    <button
                      onClick={() => abrirContato({ ...t, source: 'TALENTO' })}
                      className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white py-2 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition cursor-pointer"
                    >
                      <Send className="w-3.5 h-3.5" />
                      Contatar
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
