import { useEffect, useState } from 'react';
import { ArrowLeft, Mail, Briefcase, CalendarClock, Loader2, Send, Phone, Link2 } from 'lucide-react';
import { obterColaborador, obterTalento, disponibilidadeNoMes } from '../services/api';
import { Avatar } from '../components/Comum';

const MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

function proximosMeses(qtd) {
  const hoje = new Date();
  return Array.from({ length: qtd }, (_, i) => {
    const d = new Date(hoje.getFullYear(), hoje.getMonth() + i, 1);
    return { ano: d.getFullYear(), mes: d.getMonth() + 1 };
  });
}

function nivel(n) {
  const v = (n || '').toUpperCase();
  if (v.startsWith('AVAN')) return { rotulo: 'Avançado', largura: '100%' };
  if (v.startsWith('INTER')) return { rotulo: 'Intermediário', largura: '66%' };
  if (v.startsWith('BAS') || v.startsWith('BÁS')) return { rotulo: 'Básico', largura: '33%' };
  return { rotulo: n || '', largura: '50%' };
}

function corLivre(livre) {
  if (livre >= 100) return { barra: 'bg-emerald-400', texto: 'text-emerald-300' };
  if (livre > 0) return { barra: 'bg-amber-400', texto: 'text-amber-300' };
  return { barra: 'bg-rose-400', texto: 'text-rose-300' };
}

/**
 * Perfil de um profissional: colaborador interno ou talento externo.
 * `pessoa` é o candidato que veio da busca com IA (name, role, source, availability, skills...).
 * O resto (e-mail, nível das skills, próximos meses) é carregado da API.
 */
export default function Perfil({ pessoa, onVoltar, onAlocar, onContatar }) {
  const externo = pessoa.source !== 'INTERNO';
  const [detalhe, setDetalhe] = useState(null);
  const [meses, setMeses] = useState(null);

  useEffect(() => {
    let ativo = true;
    setDetalhe(null);
    setMeses(null);
    (externo ? obterTalento : obterColaborador)(pessoa.id)
      .then((d) => ativo && setDetalhe(d))
      .catch(() => ativo && setDetalhe({ erro: true }));
    // Disponibilidade mês a mês só existe para quem é da equipe interna
    if (externo) {
      setMeses([]);
      return () => {
        ativo = false;
      };
    }
    const lista = proximosMeses(6);
    Promise.all(lista.map((m) => disponibilidadeNoMes(pessoa.id, m.ano, m.mes).catch(() => null))).then(
      (valores) => ativo && setMeses(lista.map((m, i) => ({ ...m, livre: valores[i] })))
    );
    return () => {
      ativo = false;
    };
  }, [pessoa.id, externo]);

  const skills = detalhe?.skills?.length
    ? detalhe.skills
    : (pessoa.skills || []).map((s) => ({ nome: s, nivel: '' }));
  const temMeses = meses?.some((m) => m.livre !== null);

  return (
    <div className="space-y-6">
      <button
        onClick={onVoltar}
        className="inline-flex items-center gap-2 text-xs font-medium text-slate-400 hover:text-white transition cursor-pointer"
      >
        <ArrowLeft className="w-4 h-4" />
        Voltar aos resultados
      </button>

      {/* Cabeçalho */}
      <section className="bg-[#110B22]/90 rounded-2xl p-6 border border-purple-500/20 flex flex-col md:flex-row md:items-center gap-5">
        <Avatar name={pessoa.name} src={pessoa.avatar} className="w-20 h-20 text-xl border border-purple-500/30" />
        <div className="flex-1 space-y-2 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold text-white">{pessoa.name}</h1>
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide ${
                externo ? 'bg-cyan-500/20 text-cyan-300' : 'bg-purple-500/20 text-purple-300'
              }`}
            >
              {externo ? 'Banco de Talentos' : 'Banco Interno'}
            </span>
          </div>
          <p className="text-sm text-slate-400">
            {[pessoa.role || detalhe?.cargo, detalhe?.senioridade, detalhe?.modalidade].filter(Boolean).join(' • ')}
          </p>
          <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-400">
            {detalhe?.email && (
              <a href={`mailto:${detalhe.email}`} className="inline-flex items-center gap-1.5 text-purple-300 hover:text-purple-200">
                <Mail className="w-3.5 h-3.5" />
                {detalhe.email}
              </a>
            )}
            {detalhe?.telefone && (
              <span className="inline-flex items-center gap-1.5">
                <Phone className="w-3.5 h-3.5" />
                {detalhe.telefone}
              </span>
            )}
            {/^https?:\/\//.test(detalhe?.linkedin || '') && (
              <a href={detalhe.linkedin} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-purple-300 hover:text-purple-200">
                <Link2 className="w-3.5 h-3.5" />
                LinkedIn
              </a>
            )}
            {!externo && pessoa.currentProject && (
              <span className="inline-flex items-center gap-1.5">
                <Briefcase className="w-3.5 h-3.5" />
                Projeto atual: <strong className="text-white">{pessoa.currentProject}</strong>
              </span>
            )}
            {pessoa.freeDate && (
              <span className="inline-flex items-center gap-1.5">
                <CalendarClock className="w-3.5 h-3.5" />
                Disponibilidade: <strong className="text-emerald-400">{pessoa.freeDate}</strong>
              </span>
            )}
          </div>
        </div>
        <button
          onClick={() => (externo ? onContatar(pessoa) : onAlocar(pessoa))}
          className={`text-white px-5 py-3 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition cursor-pointer shrink-0 ${
            externo ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-[#8B3DFF] hover:bg-[#7C2AE8]'
          }`}
        >
          <Send className="w-4 h-4" />
          {externo ? 'Contatar para contratar' : 'Alocar em projeto'}
        </button>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Disponibilidade */}
        <section className="lg:col-span-2 bg-[#110B22]/90 rounded-2xl p-6 border border-purple-500/20 space-y-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="text-sm font-bold text-white">
              {externo ? 'Disponibilidade' : 'Disponibilidade — próximos 6 meses'}
            </h2>
            {!externo && <span className="text-[11px] text-slate-400">% livre no mês</span>}
          </div>

          {externo && (
            <div className="space-y-3 text-sm text-slate-300">
              <p>
                Disponível para começar: <strong className="text-emerald-400">{pessoa.freeDate || 'não informado'}</strong>
              </p>
              {typeof pessoa.availability === 'number' && (
                <p>Dedicação informada: <strong className="text-white">{pessoa.availability}%</strong></p>
              )}
              {pessoa.reason && (
                <p className="text-xs text-slate-400 leading-relaxed">
                  <strong className="text-purple-300">Análise da IA:</strong> {pessoa.reason}
                </p>
              )}
            </div>
          )}

          {meses === null && (
            <div className="flex items-center gap-2 text-xs text-slate-400 py-10 justify-center">
              <Loader2 className="w-4 h-4 animate-spin" /> Carregando…
            </div>
          )}

          {!externo && meses !== null && !temMeses && (
            <p className="text-xs text-slate-400 py-6">
              Sem planejamento lançado para os próximos meses.
              {typeof pessoa.availability === 'number' && (
                <> Neste mês: <strong className="text-white">{pessoa.availability}% livre</strong>.</>
              )}
            </p>
          )}

          {temMeses && (
            <>
              <div className="grid grid-cols-6 gap-3 items-end h-44">
                {meses.map((m) => {
                  const cor = m.livre === null ? null : corLivre(m.livre);
                  return (
                    <div key={`${m.ano}-${m.mes}`} className="flex flex-col items-center justify-end gap-2 h-full">
                      <span className={`text-xs font-semibold ${cor ? cor.texto : 'text-slate-500'}`}>
                        {m.livre === null ? '—' : `${Math.round(m.livre)}%`}
                      </span>
                      {m.livre === null ? (
                        <div className="w-full max-w-12 h-28 rounded-t-md border border-dashed border-purple-400/30" />
                      ) : (
                        <div
                          className={`w-full max-w-12 rounded-t-md ${cor.barra}`}
                          style={{ height: `${Math.max(4, Math.min(100, m.livre)) * 1.12}px` }}
                        />
                      )}
                      <span className="text-[11px] text-slate-400">{MESES[m.mes - 1]}</span>
                    </div>
                  );
                })}
              </div>
              <p className="text-[11px] text-slate-500">Tracejado = sem planejamento lançado.</p>
            </>
          )}
        </section>

        {/* Skills */}
        <section className="bg-[#110B22]/90 rounded-2xl p-6 border border-purple-500/20 space-y-4">
          <h2 className="text-sm font-bold text-white">Skills</h2>
          {skills.length === 0 && <p className="text-xs text-slate-400">Nenhuma skill cadastrada.</p>}
          {skills.map((s) => {
            const n = nivel(s.nivel);
            return (
              <div key={s.nome} className="space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="font-medium text-white">{s.nome}</span>
                  {n.rotulo && <span className="text-purple-300">{n.rotulo}</span>}
                </div>
                {s.nivel && (
                  <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-purple-500 to-cyan-400" style={{ width: n.largura }} />
                  </div>
                )}
              </div>
            );
          })}
        </section>
      </div>
    </div>
  );
}
