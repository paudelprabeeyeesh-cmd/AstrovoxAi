import type { ModelProvider, GenerateOptions, GenerateResponse } from '../types';

export const openaiProvider: ModelProvider = {
  name: 'openai',
  supportsStreaming: true,

  async generate(options: GenerateOptions): Promise<GenerateResponse | AsyncIterable<string>> {
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) throw new Error('OPENAI_API_KEY not set');

    const model = options.model;
    const headers: Record<string, string> = {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    };

    const body: any = {};
    if (options.messages) {
      body.model = model;
      body.messages = options.messages;
      body.max_tokens = options.maxTokens ?? 1024;
      body.temperature = options.temperature ?? 0.2;
      body.stream = !!options.stream;
    } else if (options.prompt) {
      body.model = model;
      body.prompt = options.prompt;
      body.max_tokens = options.maxTokens ?? 256;
      body.temperature = options.temperature ?? 0.2;
      body.stream = !!options.stream;
    }

    const url = 'https://api.openai.com/v1/chat/completions';

    if (options.stream) {
      const resp = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(body)
      });

      if (!resp.ok || !resp.body) {
        const t = await resp.text();
        throw new Error(`OpenAI stream error: ${resp.status} ${t}`);
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder('utf-8');

      return (async function* () {
        try {
          let buffer = '';
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split(/\r?\n/);
            buffer = parts.pop() ?? '';
            for (const line of parts) {
              if (!line) continue;
              const s = line.replace(/^data: /, '');
              if (s === '[DONE]') return;
              try {
                const json = JSON.parse(s);
                const delta = json?.choices?.[0]?.delta;
                if (delta?.content) {
                  yield delta.content;
                } else {
                  const txt = json?.choices?.[0]?.text;
                  if (txt) yield txt;
                }
              } catch (e) {
                yield s;
              }
            }
          }
          if (buffer) {
            try {
              const json = JSON.parse(buffer);
              const txt = json?.choices?.[0]?.delta?.content ?? json?.choices?.[0]?.text;
              if (txt) yield txt;
            } catch (e) {
              yield buffer;
            }
          }
        } finally {
          try { reader.releaseLock(); } catch {}
        }
      })();
    } else {
      const resp = await fetch(url, { method: 'POST', headers, body: JSON.stringify(body) });
      if (!resp.ok) {
        const t = await resp.text();
        throw new Error(`OpenAI error ${resp.status}: ${t}`);
      }
      const json = await resp.json();
      const text = (json.choices && json.choices.map((c: any) => c.message?.content ?? c.text).join('')) ?? json.text ?? '';
      const usage = json.usage ? {
        promptTokens: json.usage.prompt_tokens,
        completionTokens: json.usage.completion_tokens,
        totalTokens: json.usage.total_tokens,
        costUSD: undefined
      } : undefined;

      const out = {
        id: json.id,
        text,
        finishReason: json.choices?.[0]?.finish_reason ?? null,
        usage
      } as GenerateResponse;

      return out;
    }
  },

  async cancel(_id: string) {
    // no-op
  }
};
