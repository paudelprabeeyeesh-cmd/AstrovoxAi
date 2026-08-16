import fs from 'fs';
import path from 'path';
import { PromptTemplate, validateTemplate } from './schema';

const REGISTRY_FILE = path.join(process.cwd(), 'src', 'prompts', 'registry.json');

function parseSemver(v: string) {
  const parts = v.split('-')[0].split('.').map(p => parseInt(p, 10));
  return [parts[0] || 0, parts[1] || 0, parts[2] || 0];
}

function compareSemver(a: string, b: string) {
  const pa = parseSemver(a);
  const pb = parseSemver(b);
  for (let i = 0; i < 3; i++) {
    if (pa[i] > pb[i]) return 1;
    if (pa[i] < pb[i]) return -1;
  }
  return 0;
}

function satisfiesRange(version: string, range?: string) {
  if (!range || range === 'latest') return true;
  range = range.trim();
  if (range === version) return true;
  // basic operators
  if (range.startsWith('>=')) {
    const v = range.slice(2).trim();
    return compareSemver(version, v) >= 0;
  }
  if (range.startsWith('<=')) {
    const v = range.slice(2).trim();
    return compareSemver(version, v) <= 0;
  }
  if (range.startsWith('>')) {
    const v = range.slice(1).trim();
    return compareSemver(version, v) > 0;
  }
  if (range.startsWith('<')) {
    const v = range.slice(1).trim();
    return compareSemver(version, v) < 0;
  }
  if (range.startsWith('^')) {
    const v = range.slice(1).trim();
    const [maj] = parseSemver(v);
    const [verMaj] = parseSemver(version);
    return verMaj === maj && compareSemver(version, v) >= 0;
  }
  if (range.startsWith('~')) {
    const v = range.slice(1).trim();
    const [maj, min] = parseSemver(v);
    const [verMaj, verMin] = parseSemver(version);
    return verMaj === maj && verMin === min && compareSemver(version, v) >= 0;
  }
  // fallback: exact match
  return version === range;
}

export class PromptRegistry {
  private templates: Map<string, PromptTemplate[]> = new Map();

  constructor(private persistFile = REGISTRY_FILE) {
    this.loadFromDisk();
  }

  private loadFromDisk() {
    try {
      if (!fs.existsSync(this.persistFile)) return;
      const txt = fs.readFileSync(this.persistFile, 'utf-8');
      const obj = JSON.parse(txt);
      if (!obj || typeof obj !== 'object') return;
      for (const name of Object.keys(obj)) {
        const arr = obj[name] as PromptTemplate[];
        this.templates.set(name, arr);
      }
    } catch (e) {
      console.error('Failed to load prompt registry:', e);
    }
  }

  private persist() {
    try {
      const out: Record<string, PromptTemplate[]> = {};
      for (const [k, v] of this.templates.entries()) out[k] = v;
      const dir = path.dirname(this.persistFile);
      if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(this.persistFile, JSON.stringify(out, null, 2), 'utf-8');
    } catch (e) {
      console.error('Failed to persist prompt registry:', e);
    }
  }

  listNames() {
    return Array.from(this.templates.keys());
  }

  listVersions(name: string) {
    const arr = this.templates.get(name) ?? [];
    return arr.map(t => t.version).sort((a, b) => compareSemver(b, a));
  }

  add(template: PromptTemplate) {
    const { valid, errors } = validateTemplate(template);
    if (!valid) throw new Error('Invalid template: ' + errors.join('; '));
    const arr = this.templates.get(template.name) ?? [];
    // prevent duplicate version
    if (arr.some(t => t.version === template.version)) throw new Error('Template version already exists');
    arr.push({ ...template, createdAt: template.createdAt ?? new Date().toISOString(), updatedAt: new Date().toISOString() });
    // sort descending
    arr.sort((a, b) => compareSemver(b.version, a.version));
    this.templates.set(template.name, arr);
    this.persist();
    return template;
  }

  get(name: string, versionRange?: string): PromptTemplate | null {
    const arr = this.templates.get(name);
    if (!arr || arr.length === 0) return null;
    if (!versionRange || versionRange === 'latest') return arr[0];
    // find highest version satisfying range
    const candidates = arr.filter(t => satisfiesRange(t.version, versionRange));
    if (!candidates || candidates.length === 0) return null;
    candidates.sort((a, b) => compareSemver(b.version, a.version));
    return candidates[0];
  }

  remove(name: string, version?: string) {
    if (!this.templates.has(name)) return false;
    if (!version) {
      this.templates.delete(name);
      this.persist();
      return true;
    }
    const arr = this.templates.get(name)!.filter(t => t.version !== version);
    if (arr.length === 0) this.templates.delete(name);
    else this.templates.set(name, arr);
    this.persist();
    return true;
  }

  update(name: string, version: string, patch: Partial<PromptTemplate>) {
    const arr = this.templates.get(name);
    if (!arr) throw new Error('Template not found');
    const idx = arr.findIndex(t => t.version === version);
    if (idx < 0) throw new Error('Version not found');
    const updated = { ...arr[idx], ...patch, updatedAt: new Date().toISOString() };
    const { valid, errors } = validateTemplate(updated);
    if (!valid) throw new Error('Invalid updated template: ' + errors.join('; '));
    arr[idx] = updated;
    arr.sort((a, b) => compareSemver(b.version, a.version));
    this.templates.set(name, arr);
    this.persist();
    return updated;
  }
}
