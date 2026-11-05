const MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

function estilo(livre) {
  if (livre === null) return { barra: 'bg-transparent border border-dashed border-slate-600', texto: 'text-slate-500' };
  if (livre >= 100) return { barra: 'bg-emerald-400', texto: 'text-emerald-300' };
  if (livre > 0) return { barra: 'bg-amber-400', texto: 'text-amber-300' };
  return { barra: 'bg-rose-400/80', texto: 'text-rose-300' };
}

/**
 * Faixa compacta com a % livre de um colaborador nos próximos meses.
 * `meses`: [{ ano, mes, livre }] — livre = número (0–100) ou null (sem planejamento).
 */
export default function ProximosMeses({ meses }) {
  if (!meses?.length) return null;
  const descricao = meses
    .map((m) => `${MESES[m.mes - 1]}: ${m.livre === null ? 'sem planejamento' : `${Math.round(m.livre)}% livre`}`)
    .join(', ');

  return (
    <div className="space-y-1.5" role="group" aria-label={`Próximos meses — ${descricao}`}>
      <p className="text-[11px] font-semibold text-slate-400">Próximos meses</p>
      <div className="grid gap-1.5" style={{ gridTemplateColumns: `repeat(${meses.length}, minmax(0, 1fr))` }}>
        {meses.map((m) => {
          const e = estilo(m.livre);
          return (
            <div key={`${m.ano}-${m.mes}`} className="flex flex-col gap-1" aria-hidden="true">
              <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
                <div className={`h-full rounded-full ${e.barra}`} style={{ width: m.livre === null ? '100%' : `${Math.max(6, m.livre)}%` }} />
              </div>
              <div className="flex justify-between text-[10px] leading-none">
                <span className="text-slate-500">{MESES[m.mes - 1]}</span>
                <span className={`font-semibold ${e.texto}`}>{m.livre === null ? '—' : `${Math.round(m.livre)}%`}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
