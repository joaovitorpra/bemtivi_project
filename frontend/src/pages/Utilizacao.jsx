import { useCallback, useState } from 'react';
import { AlertCircle, CheckCircle2, Clock, Gauge, Loader2, UserCheck, UserX } from 'lucide-react';
import { alocarColaborador, listarOportunidades, obterIndicadores } from '../services/api';
import { useApi } from '../hooks/useApi';
import { Avatar, EstadoDaPagina } from '../components/Comum';

const numero = (valor, casas = 0) =>
  Number(valor).toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });

const mesAtual = () => {
  const hoje = new Date();
  return { ano: hoje.getFullYear(), mes: hoje.getMonth() + 1 };
};

// Os indicadores sempre partem do mês atual (os 6 meses do gráfico não mudam)
const carregarIndicadores = () => obterIndicadores({ meses: 6 });

function Indicador({ icone: Icone, titulo, valor, detalhe, destaque = 'text-purple-300' }) {
  return (
    <div className="bg-[#110B22]/90 rounded-2xl p-5 border border-purple-500/20 space-y-2">
      <div className="flex items-center gap-2 text-xs text-slate-400">
        <Icone className={`w-4 h-4 ${destaque}`} />
        {titulo}
      </div>
      <p className="text-3xl font-bold text-white tabular-nums">{valor}</p>
      <p className="text-[11px] text-slate-400 leading-snug">{detalhe}</p>
    </div>
  );
}

// Gráfico de colunas dos próximos meses; clicar numa coluna troca o mês analisado
function GraficoOcupacao({ meses, selecionado, onSelecionar }) {
  return (
    <div className="bg-[#110B22]/90 rounded-2xl p-6 border border-purple-500/20 space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-sm font-bold text-white">Ocupação nos próximos meses</h2>
        <p className="text-[11px] text-slate-400">Clique num mês para ver as oportunidades dele</p>
      </div>
      <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${meses.length}, minmax(0, 1fr))` }}>
        {meses.map((m) => {
          const ativo = m.ano === selecionado.ano && m.mes === selecionado.mes;
          const poucoPlanejado = m.unplanned > m.plannedEmployees;
          return (
            <button
              key={m.period}
              type="button"
              onClick={() => onSelecionar({ ano: m.ano, mes: m.mes })}
              aria-pressed={ativo}
              title={`${m.period}: ${numero(m.averageOccupancy, 1)}% de ocupação, ${m.idleHours} h ociosas`}
              className={`group flex flex-col items-center gap-2 rounded-xl p-2 transition cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-400 ${
                ativo ? 'bg-purple-500/15 ring-1 ring-purple-400/50' : 'hover:bg-white/5'
              }`}
            >
              <span className="text-xs font-semibold text-white tabular-nums">{numero(m.averageOccupancy, 1)}%</span>
              <div
                className={`relative w-full max-w-[56px] h-40 rounded-lg bg-white/5 overflow-hidden ${
                  poucoPlanejado ? 'outline-1 outline-dashed outline-amber-400/60' : ''
                }`}
              >
                <div
                  className={`absolute bottom-0 inset-x-0 rounded-lg bg-gradient-to-t from-purple-600 to-cyan-400 transition-all duration-500 ${
                    poucoPlanejado ? 'opacity-30' : ativo ? '' : 'opacity-70 group-hover:opacity-90'
                  }`}
                  style={{ height: `${m.averageOccupancy}%` }}
                />
              </div>
              <span className={`text-xs font-medium ${ativo ? 'text-purple-200' : 'text-slate-300'}`}>{m.period}</span>
              <span className="text-[10px] text-amber-300/90 tabular-nums">{numero(m.idleHours)} h livres</span>
              {m.unplanned > 0 && (
                <span className={`text-[10px] tabular-nums ${poucoPlanejado ? 'text-amber-300' : 'text-slate-500'}`}>
                  {m.unplanned} sem plano
                </span>
              )}
            </button>
          );
        })}
      </div>
      {meses.some((m) => m.unplanned > m.plannedEmployees) && (
        <p className="text-[11px] text-amber-300/90 flex items-center gap-1.5">
          <span className="inline-block w-3 h-3 rounded-sm outline-1 outline-dashed outline-amber-400/60 bg-purple-500/30" />
          Barras apagadas: mais da metade da equipe ainda sem planejamento no mês, então a ocupação real pode ser bem
          diferente.
        </p>
      )}
    </div>
  );
}

function CardOportunidade({ pessoa, alocando, onAlocar }) {
  return (
    <div className="bg-[#110B22]/90 rounded-2xl p-5 border border-purple-500/20 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Avatar name={pessoa.name} src={pessoa.avatar} />
          <div className="space-y-1">
            <h3 className="font-bold text-white text-sm">{pessoa.name}</h3>
            <p className="text-xs text-slate-400">
              {pessoa.role}
              {pessoa.seniority ? ` • ${pessoa.seniority}` : ''}
            </p>
            <p className="text-xs text-slate-500">Projeto atual: {pessoa.currentProject}</p>
          </div>
        </div>
        <div className="sm:text-right space-y-1.5 sm:min-w-44">
          <p className="text-sm font-bold text-emerald-400 tabular-nums">
            {pessoa.freePercent}% livre <span className="font-medium text-slate-400">({pessoa.freeHours} h no mês)</span>
          </p>
          <div className="h-1.5 w-full bg-emerald-500/20 rounded-full overflow-hidden" title={`${pessoa.occupancy}% ocupado`}>
            <div className="h-full bg-gradient-to-r from-purple-500 to-cyan-400" style={{ width: `${pessoa.occupancy}%` }} />
          </div>
          <p className="text-[10px] text-slate-500">{pessoa.occupancy}% ocupado</p>
        </div>
      </div>

      {pessoa.suggestions.length > 0 ? (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-purple-300">Onde encaixar</p>
          {pessoa.suggestions.map((s) => {
            const chave = `${pessoa.id}-${s.demandId}`;
            return (
              <div
                key={s.demandId}
                className="bg-[#1A1133] rounded-xl px-4 py-3 border border-white/5 flex flex-col md:flex-row md:items-center justify-between gap-3"
              >
                <div className="space-y-1.5">
                  <p className="text-sm text-white">
                    <strong>{s.demandName}</strong> <span className="text-xs text-slate-400">({s.client})</span>
                  </p>
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="text-[11px] font-semibold text-purple-200 mr-1">
                      {s.matchScore}% das skills exigidas
                    </span>
                    {s.matchedSkills.map((skill) => (
                      <span key={skill} className="text-[10px] px-2 py-0.5 rounded-md bg-white/5 text-slate-300 border border-white/10">
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
                <button
                  type="button"
                  disabled={alocando !== null}
                  onClick={() => onAlocar(pessoa, s)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-white bg-[#8B3DFF] hover:bg-[#7C2AE8] transition shrink-0 cursor-pointer disabled:opacity-50 disabled:cursor-wait flex items-center gap-2 justify-center focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-300"
                >
                  {alocando === chave && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Alocar {s.suggestedPercent}%
                </button>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="text-xs text-slate-400 bg-[#1A1133] rounded-xl px-4 py-3 border border-white/5">
          Nenhuma demanda vigente pede as skills desta pessoa. Busque um encaixe no Assistente de IA ou revise as skills
          cadastradas dela.
        </p>
      )}
    </div>
  );
}

export default function Utilizacao() {
  const [selecionado, setSelecionado] = useState(mesAtual);
  const [apenasComEncaixe, setApenasComEncaixe] = useState(false);
  const [alocando, setAlocando] = useState(null);
  const [aviso, setAviso] = useState(null);

  const indicadores = useApi(carregarIndicadores);
  const carregarOportunidades = useCallback(
    () =>
      listarOportunidades({
        ano: selecionado.ano,
        mes: selecionado.mes,
        apenas_com_sugestao: apenasComEncaixe,
        limit: 50,
      }),
    [selecionado.ano, selecionado.mes, apenasComEncaixe]
  );
  const oportunidades = useApi(carregarOportunidades);

  const meses = indicadores.data?.trend || [];
  const atual = meses.find((m) => m.ano === selecionado.ano && m.mes === selecionado.mes) || indicadores.data?.current;
  const lista = oportunidades.data?.opportunities || [];

  const alocar = async (pessoa, sugestao) => {
    setAlocando(`${pessoa.id}-${sugestao.demandId}`);
    setAviso(null);
    try {
      const resposta = await alocarColaborador({
        id_colaborador: pessoa.id,
        id_demanda: sugestao.demandId,
        ano: selecionado.ano,
        mes: selecionado.mes,
        porcentagem: sugestao.suggestedPercent,
      });
      setAviso({ tipo: 'ok', texto: resposta.message });
      indicadores.reload();
      oportunidades.reload();
    } catch (err) {
      setAviso({ tipo: 'erro', texto: err.message });
    } finally {
      setAlocando(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Utilização da Equipe</h1>
        <p className="text-xs text-slate-400">
          Quanto da capacidade está sendo usada e onde encaixar quem tem horas livres
          {indicadores.data ? ` (jornada de ${indicadores.data.hoursPerMonth} h/mês)` : ''}
        </p>
      </div>

      <EstadoDaPagina loading={indicadores.loading} error={indicadores.error} onRetry={indicadores.reload} />

      {atual && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Indicador
              icone={Gauge}
              titulo={`Ocupação média em ${atual.period}`}
              valor={`${numero(atual.averageOccupancy, 1)}%`}
              detalhe={`Entre as ${atual.plannedEmployees} pessoas com planejamento lançado`}
            />
            <Indicador
              icone={Clock}
              titulo="Horas ociosas"
              valor={`${numero(atual.idleHours)} h`}
              detalhe={`O mesmo que ${numero(atual.idleFte, 1)} ${atual.idleFte === 1 ? 'pessoa parada' : 'pessoas paradas'} o mês inteiro`}
              destaque="text-amber-300"
            />
            <Indicador
              icone={UserCheck}
              titulo="Com horas livres"
              valor={atual.partial + atual.free}
              detalhe={`${atual.partial} parcialmente alocadas e ${atual.free} sem nenhuma alocação`}
              destaque="text-emerald-400"
            />
            <Indicador
              icone={UserX}
              titulo="Sem planejamento"
              valor={atual.unplanned}
              detalhe="Ficam fora da conta até o gestor lançar o planejamento do mês"
              destaque="text-slate-400"
            />
          </div>

          {atual.unplanned > atual.plannedEmployees && (
            <div className="p-4 rounded-xl bg-amber-950/50 border border-amber-500/40 text-amber-200 flex items-start gap-3 text-sm">
              <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              <span>
                Em {atual.period}, {atual.unplanned} de {indicadores.data.totalEmployees} pessoas ainda não têm
                planejamento. Os números acima consideram só quem tem, então podem mudar bastante quando os lançamentos
                forem feitos.
              </span>
            </div>
          )}

          <GraficoOcupacao meses={meses} selecionado={selecionado} onSelecionar={setSelecionado} />
        </>
      )}

      <section className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-base font-bold text-white">
            Oportunidades em {atual?.period || oportunidades.data?.period || '...'}
            {!oportunidades.loading && oportunidades.data && (
              <span className="ml-2 text-xs font-medium text-slate-400">
                {lista.length} {lista.length === 1 ? 'pessoa' : 'pessoas'}
              </span>
            )}
          </h2>
          <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={apenasComEncaixe}
              onChange={(e) => setApenasComEncaixe(e.target.checked)}
              className="accent-purple-500 w-4 h-4"
            />
            Mostrar só quem tem encaixe sugerido
          </label>
        </div>

        {aviso && (
          <div
            role="status"
            className={`p-4 rounded-xl border flex items-center gap-3 text-sm font-medium ${
              aviso.tipo === 'ok'
                ? 'bg-emerald-950/70 border-emerald-500/40 text-emerald-200'
                : 'bg-red-950/60 border-red-500/40 text-red-200'
            }`}
          >
            {aviso.tipo === 'ok' ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
            )}
            <span>{aviso.texto}</span>
          </div>
        )}

        <EstadoDaPagina loading={oportunidades.loading} error={oportunidades.error} onRetry={oportunidades.reload} />
        {!oportunidades.loading && oportunidades.data && lista.length === 0 && (
          <p className="text-sm text-slate-400 py-10 text-center">
            Ninguém com planejamento lançado tem horas livres neste mês.
          </p>
        )}

        <div className="space-y-3">
          {lista.map((pessoa) => (
            <CardOportunidade key={pessoa.id} pessoa={pessoa} alocando={alocando} onAlocar={alocar} />
          ))}
        </div>
      </section>
    </div>
  );
}
