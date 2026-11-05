import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Loader2, Send, AlertCircle, CheckCircle2, RotateCcw } from 'lucide-react';
import { listarProjetos, obterColaborador, alocarColaborador, enviarEmail } from '../services/api';
import { Avatar } from '../components/Comum';

const MESES_CURTOS = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
const MESES_LONGOS = [
  'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
  'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
];

// Quem assina o e-mail. Defina VITE_ASSINATURA_EMAIL no .env do frontend para trocar.
const ASSINATURA = import.meta.env.VITE_ASSINATURA_EMAIL || 'Equipe Vint Global';

const campo =
  'w-full bg-[#0B0619] border border-purple-500/25 rounded-xl px-3 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-400';
const rotulo = 'block text-xs font-semibold text-slate-300 mb-1.5';

function proximosMeses(qtd) {
  const hoje = new Date();
  return Array.from({ length: qtd }, (_, i) => {
    const d = new Date(hoje.getFullYear(), hoje.getMonth() + i, 1);
    return { ano: d.getFullYear(), mes: d.getMonth() + 1 };
  });
}

function montarEmail({ nome, projeto, ano, mes, porcentagem }) {
  const primeiroNome = (nome || '').split(' ')[0];
  const nomeProjeto = projeto?.name || '[projeto]';
  return {
    assunto: `Você foi alocado(a) em ${nomeProjeto}`,
    mensagem: [
      `Olá, ${primeiroNome}!`,
      '',
      `Você foi alocado(a) no projeto ${nomeProjeto}${projeto?.client ? ` (${projeto.client})` : ''} com dedicação de ${porcentagem}% em ${MESES_LONGOS[mes - 1]} de ${ano}.`,
      '',
      'Qualquer dúvida, é só responder este e-mail.',
      '',
      'Abraços,',
      ASSINATURA,
    ].join('\n'),
  };
}

/**
 * Alocação de um colaborador interno com e-mail de aviso.
 * `pessoa` é o candidato que veio da busca com IA.
 */
export default function Alocar({ pessoa, onVoltar, onConcluido }) {
  const meses = useMemo(() => proximosMeses(12), []);
  const livreAgora = typeof pessoa.availability === 'number' ? pessoa.availability : null;

  const [projetos, setProjetos] = useState(null);
  const [erroProjetos, setErroProjetos] = useState('');

  const [idProjeto, setIdProjeto] = useState('');
  const [periodo, setPeriodo] = useState(`${meses[0].ano}-${meses[0].mes}`);
  const [porcentagem, setPorcentagem] = useState(livreAgora !== null && livreAgora < 100 ? livreAgora : 100);

  const [comEmail, setComEmail] = useState(true);
  const [para, setPara] = useState('');
  const [cc, setCc] = useState('');
  const [assunto, setAssunto] = useState('');
  const [mensagem, setMensagem] = useState('');
  const [editado, setEditado] = useState(false);

  const [envio, setEnvio] = useState({ status: 'parado' });

  const [ano, mes] = periodo.split('-').map(Number);
  const projeto = projetos?.find((p) => String(p.id) === String(idProjeto));
  const ehMesAtual = periodo === `${meses[0].ano}-${meses[0].mes}`;

  useEffect(() => {
    listarProjetos()
      .then((lista) => setProjetos(Array.isArray(lista) ? lista : []))
      .catch((e) => setErroProjetos(e.message));
    obterColaborador(pessoa.id)
      .then((d) => d.email && setPara((atual) => atual || d.email))
      .catch(() => {});
  }, [pessoa.id]);

  // Texto automático do e-mail, até a pessoa editar à mão.
  useEffect(() => {
    if (editado) return;
    const e = montarEmail({ nome: pessoa.name, projeto, ano, mes, porcentagem });
    setAssunto(e.assunto);
    setMensagem(e.mensagem);
  }, [pessoa.name, projeto, ano, mes, porcentagem, editado]);

  const pct = Number(porcentagem);
  const pctValida = Number.isFinite(pct) && pct > 0 && pct <= 100;
  const excede = ehMesAtual && livreAgora !== null && pct > livreAgora;
  const podeConfirmar = projeto && pctValida && !excede && (!comEmail || para.trim()) && envio.status !== 'enviando';

  async function confirmar(e) {
    e.preventDefault();
    if (!podeConfirmar) return;
    setEnvio({ status: 'enviando' });

    try {
      await alocarColaborador({ id_colaborador: Number(pessoa.id), id_demanda: Number(projeto.id), ano, mes, porcentagem: pct });
    } catch (err) {
      setEnvio({ status: 'erro', mensagem: `A alocação não foi feita: ${err.message}` });
      return;
    }

    const resumo = `${pessoa.name} foi alocado(a) em ${projeto.name} (${pct}% em ${MESES_CURTOS[mes - 1]}/${ano})`;
    if (!comEmail) {
      onConcluido({ tipo: 'ok', texto: `${resumo}.` });
      return;
    }
    try {
      const copias = cc.split(/[,;\s]+/).map((x) => x.trim()).filter(Boolean);
      await enviarEmail({ para: para.trim(), cc: copias, assunto, mensagem });
      onConcluido({ tipo: 'ok', texto: `${resumo} e o e-mail foi enviado para ${para.trim()}.` });
    } catch (err) {
      onConcluido({ tipo: 'aviso', texto: `${resumo}, mas o e-mail não foi enviado: ${err.message}` });
    }
  }

  return (
    <div className="space-y-6">
      <button
        onClick={onVoltar}
        className="inline-flex items-center gap-2 text-xs font-medium text-slate-400 hover:text-white transition cursor-pointer"
      >
        <ArrowLeft className="w-4 h-4" />
        Voltar
      </button>

      <div className="flex items-center gap-4">
        <Avatar name={pessoa.name} src={pessoa.avatar} className="border border-purple-500/30" />
        <div>
          <h1 className="text-2xl font-bold text-white">Alocar {pessoa.name}</h1>
          <p className="text-xs text-slate-400">
            Escolha o projeto e a dedicação. O e-mail é preenchido sozinho e você pode editar antes de enviar.
          </p>
        </div>
      </div>

      <form onSubmit={confirmar} className="space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* 1. Alocação */}
          <section className="lg:col-span-2 bg-[#110B22]/90 rounded-2xl p-6 border border-purple-500/20 space-y-5">
            <h2 className="text-sm font-bold text-white">1. Alocação</h2>

            <div>
              <label htmlFor="aloc-projeto" className={rotulo}>Projeto</label>
              {erroProjetos ? (
                <p className="text-xs text-red-300">Não foi possível carregar os projetos: {erroProjetos}</p>
              ) : (
                <select id="aloc-projeto" className={campo} value={idProjeto} onChange={(e) => setIdProjeto(e.target.value)} required>
                  <option value="">{projetos === null ? 'Carregando…' : 'Selecione um projeto'}</option>
                  {(projetos || []).map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}{p.client ? ` — ${p.client}` : ''}
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="aloc-mes" className={rotulo}>Mês</label>
                <select id="aloc-mes" className={campo} value={periodo} onChange={(e) => setPeriodo(e.target.value)}>
                  {meses.map((m) => (
                    <option key={`${m.ano}-${m.mes}`} value={`${m.ano}-${m.mes}`}>
                      {MESES_CURTOS[m.mes - 1]}/{m.ano}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="aloc-pct" className={rotulo}>Dedicação (%)</label>
                <input
                  id="aloc-pct"
                  type="number"
                  min="1"
                  max="100"
                  className={campo}
                  value={porcentagem}
                  onChange={(e) => setPorcentagem(e.target.value)}
                  required
                />
              </div>
            </div>

            {ehMesAtual && livreAgora !== null && !excede && (
              <div className="p-3 rounded-xl bg-emerald-950/60 border border-emerald-500/30 text-emerald-200 text-xs leading-relaxed">
                Livre neste mês: <strong>{livreAgora}%</strong>.
                {pctValida && <> Depois desta alocação ficam <strong>{Math.round(livreAgora - pct)}%</strong>.</>}
              </div>
            )}
            {excede && (
              <div className="p-3 rounded-xl bg-red-950/60 border border-red-500/40 text-red-200 text-xs flex gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                Só há {livreAgora}% livres neste mês. Reduza a dedicação ou escolha outro mês.
              </div>
            )}
            {!ehMesAtual && (
              <p className="text-[11px] text-slate-400">
                A API confere o limite de 100% do mês ao confirmar e avisa se passar.
              </p>
            )}

            <label className="flex items-center gap-3 text-sm text-slate-200 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={comEmail}
                onChange={(e) => setComEmail(e.target.checked)}
                className="w-4 h-4 accent-purple-500"
              />
              Enviar e-mail avisando o colaborador
            </label>
          </section>

          {/* 2. E-mail */}
          {comEmail && (
            <section className="lg:col-span-3 bg-[#110B22]/90 rounded-2xl p-6 border border-purple-500/20 space-y-4">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-sm font-bold text-white">2. E-mail</h2>
                {editado && (
                  <button
                    type="button"
                    onClick={() => setEditado(false)}
                    className="inline-flex items-center gap-1.5 text-[11px] text-purple-300 hover:text-purple-200 cursor-pointer"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    Restaurar texto automático
                  </button>
                )}
              </div>

              <div>
                <label htmlFor="aloc-para" className={rotulo}>Para</label>
                <input id="aloc-para" type="email" className={campo} value={para} onChange={(e) => setPara(e.target.value)} placeholder="email@empresa.com" required />
              </div>
              <div>
                <label htmlFor="aloc-cc" className={rotulo}>Cópia (opcional, separe por vírgula)</label>
                <input id="aloc-cc" type="text" className={campo} value={cc} onChange={(e) => setCc(e.target.value)} placeholder="gestor@empresa.com" />
              </div>
              <div>
                <label htmlFor="aloc-assunto" className={rotulo}>Assunto</label>
                <input
                  id="aloc-assunto"
                  type="text"
                  className={campo}
                  value={assunto}
                  onChange={(e) => { setAssunto(e.target.value); setEditado(true); }}
                />
              </div>
              <div>
                <label htmlFor="aloc-msg" className={rotulo}>Mensagem</label>
                <textarea
                  id="aloc-msg"
                  rows={9}
                  className={`${campo} leading-relaxed resize-y`}
                  value={mensagem}
                  onChange={(e) => { setMensagem(e.target.value); setEditado(true); }}
                />
              </div>
            </section>
          )}
        </div>

        {envio.status === 'erro' && (
          <div className="p-4 rounded-xl bg-red-950/60 border border-red-500/40 text-red-200 flex items-center gap-3 text-sm">
            <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
            <span>{envio.mensagem}</span>
          </div>
        )}

        <div className="flex flex-wrap justify-end gap-3">
          <button
            type="button"
            onClick={onVoltar}
            className="px-5 py-2.5 rounded-xl text-sm font-medium text-slate-200 border border-purple-500/30 hover:bg-white/5 transition cursor-pointer"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={!podeConfirmar}
            className="bg-[#8B3DFF] hover:bg-[#7C2AE8] text-white px-5 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2 transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {envio.status === 'enviando' ? <Loader2 className="w-4 h-4 animate-spin" /> : comEmail ? <Send className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
            {envio.status === 'enviando' ? 'Enviando…' : comEmail ? 'Alocar e enviar e-mail' : 'Alocar'}
          </button>
        </div>
      </form>
    </div>
  );
}
