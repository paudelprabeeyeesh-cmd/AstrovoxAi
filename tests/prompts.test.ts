import assert from 'assert';
import { PromptLoader } from '../src/prompts/loader';

async function runTests() {
  const loader = new PromptLoader({ templatesDir: 'src/prompts/templates', watch: false });

  // Test rendering with default
  const out1 = loader.render('system.welcome', { user_name: 'Alex' });
  assert(out1.text.includes('Hello, Alex'));

  // Test default value
  const out2 = loader.render('system.welcome', {});
  assert(out2.text.includes('Hello, there'));

  // Test missing template
  let threw = false;
  try {
    loader.render('non.existent', {});
  } catch (e) { threw = true; }
  assert(threw, 'expected error for missing template');

  // Test developer issue_summary
  const dev = loader.render('developer.issue_summary', { issue_title: 'Bug', issue_body: 'Steps to reproduce' });
  assert(dev.text.includes('Title: Bug'));

  console.log('All prompt tests passed');
}

runTests().catch(err => { console.error(err); process.exit(1); });
