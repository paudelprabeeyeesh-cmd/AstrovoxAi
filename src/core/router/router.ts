import type { ModelProvider, GenerateOptions, GenerateResponse, ModelTask } from './types';
import { selectProvidersForTask } from './selector';
import { asAsyncIterable } from './abstractProvider';
import { usage } from './usage';

export class Router {
  private providers: Map<string, ModelProvider> = new Map();

  registerProvider(provider: ModelProvider) {
    if (!provider || !provider.name) throw new Error('Invalid provider');
    this.providers.set(provider.name, provider);
  }

  hasProvider(name: string) {
    return this.providers.has(name);
  }

  private async tryGenerate(providerName: string, options: GenerateOptions): Promise<GenerateResponse | AsyncIterable<string>> {
    const p = this.providers.get(providerName);
    if (!p) throw new Error(`Provider ${providerName} not found`);
    return p.generate(options);
  }

  async generate(task: ModelTask, options: GenerateOptions): Promise<GenerateResponse | AsyncIterable<string>> {
    const providerOrder = selectProvidersForTask(task);

    const tried: Array<{ provider: string; error?: any; response?: any }> = [];

    for (const pn of providerOrder) {
      if (!this.providers.has(pn)) continue;
      try {
        const res = await this.tryGenerate(pn, options);
        if (res && typeof (res as any)[Symbol.asyncIterator] !== 'function') {
          const gr = res as GenerateResponse;
          usage.record({
            provider: pn,
            model: options.model,
            promptTokens: gr.usage?.promptTokens,
            completionTokens: gr.usage?.completionTokens,
            totalTokens: gr.usage?.totalTokens,
            costUSD: gr.usage?.costUSD,
            meta: { task }
          });
          return gr;
        }

        const iterable = asAsyncIterable(res as any);
        usage.record({ provider: pn, model: options.model, meta: { streamed: true, task } });
        return iterable;
      } catch (err) {
        tried.push({ provider: pn, error: err });
      }
    }

    throw new Error(`All providers failed for task ${task}: ${JSON.stringify(tried.map(t => ({ provider: t.provider, error: String(t.error) })))}`);
  }
}
