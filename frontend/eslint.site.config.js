import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';

export default [
  { ignores: ['node_modules/**', 'dist/**', 'dist-site/**'] },
  {
    files: ['website/**/*.{js,jsx}', 'tests/site*.js'],
    ...js.configs.recommended,
    languageOptions: { globals: { ...globals.browser, ...globals.node }, parserOptions: { ecmaFeatures: { jsx: true } } },
    plugins: { 'react-hooks': reactHooks },
    rules: { ...js.configs.recommended.rules, ...reactHooks.configs.recommended.rules, 'no-unused-vars': ['error', { varsIgnorePattern: '^[A-Z]' }] },
  },
  { files: ['scripts/*.mjs', '*.site.config.js'], ...js.configs.recommended, languageOptions: { globals: globals.node } },
];
