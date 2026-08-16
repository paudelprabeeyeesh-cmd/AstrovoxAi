import type { ModelTask } from './types';

/**
 * Simple selector: maps task -> preferred provider order
 * Extend with model capabilities, latency, cost heuristics, health checks, etc.
 */
export function selectProvidersForTask(task: ModelTask): string[] {
  const map: Record<string, string[]> = {
    chat: ['openai', 'anthropic', 'gemini', 'ollama'],
    embed: ['openai', 'gemini', 'ollama'],
    completion: ['openai', 'anthropic', 'gemini', 'ollama'],
    moderation: ['openai', 'anthropic'],
  };

  return map[task] ?? ['openai', 'anthropic', 'gemini', 'ollama'];
}
