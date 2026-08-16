// Small helper to wrap non-stream responses into AsyncIterable
import type { GenerateOptions, GenerateResponse } from './types';

export function asAsyncIterable(resultPromiseOrIterable: Promise<GenerateResponse> | AsyncIterable<string> | GenerateResponse): AsyncIterable<string> {
  if ((resultPromiseOrIterable as any)[Symbol.asyncIterator]) {
    return resultPromiseOrIterable as AsyncIterable<string>;
  }

  return (async function* () {
    const res = await Promise.resolve(resultPromiseOrIterable as Promise<GenerateResponse> | GenerateResponse);
    if (res == null) return;
    if (typeof res === 'object') {
      if (typeof res.text === 'string') {
        yield res.text;
      } else if ((res as any).choices && Array.isArray((res as any).choices)) {
        for (const ch of (res as any).choices) {
          if (typeof ch.text === 'string') yield ch.text;
          else if (ch.delta && ch.delta.content) yield ch.delta.content;
        }
      }
    } else if (typeof res === 'string') {
      yield res;
    }
  })();
}
