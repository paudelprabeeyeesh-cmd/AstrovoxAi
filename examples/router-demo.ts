import { Router } from '../src/core/router/router';
import { openaiProvider } from '../src/core/router/providers/openai';

async function main() {
  const r = new Router();
  r.registerProvider(openaiProvider);

  const res = await r.generate('chat', {
    model: 'gpt-4o-mini',
    messages: [{ role: 'system', content: 'You are a helpful assistant.' }, { role: 'user', content: 'Say hi' }],
    stream: false
  });

  if ((res as any)[Symbol.asyncIterator]) {
    for await (const chunk of res as AsyncIterable<string>) {
      process.stdout.write(chunk);
    }
  } else {
    console.log('Response text:', (res as any).text);
  }
}

main().catch(err => { console.error(err); process.exit(1); });
