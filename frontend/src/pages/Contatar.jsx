import { useEffect, useState } from 'react';
import { ArrowLeft, Loader2, Send, AlertCircle, RotateCcw } from 'lucide-react';
import { listarProjetos, obterTalento, enviarEmail } from '../services/api';
import { Avatar } from '../components/Comum';

// Quem assina o e-mail. Defina VITE_ASSINATURA_EMAIL no .env do frontend para trocar.
const ASSINATURA = import.meta.env.VITE_ASSINATURA_EMAIL || 'Equipe Vint Global';

const campo =
  'w-full bg-[#0B0619] border border-purple-500/25 rounded-xl px-3 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-400';
const rotulo = 'block text-xs font-semibold text-slate-300 mb-1.5';

function montarEmail({ nome, cargo, projeto }) {
  const primeiroNome = (nome || '').split(' ')[0];
  const sobreProjeto = projeto
    ? `Estamos montando a equipe do projeto ${projeto.name}${projeto.client ? `, para ${projeto.client}` : ''}, e o seu perfil chamou nossa atenção.`
    : 'Temos uma oportunidade em aberto e o seu perfil chamou nossa atenção.';
  return {
    assunto: projeto ? `Oportunidade: ${projeto.name}` : `Oportunidade${cargo ? ` para ${cargo}` : ''} na Vint Global`,
    mensagem: [
      `Olá, ${primeiroNome}!`,
      '',
      sobreProjeto,
      '',
      'Você teria disponibilidade para uma conversa rápida nos próximos dias para falarmos sobre a vaga, escopo e condições?',
      'É só responder este e-mail com os melhores horários.',
      '',
      'Abraços,',
      ASSINATURA,
    ].join('\n'),
  };
}

/**
 * Contato com um talento externo do Banco de Talentos.
 * Não faz alocação (a pessoa ainda não é da equipe): só envia o e-mail de convite.
 */
export default function Contatar({ pessoa, onVoltar, onConcluido }) {
  const [projetos, setProjetos] = useState(null);
  const [idProjeto, setIdProjeto] = useState('');

  const [para, setPara] = useState('');
  const [cc, setCc] = useState('');
  const [assunto, setAssunto] = useState('');
  const [mensagem, setMensagem] = useState('');
  const [editado, setEditado] = useState(false);
  const [envio, setEnvio] = useState({ status: 'parado' });

  const projeto = projetos?.find((p) => String(p.id) === String(idProjeto));

  useEffect(() => {
    listarProjetos()
      .then((lista) => setProjetos(Array.isArray(lista) ? lista : []))
      .catch(() => setProjetos([]));
    obterTalento(pessoa.id)
      .then((d) => d.email && setPara((atual) => atual || d.email))
      .catch(() => {});
  }, [pessoa.id]);

  // Texto automático do e-mail, até a pessoa editar à mão.
  useEffect(() => {
    if (editado) return;
    const e = montarEmail({ nome: pessoa.name, cargo: pessoa.role, projeto });
    setAssunto(e.assunto);
    setMensagem(e.mensagem);
  }, [pessoa.name, pessoa.role, projeto, editado]);

  const podeEnviar = para.trim() && assunto.trim() && mensagem.trim() && envio.status !== 'enviando';

  async function enviar(e) {
    e.preventDefault();
    if (!podeEnviar) return;
    setEnvio({ status: 'enviando' });
    try {
      const copias = cc.split(/[,;\s]+/).map((x) => x.trim()).filter(Boolean);
      await enviarEmail({ para: para.trim(), cc: copias, assunto, mensagem });
      onConcluido({ tipo: 'ok', texto: `Convite enviado para ${pessoa.name} (${para.trim()}).` });
    } catch (err) {
      setEnvio({ status: 'erro', mensagem: `O e-mail não foi enviado: ${err.message}` });
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
        <Avatar name={pessoa.name} src={pessoa.avatar} className="border border-cyan-500/30" />
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold text-white">Contatar {pessoa.name}</h1>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide bg-cyan-500/20 text-cyan-300">
              Banco de Talentos
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Envie um convite para uma conversa. O texto é preenchido sozinho e você pode editar antes de enviar.
          </p>
        </div>
      </div>

      <form onSubmit={enviar} className="space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <section className="lg:col-span-2 bg-[#110B22]/90 rounded-2xl p-6 border border-purple-500/20 space-y-5">
            <h2 className="text-sm font-bold text-white">1. Oportunidade</h2>
            <div>
              <label htmlFor="cont-projeto" className={rotulo}>Projeto (opcional)</label>
              <select id="cont-projeto" className={campo} value={idProjeto} onChange={(e) => setIdProjeto(e.target.value)}>
                <option value="">{projetos === null ? 'Carregando…' : 'Sem projeto específico'}</option>
                {(projetos || []).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}{p.client ? ` — ${p.client}` : ''}
                  </option>
                ))}
              </select>
            </div>
            <div className="text-xs text-slate-400 space-y-1.5 bg-[#1A1133] px-3 py-2.5 rounded-lg border border-white/5">
              {pessoa.role && <p>Cargo: <strong className="text-white">{pessoa.role}</strong></p>}
              {pessoa.freeDate && <p>Disponibilidade: <strong className="text-emerald-400">{pessoa.freeDate}</strong></p>}
              {pessoa.skills?.length > 0 && <p>Skills: <span className="text-slate-300">{pessoa.skills.join(', ')}</span></p>}
            </div>
          </section>

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
              <label htmlFor="cont-para" className={rotulo}>Para</label>
              <input id="cont-para" type="email" className={campo} value={para} onChange={(e) => setPara(e.target.value)} placeholder="email@exemplo.com" required />
            </div>
            <div>
              <label htmlFor="cont-cc" className={rotulo}>Cópia (opcional, separe por vírgula)</label>
              <input id="cont-cc" type="text" className={campo} value={cc} onChange={(e) => setCc(e.target.value)} placeholder="recrutamento@empresa.com" />
            </div>
            <div>
              <label htmlFor="cont-assunto" className={rotulo}>Assunto</label>
              <input
                id="cont-assunto"
                type="text"
                className={campo}
                value={assunto}
                onChange={(e) => { setAssunto(e.target.value); setEditado(true); }}
              />
            </div>
            <div>
              <label htmlFor="cont-msg" className={rotulo}>Mensagem</label>
              <textarea
                id="cont-msg"
                rows={10}
                className={`${campo} leading-relaxed resize-y`}
                value={mensagem}
                onChange={(e) => { setMensagem(e.target.value); setEditado(true); }}
              />
            </div>
          </section>
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
            disabled={!podeEnviar}
            className="bg-emerald-600 hover:bg-emerald-500 text-white px-5 py-2.5 rounded-xl text-sm font-semibold flex items-center gap-2 transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {envio.status === 'enviando' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            {envio.status === 'enviando' ? 'Enviando…' : 'Enviar convite'}
          </button>
        </div>
      </form>
    </div>
  );
}
