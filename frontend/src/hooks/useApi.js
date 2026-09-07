import { useCallback, useEffect, useRef, useState } from 'react';
import { parseApiError } from '../api/client.js';

/**
 * Run an async API call and track { data, loading, error, slow }.
 * `slow` flips on after 4 s so the UI can explain a free-tier cold start.
 * `deps` re-runs the call; `reload()` re-runs it manually.
 */
export default function useApi(fn, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null, slow: false });
  const requestId = useRef(0);

  const run = useCallback(() => {
    const id = ++requestId.current;
    setState((s) => ({ ...s, loading: true, error: null, slow: false }));
    const slowTimer = setTimeout(() => {
      if (requestId.current === id) setState((s) => ({ ...s, slow: true }));
    }, 4000);

    fn()
      .then((data) => {
        if (requestId.current === id) setState({ data, loading: false, error: null, slow: false });
      })
      .catch((err) => {
        if (requestId.current === id) setState({ data: null, loading: false, error: parseApiError(err), slow: false });
      })
      .finally(() => clearTimeout(slowTimer));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    run();
  }, [run]);

  return { ...state, reload: run };
}
