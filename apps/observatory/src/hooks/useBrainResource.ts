"use client";

import { useCallback, useEffect, useState } from "react";

export type ResourceState<T> =
  | { status: "loading"; data: null; error: null }
  | { status: "ready"; data: T; error: null }
  | { status: "error"; data: null; error: string };

/**
 * Load one Brain resource and report exactly what happened.
 *
 * Deliberately has no fallback data. A cockpit that substitutes invented
 * records when a fetch fails teaches its operator to trust rows that were never
 * in the Brain — the one thing this console must never do.
 */
export function useBrainResource<T>(load: () => Promise<T>): ResourceState<T> & {
  reload: () => void;
} {
  const [state, setState] = useState<ResourceState<T>>({
    status: "loading",
    data: null,
    error: null,
  });
  const [nonce, setNonce] = useState(0);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading", data: null, error: null });

    load()
      .then((data) => {
        if (!cancelled) setState({ status: "ready", data, error: null });
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        const error = e instanceof Error ? e.message : String(e);
        setState({ status: "error", data: null, error });
      });

    return () => {
      cancelled = true;
    };
    // `load` is expected to be a stable closure from the caller; `nonce` drives
    // explicit refreshes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nonce]);

  return { ...state, reload };
}
