import { AlertCircle, Loader2, RefreshCw } from 'lucide-react';

// AVATAR: usa a foto se existir; senão, mostra as iniciais do nome
export function Avatar({ name, src, className = '' }) {
  if (src) {
    return <img src={src} alt={name} className={`w-12 h-12 rounded-full object-cover shrink-0 ${className}`} />;
  }
  const iniciais = (name || '?')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((parte) => parte[0].toUpperCase())
    .join('');
  return (
    <div
      className={`w-12 h-12 rounded-full shrink-0 flex items-center justify-center text-sm font-bold text-white bg-gradient-to-br from-purple-600 to-cyan-600 ${className}`}
      title={name}
    >
      {iniciais}
    </div>
  );
}

// CARREGANDO / ERRO / VAZIO para as páginas que buscam dados na API
export function EstadoDaPagina({ loading, error, vazio, onRetry }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center gap-3 py-16 text-sm text-purple-200">
        <Loader2 className="w-5 h-5 animate-spin" /> Carregando dados do banco...
      </div>
    );
  }
  if (error) {
    return (
      <div className="p-4 rounded-xl bg-red-950/60 border border-red-500/40 text-red-200 flex items-center justify-between gap-3 text-sm">
        <span className="flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
          {error}
        </span>
        <button
          onClick={onRetry}
          className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 transition cursor-pointer shrink-0"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Tentar novamente
        </button>
      </div>
    );
  }
  if (vazio) {
    return <p className="text-sm text-slate-400 py-10 text-center">Nenhum registro encontrado.</p>;
  }
  return null;
}
