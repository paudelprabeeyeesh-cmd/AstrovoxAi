import fs from 'fs';
import path from 'path';
import { renderTemplate, RenderOptions } from './renderer';
import { PromptTemplate } from './schema';

export interface LoaderOptions {
  templatesDir?: string;
  watch?: boolean;
}

export class PromptLoader {
  private dir: string;
  private cache: Map<string, PromptTemplate> = new Map();
  private versions: Map<string, PromptTemplate[]> = new Map();
  private watcher: fs.FSWatcher | null = null;

  constructor(options: LoaderOptions = {}) {
    this.dir = options.templatesDir ?? path.join(process.cwd(), 'src', 'prompts');
    this.loadAll();
    if (options.watch) this.watch();
  }

  private async loadAll() {
    try {
      const entries = await fs.promises.readdir(this.dir, { withFileTypes: true });
      for (const e of entries) {
        if (e.isDirectory()) {
          await this.loadFolder(path.join(this.dir, e.name));
        }
      }
    } catch (e) {
      // no prompts folder yet
    }
  }

  private async loadFolder(folder: string) {
    const files = await fs.promises.readdir(folder);
    for (const f of files) {
      if (!f.endsWith('.json') && !f.endsWith('.yaml') && !f.endsWith('.yml')) continue;
      const fp = path.join(folder, f);
      try {
        const txt = await fs.promises.readFile(fp, 'utf-8');
        const tpl = parseTemplateFile(txt);
        if (tpl && tpl.name) {
          this.register(tpl);
        }
      } catch (e) {
        // ignore parse errors for now
        console.error('Failed to load prompt', fp, e);
      }
    }
  }

  private watch() {
    try {
      this.watcher = fs.watch(this.dir, { recursive: true }, (eventType, filename) => {
        if (!filename) return;
        const fp = path.join(this.dir, filename);
        // simple invalidation: reload all
        this.loadAll();
      });
    } catch (e) {
      // watch not available
    }
  }

  register(tpl: PromptTemplate) {
    const key = `${tpl.name}@${tpl.version}`;
    this.cache.set(key, tpl);
    const arr = this.versions.get(tpl.name) ?? [];
    arr.push(tpl);
    // simple sort by version string (semver would be better)
    arr.sort((a, b) => (a.version > b.version ? -1 : 1));
    this.versions.set(tpl.name, arr);
  }

  get(name: string, version?: string): PromptTemplate | null {
    if (version) {
      const key = `${name}@${version}`;
      return this.cache.get(key) ?? null;
    }
    const arr = this.versions.get(name);
    if (!arr || arr.length === 0) return null;
    return arr[0]; // latest
  }

  render(name: string, variables: Record<string, any> = {}, options: { version?: string } & RenderOptions = {}): { text: string; meta: any } {
    const tpl = this.get(name, options.version);
    if (!tpl) throw new Error(`Template ${name} not found`);
    const res = renderTemplate(tpl.content, variables, options);
    return { text: res.text, meta: { template: tpl, missing: res.missing, tokens: res.tokens } };
  }
}

function parseTemplateFile(txt: string): PromptTemplate | null {
  const trimmed = txt.trim();
  // try JSON
  if (trimmed.startsWith('{')) {
    try { return JSON.parse(trimmed) as PromptTemplate; } catch (e) { return null; }
  }
  // minimal YAML parser for simple key: value + content: | blocks
  const lines = txt.split(/\r?\n/);
  const obj: any = {};
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const m = line.match(/^([a-zA-Z0-9_\-]+):\s*(.*)$/);
    if (m) {
      const key = m[1];
      let rest = m[2];
      if (rest === '|') {
        // multiline block
        i++;
        const buf: string[] = [];
        while (i < lines.length) {
          const l = lines[i];
          if (l.match(/^\s*$/) && buf.length === 0) { i++; continue; }
          // stop on dedent of key at column 0
          if (!l.startsWith(' ') && !l.startsWith('\t')) break;
          buf.push(l.replace(/^\s?/, ''));
          i++;
        }
        obj[key] = buf.join('\n');
        continue;
      } else {
        // single-line value
        // parse arrays like [a,b]
        if (rest.startsWith('[') && rest.endsWith(']')) {
          const inner = rest.slice(1, -1).trim();
          obj[key] = inner.length ? inner.split(',').map(s => s.trim()) : [];
        } else if (rest === '') {
          obj[key] = '';
        } else {
          // remove surrounding quotes
          obj[key] = rest.replace(/^"|"$/g, '').replace(/^'|'$/g, '');
        }
      }
    }
    i++;
  }
  if (!obj.name || !obj.version || !obj.content) return null;
  // normalize types
  if (obj.inputs && typeof obj.inputs === 'string') obj.inputs = obj.inputs.split(',').map((s:string)=>s.trim());
  return obj as PromptTemplate;
}
