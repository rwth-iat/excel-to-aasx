// PlantUML diagrams for the preview, rendered by the server (ADR 0011).
// Kept by source text, so only a changed diagram is sent again. Requests start only after
// typing has paused, go one at a time with a gap between them, and outdated versions are
// dropped before they are sent. The server enforces the same per session.

const PAUSE_MS = 1500;
const GAP_MS = 2000;
const RETRY_MS = 3000;

export function createDiagrams(render, onChange) {
  const cache = new Map(); // source -> { url } | { error } | { pending: true, retried? }
  const queue = [];
  let pauseTimer = null;
  let gapTimer = null;
  let busy = false;
  let lastStart = 0;

  function pump() {
    if (busy || gapTimer || queue.length === 0) return;
    const wait = lastStart + GAP_MS - Date.now();
    if (wait > 0) {
      gapTimer = setTimeout(() => { gapTimer = null; pump(); }, wait);
      return;
    }
    run(queue.shift());
  }

  async function run(source) {
    busy = true;
    lastStart = Date.now();
    try {
      const blob = await render(source);
      if (cache.has(source)) cache.set(source, { url: URL.createObjectURL(blob) });
    } catch (error) {
      const state = cache.get(source);
      if (error.status === 429 && state && !state.retried) {
        cache.set(source, { pending: true, retried: true });
        setTimeout(() => { if (cache.has(source)) { queue.push(source); pump(); } }, RETRY_MS);
      } else if (state) {
        cache.set(source, { error: error.message });
      }
    } finally {
      busy = false;
      onChange();
      pump();
    }
  }

  function prune(keep) {
    for (const [source, state] of cache) {
      if (keep.has(source)) continue;
      if (state.url) URL.revokeObjectURL(state.url);
      cache.delete(source);
    }
    queue.splice(0, queue.length, ...queue.filter((s) => keep.has(s)));
  }

  return {
    lookup: (source) => cache.get(source),
    want(sources) {
      prune(new Set(sources));
      clearTimeout(pauseTimer);
      pauseTimer = setTimeout(() => {
        for (const source of sources) {
          if (cache.has(source)) continue;
          cache.set(source, { pending: true });
          queue.push(source);
        }
        onChange();
        pump();
      }, PAUSE_MS);
    },
  };
}
