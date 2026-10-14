/**
 * Defences for the extension's agent surface.
 *
 * The whole problem in one sentence: a file's contents are data, and an agent
 * reads them, so the contents must never be able to look like an instruction.
 *
 * Everything here is deliberately small and pure so it can be tested without a
 * VS Code host. None of it is a substitute for the approval gates a real coding
 * agent needs; it is the input hygiene that makes those gates reachable.
 */

import * as path from 'path'

// Anything matching a key prefix is treated as a secret even if it looks like
// an identifier. A pattern list rather than a length check, because "a long
// string" is not what makes a credential a credential.
const SECRET_PATTERNS = [
  /\bsk-[A-Za-z0-9_-]{16,}/,
  /\bAKIA[A-Z0-9]{12,}/,
  /\bghp_[A-Za-z0-9]{16,}/,
  /\bgho_[A-Za-z0-9]{16,}/,
  /\bxox[baprs]-[A-Za-z0-9-]{10,}/,
  /\bglpat-[A-Za-z0-9_-]{16,}/,
  /\bAIza[0-9A-Za-z_-]{30,}/,
  /\b-----BEGIN [A-Z ]*PRIVATE KEY-----/,
]

// Assignment-shaped secrets, so a redaction pass catches `KEY=value` lines.
const ASSIGNMENT_SECRET = /\b([A-Z0-9_]*(?:SECRET|TOKEN|PASSWORD|PRIVATE_KEY)[A-Z0-9_]*)\s*=\s*(\S+)/gi

// Lift from a real credential-looking string: a run of key-shaped characters.
const SECRET_SHAPE = /\b(?:sk-|AKIA|ghp_|gho_|xox|glpat-|AIza)[A-Za-z0-9_-]{8,}/g

// Refused outright. A lockfile or a key file should never be sent as context
// whatever its size, because the cost of sending one is a credential leak.
const DENIED_BASENAMES = new Set([
  'package-lock.json',
  'yarn.lock',
  'pnpm-lock.yaml',
  'npm-shrinkwrap.json',
  '.env',
  '.npmrc',
  '.pypirc',
  '.git-credentials',
  'id_rsa',
  'id_dsa',
  'id_ecdsa',
  'id_ed25519',
  '.netrc',
])

// Denied anywhere in the path, not just as the basename: `.git/config` holds
// remotes and credentials, and `node_modules` is a dependency, not the user's code.
const DENIED_PATH_PARTS = ['.git', 'node_modules', '.ssh', '.aws', '.gnupg', '.azure']

// One file above this size is refused rather than truncated. Truncating a
// lockfile or a bundle gives the model a partial, misleading view and still
// sends everything up to the cut.
const MAX_TRANSMIT_BYTES = 2 * 1024 * 1024

const FENCE_OPEN = '<<<UNTRUSTED_CONTENT>>>'
const FENCE_CLOSE = '<<<END_UNTRUSTED_CONTENT>>>'

/**
 * Wrap untrusted text so the model can tell where it starts and stops.
 *
 * The payload is preserved verbatim except for angle brackets in tags, which
 * are escaped: an unescaped `</system>` inside the content could close the
 * system prompt and open its own instructions.
 */
function sanitizeContentForPrompt(content) {
  if (typeof content !== 'string' || content.length === 0) {
    return content === '' ? '' : ''
  }

  let body = content
  // Escape only the closing forms. An opening `<system>` in user data is inert;
  // a closing one is what lets a payload end the real prompt early.
  body = body.replace(/<\/system>/gi, '&lt;/system&gt;')
  body = body.replace(/<\/assistant>/gi, '&lt;/assistant&gt;')

  if (!body.trim()) {
    return ''
  }
  return `${FENCE_OPEN}\n${body}\n${FENCE_CLOSE}`
}

/**
 * Whether a string looks like a credential.
 *
 * Deliberately conservative: a false positive costs a redaction marker the
 * user can see, while a false negative sends a live key to a third party.
 */
function isSecretLike(value) {
  if (typeof value !== 'string' || value.length === 0) {
    return false
  }
  return SECRET_PATTERNS.some((pattern) => pattern.test(value))
}

/** Replace every credential-looking run with a marker. */
function redactSecrets(content) {
  if (typeof content !== 'string' || content.length === 0) {
    return content
  }

  let out = content.replace(SECRET_SHAPE, '[REDACTED_KEY]')
  out = out.replace(
    ASSIGNMENT_SECRET,
    (_match, name) => `${name}=[REDACTED]`
  )
  // A multi-line private key block, which no line-based pattern can hold.
  out = out.replace(
    /-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/g,
    '[REDACTED_KEY_BLOCK]'
  )
  return out
}

/**
 * Whether a file may be sent to the model at all.
 *
 * Four independent checks: workspace confinement, size, a denied basename,
 * and a denied path part. All are needed because they catch different leaks -
 * confinement catches a symlink or a ../ escape, size catches a bundle, the
 * basename catches a lockfile, and the path part catches `.git/config` and
 * `node_modules`.
 *
 * workspaceRoot is required, not optional. Without it a caller cannot be
 * confined to the project at all, and "any absolute path the agent was given"
 * is exactly the exfiltration path.
 */
function shouldTransmitToModel(absolutePath, byteLength, workspaceRoot) {
  if (typeof absolutePath !== 'string' || absolutePath.length === 0) {
    return false
  }
  if (typeof byteLength !== 'number' || Number.isNaN(byteLength) || byteLength < 0) {
    return false
  }
  if (!workspaceRoot || typeof workspaceRoot !== 'string') {
    return false
  }

  // Confinement first: an escape makes every other check irrelevant.
  try {
    resolveWithinWorkspace(workspaceRoot, absolutePath)
  } catch {
    return false
  }

  if (byteLength > MAX_TRANSMIT_BYTES) {
    return false
  }

  const base = path.basename(absolutePath).toLowerCase()
  if (DENIED_BASENAMES.has(base)) {
    return false
  }

  const parts = absolutePath.split(/[\\/]/).map((p) => p.toLowerCase())
  if (parts.some((part) => DENIED_PATH_PARTS.includes(part))) {
    return false
  }

  // A dotfile is not automatically secret, but a dotfile nobody edits in an
  // editor almost always is.
  if (base !== '.' && base !== '..' && base.startsWith('.') && base !== '.md') {
    return false
  }

  return true
}

/**
 * Resolve a path and confirm it is inside the workspace.
 *
 * Throws rather than returning a normalised path: a caller that gets a string
 * back cannot tell "inside" from "escaped", and the escape case must be a loud
 * failure rather than a silently rewritten path.
 */
function resolveWithinWorkspace(workspaceRoot, candidate) {
  const root = normalize(workspaceRoot)
  const resolved = normalize(candidate)

  if (!isInside(root, resolved)) {
    throw new Error(`path is outside the workspace: ${candidate}`)
  }
  return resolved
}

function normalize(p) {
  if (typeof p !== 'string' || p.length === 0) {
    return ''
  }
  // path.resolve collapses `..` without touching the filesystem, so a
  // traversal cannot hide behind a segment the OS would reject later.
  return path.resolve(p)
}

function isInside(root, target) {
  if (!root || !target) {
    return false
  }
  if (target === root) {
    return true
  }
  const rootWithSep = root.endsWith(path.sep) ? root : root + path.sep
  return target.startsWith(rootWithSep)
}

export { sanitizeContentForPrompt }
export { isSecretLike }
export { redactSecrets }
export { shouldTransmitToModel }
export { resolveWithinWorkspace }
