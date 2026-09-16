import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

// 🔴 EL LINTER NO VEÍA LOS COMPONENTES USADOS EN JSX (2026-09-16). `no-unused-vars` de ESLint 9 no
// cuenta `<ChipRol/>` como uso de `ChipRol`: marcaba como «sin usar» componentes que se dibujan en
// pantalla (`IcoLab`, `ChipRol`, `ResumenPermisos`, `AyudaGuiada`…) y el total de «variables sin
// usar» salía inflado. Peor: limpiarlas confiando en ese número rompía la app. Es lo que hace
// `react/jsx-uses-vars`; acá va escrito a mano para no sumar una dependencia por 15 líneas.
const jsxUsaVariables = {
  meta: { type: 'problem', schema: [] },
  create(context) {
    return {
      JSXOpeningElement(node) {
        let n = node.name
        if (n.type === 'JSXNamespacedName') return
        const esMiembro = n.type === 'JSXMemberExpression'
        while (n.type === 'JSXMemberExpression') n = n.object
        if (n.type !== 'JSXIdentifier') return
        // <div>, <svg>… son etiquetas del navegador, no variables (salvo `<obj.Comp>`)
        if (!esMiembro && /^[a-z]/.test(n.name)) return
        context.sourceCode.markVariableAsUsed(n.name, node)
      },
    }
  },
}

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
    plugins: { tizada: { rules: { 'jsx-usa-variables': jsxUsaVariables } } },
    rules: {
      'tizada/jsx-usa-variables': 'error',
      // `const { a, b, ...resto } = x` para SACAR a y b del resto es a propósito: no es «sin usar».
      'no-unused-vars': ['error', { ignoreRestSiblings: true }],
    },
    languageOptions: {
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
  },
])
