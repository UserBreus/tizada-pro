/**
 * Config de ESLint AL SOLO EFECTO de cazar los dos errores que dejan la PANTALLA NEGRA y que
 * ningún contrato puede ver (no ejecutan React). La usa `verificar_tdz.mjs`.
 *
 *   · `no-use-before-define` — leer una `const` antes de su declaración → «Cannot access X before
 *     initialization» (changelog 348: pasó al cargar el arte con la ayuda abierta).
 *   · `no-undef` — usar algo que NO EXISTE → «X is not defined» (changelog 351: al eliminar la
 *     lógica de 2 diseños me llevé por delante `carga` y `modalAb`, que estaban en el medio del
 *     bloque borrado; el build compiló igual y la pantalla quedó negra).
 *
 * Va aparte de `eslint.config.js` a propósito: ese config del proyecto hoy NO ARRANCA
 * (`reactHooks.configs.flat.recommended` es undefined con la versión instalada del plugin), o sea
 * `npm run lint` está roto — otra cosa para arreglar, pero este candado no puede depender de eso.
 */
import globals from 'globals';

export default [
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      parserOptions: { ecmaFeatures: { jsx: true } },
      // el navegador (document, window, fetch…) y las globales de Node que usan los contratos
      globals: { ...globals.browser, ...globals.node },
    },
    // los `eslint-disable-line react-hooks/...` del código apuntan a un plugin que acá no se
    // carga; sin esto ESLint los reporta como «regla no encontrada» y tapa lo que importa
    linterOptions: { noInlineConfig: true },
    rules: {
      'no-use-before-define': ['error', { variables: true, functions: false, classes: false }],
      'no-undef': 'error',
    },
  },
];
