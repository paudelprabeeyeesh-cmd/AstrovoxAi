// Flat config. ESLint 8.57 defaults to flat config when no eslintrc is found,
// and in that mode `--ext` is rejected, which is why `npm run lint` failed
// before: the script passed `--ext ts` to a linter running in flat mode.
const tsParser = require('@typescript-eslint/parser')
const tsPlugin = require('@typescript-eslint/eslint-plugin')

module.exports = [
  {
    ignores: ['out/**', 'node_modules/**', '.vscode-test/**'],
  },
  {
    files: ['src/**/*.ts'],
    languageOptions: {
      parser: tsParser,
      ecmaVersion: 2022,
      sourceType: 'module',
    },
    plugins: { '@typescript-eslint': tsPlugin },
    rules: {
      ...tsPlugin.configs.recommended.rules,
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      'no-console': 'off',
    },
  },
  {
    // The attack suite. CommonJS and plain JavaScript, because it runs the
    // compiled output with node:test rather than in the extension host.
    files: ['tests/**/*.cjs'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'script',
    },
    rules: {
      'no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    },
  },
]
