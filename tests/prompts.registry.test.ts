import assert from 'assert';
import { PromptRegistry } from '../src/prompts/registry';

function run() {
  const reg = new PromptRegistry();
  // clean slate
  reg.remove('test.temp');

  const t1 = {
    name: 'test.temp',
    version: '1.0.0',
    content: 'Hello {{name}}',
    inputs: ['name']
  };
  reg.add(t1 as any);

  const t2 = {
    name: 'test.temp',
    version: '1.1.0',
    content: 'Hi {{name}} v1.1',
    inputs: ['name']
  };
  reg.add(t2 as any);

  const latest = reg.get('test.temp');
  assert(latest && latest.version === '1.1.0');

  const exact = reg.get('test.temp', '1.0.0');
  assert(exact && exact.version === '1.0.0');

  const caret = reg.get('test.temp', '^1.0.0');
  assert(caret && caret.version === '1.1.0');

  reg.update('test.temp', '1.1.0', { content: 'Updated {{name}}' });
  const updated = reg.get('test.temp', '1.1.0');
  assert(updated && updated.content.includes('Updated'));

  reg.remove('test.temp', '1.0.0');
  assert(!reg.get('test.temp', '1.0.0'));

  reg.remove('test.temp');
  assert(!reg.get('test.temp'));

  console.log('Prompt registry tests passed');
}

run();
