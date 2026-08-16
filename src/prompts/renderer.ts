export interface RenderOptions {
  sanitize?: boolean;
  escapeHtml?: boolean;
  strict?: boolean; // throw on missing variables
  tokenEstimator?: (text: string) => number;
  types?: Record<string, 'string' | 'number' | 'boolean' | 'json'>;
}

export interface RenderResult {
  text: string;
  missing: string[];
  tokens?: number;
}

const PLACEHOLDER_RE = /{{\s*([a-zA-Z0-9_.\-]+)(?:\|([^}]+))?\s*}}/g;

function escapeHtml(s: string) {
  return s.replace(/[&<>"']/g, (c) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[c]));
}

export function renderTemplate(template: string, variables: Record<string, any> = {}, options: RenderOptions = {}): RenderResult {
  const { sanitize = true, escapeHtml: doEscape = true, strict = true, tokenEstimator, types } = options;
  const missing: Set<string> = new Set();

  const text = template.replace(PLACEHOLDER_RE, (_match, name: string, defaultValue: string) => {
    const val = lookupVariable(variables, name);
    if (val === undefined || val === null) {
      if (defaultValue !== undefined) {
        return sanitize ? sanitizeValue(defaultValue, doEscape) : String(defaultValue);
      }
      missing.add(name);
      return strict ? (() => { throw new Error(`Missing template variable: ${name}`); })() : '';
    }

    // type validation
    if (types && types[name]) {
      const expected = types[name];
      if (!validateType(val, expected)) {
        throw new Error(`Template variable ${name} expected type ${expected} but got ${typeof val}`);
      }
    }

    return sanitize ? sanitizeValue(val, doEscape) : String(val);
  });

  const out: RenderResult = { text, missing: Array.from(missing) };
  if (tokenEstimator) {
    try {
      out.tokens = tokenEstimator(text);
    } catch (e) {
      // ignore estimator errors
    }
  }
  return out;
}

function lookupVariable(vars: Record<string, any>, name: string) {
  // support dot paths
  if (Object.prototype.hasOwnProperty.call(vars, name)) return vars[name];
  const parts = name.split('.');
  let cur: any = vars;
  for (const p of parts) {
    if (cur == null) return undefined;
    if (!Object.prototype.hasOwnProperty.call(cur, p)) return undefined;
    cur = cur[p];
  }
  return cur;
}

function sanitizeValue(val: any, doEscape: boolean) {
  if (val === null || val === undefined) return '';
  if (typeof val === 'object') {
    try { return JSON.stringify(val); } catch { return String(val); }
  }
  const s = String(val);
  return doEscape ? escapeHtml(s) : s;
}

function validateType(val: any, expected: 'string' | 'number' | 'boolean' | 'json') {
  switch (expected) {
    case 'string': return typeof val === 'string';
    case 'number': return typeof val === 'number';
    case 'boolean': return typeof val === 'boolean';
    case 'json': return typeof val === 'object' || typeof val === 'string';
    default: return true;
  }
}
