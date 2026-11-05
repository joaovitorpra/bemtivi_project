import { useEffect, useState } from 'react';

// Carrega dados da API quando `ativo` for true (ex.: ao abrir a página).
// Retorna { data, loading, error, reload }.
export function useApi(buscar, ativo = true) {
  const [resultado, setResultado] = useState({ versao: null, data: null, error: null });
  const [versao, setVersao] = useState(0);

  useEffect(() => {
    if (!ativo) return undefined;
    let cancelado = false;
    buscar()
      .then((data) => !cancelado && setResultado({ versao, data, error: null }))
      .catch((err) => !cancelado && setResultado({ versao, data: null, error: err.message }));
    return () => {
      cancelado = true;
    };
  }, [buscar, ativo, versao]);

  const loading = ativo && resultado.versao !== versao;
  return {
    data: resultado.data,
    loading,
    error: loading ? null : resultado.error,
    reload: () => setVersao((v) => v + 1),
  };
}
