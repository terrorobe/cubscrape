import js from '@eslint/js'
import vue from 'eslint-plugin-vue'
import prettier from 'eslint-plugin-prettier'
import prettierConfig from 'eslint-config-prettier'
import betterTailwind from 'eslint-plugin-better-tailwindcss'

export default [
  {
    ignores: [
      'node_modules/**',
      '.venv/**',
      '__pycache__/**',
      'dist/**',
      '.vite/**',
      'data/**',
      '.mypy_cache/**',
      'archive/**',
      '**/*.py',
    ],
  },
  js.configs.recommended,
  ...vue.configs['flat/recommended'],
  prettierConfig,
  {
    files: ['**/*.vue', '**/*.js', '**/*.jsx', '**/*.ts', '**/*.tsx'],
    plugins: {
      prettier,
      'better-tailwindcss': betterTailwind,
    },
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        console: 'readonly',
        window: 'readonly',
        document: 'readonly',
        fetch: 'readonly',
        navigator: 'readonly',
        setTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        requestAnimationFrame: 'readonly',
        require: 'readonly',
        URL: 'readonly',
        URLSearchParams: 'readonly',
        process: 'readonly', // For Node.js scripts
        localStorage: 'readonly',
        confirm: 'readonly',
        Blob: 'readonly',
        FileReader: 'readonly',
      },
    },
    settings: {
      'better-tailwindcss': {
        // Tailwind v4 configuration
        entryPoint: './src/style.css',
        callees: ['classnames', 'clsx', 'cn'],
      },
    },
    rules: {
      // Prettier integration
      'prettier/prettier': 'error',

      // Vue specific rules
      'vue/multi-word-component-names': 'off',
      'vue/no-unused-vars': 'error',
      'vue/no-multiple-template-root': 'off',

      // General JavaScript rules
      'no-console': 'off', // Allow console statements in utility scripts
      'no-debugger': 'error',
      'no-unused-vars': 'error',
      'prefer-const': 'error',
      'no-var': 'error',

      // Code quality
      eqeqeq: 'error',
      curly: 'error',
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'no-trailing-spaces': 'error',

      // Prettier compatibility - disable formatting rules
      'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/html-self-closing': 'off',
      'vue/attributes-order': 'off',

      // Better Tailwind CSS rules
      'better-tailwindcss/multiline': 'off', // Conflicts with Prettier
      'better-tailwindcss/sort-classes': 'off', // Let Prettier handle this
      'better-tailwindcss/enforce-consistent-class-order': 'off', // Let Prettier handle this
      'better-tailwindcss/enforce-consistent-important-position': 'warn',
      'better-tailwindcss/enforce-consistent-line-wrapping': 'off', // Conflicts with Prettier
      'better-tailwindcss/enforce-shorthand-classes': 'warn',
      'better-tailwindcss/no-conflicting-classes': 'warn',
      'better-tailwindcss/no-deprecated-classes': 'warn',
      'better-tailwindcss/no-duplicate-classes': 'warn',
      'better-tailwindcss/no-unnecessary-whitespace': 'warn',
      'better-tailwindcss/no-unregistered-classes': 'off', // Too strict for v4
    },
  },
]
