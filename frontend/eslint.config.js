import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    // Los archivos de configuración corren en NODE, no en el navegador: sin esto el linter
    // marcaba `process is not defined` en `vite.config.js` (un error que no existe).
    files: ['*.config.js', '*.config.mjs', 'vite.config.js'],
    languageOptions: { globals: globals.node },
  },
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      // 🔴 `configs.flat.recommended` NO EXISTE en el plugin instalado: el linter reventaba con
      // «Cannot read properties of undefined (reading 'recommended')» y `npm run lint` no corría
      // desde vaya a saber cuándo (2026-09-15). La forma «flat» de este plugin es
      // `recommended-latest`. Un linter que no arranca es un linter que no existe.
      reactHooks.configs['recommended-latest'],
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
  },
])
