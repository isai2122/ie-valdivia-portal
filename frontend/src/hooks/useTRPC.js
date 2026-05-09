/**
 * Hook useTRPC — Wrapper de React para procedimientos tRPC
 * Maneja loading, error, data y refetch automático.
 */
import { useState, useEffect, useCallback, useRef } from "react";

/**
 * useQuery — Hook para procedimientos de consulta (GET)
 * @param {Function} queryFn - Función del cliente tRPC (e.g., () => trpc.stats.overview())
 * @param {Array} deps - Dependencias para re-ejecutar la query
 * @param {Object} options - { enabled, refetchInterval, onSuccess, onError }
 */
export function useQuery(queryFn, deps = [], options = {}) {
  const {
    enabled = true,
    refetchInterval = null,
    onSuccess = null,
    onError = null,
    initialData = null,
  } = options;

  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);
  const mountedRef = useRef(true);

  const execute = useCallback(async () => {
    if (!enabled) return;
    setLoading(true);
    setError(null);
    try {
      const result = await queryFn();
      if (mountedRef.current) {
        setData(result);
        setLoading(false);
        onSuccess?.(result);
      }
    } catch (err) {
      if (mountedRef.current) {
        const msg = err?.response?.data?.detail || err?.message || "Error desconocido";
        setError(msg);
        setLoading(false);
        onError?.(err);
      }
    }
  }, [enabled, ...deps]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    mountedRef.current = true;
    execute();

    if (refetchInterval) {
      intervalRef.current = setInterval(execute, refetchInterval);
    }

    return () => {
      mountedRef.current = false;
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [execute, refetchInterval]);

  return { data, loading, error, refetch: execute };
}

/**
 * useMutation — Hook para procedimientos de mutación (POST)
 * @param {Function} mutationFn - Función del cliente tRPC (e.g., (body) => trpc.pipeline.run(body))
 * @param {Object} options - { onSuccess, onError }
 */
export function useMutation(mutationFn, options = {}) {
  const { onSuccess = null, onError = null } = options;

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const mutate = useCallback(async (variables = {}) => {
    setLoading(true);
    setError(null);
    try {
      const result = await mutationFn(variables);
      setData(result);
      setLoading(false);
      onSuccess?.(result);
      return result;
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || "Error desconocido";
      setError(msg);
      setLoading(false);
      onError?.(err);
      throw err;
    }
  }, [mutationFn]); // eslint-disable-line react-hooks/exhaustive-deps

  return { mutate, loading, error, data };
}
