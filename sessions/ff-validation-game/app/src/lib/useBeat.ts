import { useEffect, useRef } from 'react';

// Per-beat telemetry capture. Tracks the spec's behavioral signals for each
// screen: latency-to-first-tap, re-tap/scrub count, total dwell, and whether
// fine print was opened. Returns getters the beat reads when it logs.
export function useBeat() {
  const mounted = useRef<number>(Date.now());
  const firstTap = useRef<number | null>(null);
  const retaps = useRef<number>(0);
  const finePrint = useRef<boolean>(false);
  const inspected = useRef<Set<string>>(new Set());

  useEffect(() => {
    mounted.current = Date.now();
    firstTap.current = null;
    retaps.current = 0;
    finePrint.current = false;
    inspected.current = new Set();
  }, []);

  function onTap() {
    if (firstTap.current == null) firstTap.current = Date.now();
    else retaps.current += 1;
  }
  function onInspect(optionId: string) {
    inspected.current.add(optionId);
  }
  function openFinePrint() {
    finePrint.current = true;
  }

  function snapshot() {
    const now = Date.now();
    return {
      latencyMs: firstTap.current != null ? firstTap.current - mounted.current : undefined,
      retapCount: retaps.current,
      dwellMs: now - mounted.current,
      finePrintOpened: finePrint.current,
      optionsInspected: inspected.current.size,
    };
  }

  return { onTap, onInspect, openFinePrint, snapshot };
}
