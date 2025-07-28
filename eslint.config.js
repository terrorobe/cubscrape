import js from '@eslint/js'
import vue from 'eslint-plugin-vue'
import * as vueParser from 'vue-eslint-parser'
import prettier from 'eslint-plugin-prettier'
import prettierConfig from 'eslint-config-prettier'
import betterTailwind from 'eslint-plugin-better-tailwindcss'
import typescript from '@typescript-eslint/eslint-plugin'
import typescriptParser from '@typescript-eslint/parser'
// Note: @vue/eslint-config-typescript not needed for flat config

export default [
  // Global ignores
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

  // Base configurations
  js.configs.recommended,
  ...vue.configs['flat/recommended'],
  prettierConfig,

  // JavaScript files
  {
    files: ['**/*.js', '**/*.jsx'],
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
        clearTimeout: 'readonly',
        requestAnimationFrame: 'readonly',
        require: 'readonly',
        URL: 'readonly',
        URLSearchParams: 'readonly',
        process: 'readonly',
        localStorage: 'readonly',
        confirm: 'readonly',
        Blob: 'readonly',
        FileReader: 'readonly',
      },
    },
    rules: {
      // Prettier integration
      'prettier/prettier': 'error',

      // General JavaScript rules
      'no-console': 'off',
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
    },
  },

  // TypeScript files
  {
    files: ['**/*.ts', '**/*.tsx'],
    plugins: {
      '@typescript-eslint': typescript,
      prettier,
      'better-tailwindcss': betterTailwind,
    },
    languageOptions: {
      parser: typescriptParser,
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: {
        project: './tsconfig.json',
      },
      globals: {
        console: 'readonly',
        window: 'readonly',
        document: 'readonly',
        fetch: 'readonly',
        navigator: 'readonly',
        setTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        clearTimeout: 'readonly',
        requestAnimationFrame: 'readonly',
        require: 'readonly',
        URL: 'readonly',
        URLSearchParams: 'readonly',
        process: 'readonly',
        localStorage: 'readonly',
        confirm: 'readonly',
        Blob: 'readonly',
        FileReader: 'readonly',
      },
    },
    rules: {
      // Prettier integration
      'prettier/prettier': 'error',

      // Disable base ESLint rules that conflict with TypeScript
      'no-unused-vars': 'off',
      'no-undef': 'off',
      'no-redeclare': 'off', // TypeScript handles function overloads

      // TypeScript-specific rules
      '@typescript-eslint/no-unused-vars': 'error',
      '@typescript-eslint/no-redeclare': 'error',
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/explicit-function-return-type': 'off',
      '@typescript-eslint/explicit-module-boundary-types': 'off',
      '@typescript-eslint/no-non-null-assertion': 'warn',
      '@typescript-eslint/no-var-requires': 'error',

      // Code quality
      eqeqeq: 'error',
      curly: 'error',
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'no-trailing-spaces': 'error',
      'no-console': 'off',
      'no-debugger': 'error',
    },
  },

  // Vue files
  {
    files: ['**/*.vue'],
    plugins: {
      '@typescript-eslint': typescript,
      prettier,
      'better-tailwindcss': betterTailwind,
    },
    languageOptions: {
      parser: vueParser,
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: {
        parser: typescriptParser,
        project: './tsconfig.json',
        extraFileExtensions: ['.vue'],
      },
      globals: {
        console: 'readonly',
        window: 'readonly',
        document: 'readonly',
        fetch: 'readonly',
        navigator: 'readonly',
        setTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        clearTimeout: 'readonly',
        requestAnimationFrame: 'readonly',
        require: 'readonly',
        URL: 'readonly',
        URLSearchParams: 'readonly',
        process: 'readonly',
        localStorage: 'readonly',
        confirm: 'readonly',
        Blob: 'readonly',
        FileReader: 'readonly',
      },
    },
    settings: {
      'better-tailwindcss': {
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
      'vue/max-attributes-per-line': 'off',
      'vue/singleline-html-element-content-newline': 'off',
      'vue/html-self-closing': 'off',
      'vue/attributes-order': 'off',

      // Disable base ESLint rules that conflict with TypeScript
      'no-unused-vars': 'off',
      'no-undef': 'off',
      'no-redeclare': 'off', // TypeScript handles function overloads

      // TypeScript rules for Vue files
      '@typescript-eslint/no-unused-vars': 'error',
      '@typescript-eslint/no-redeclare': 'error',
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/explicit-function-return-type': 'off',
      '@typescript-eslint/explicit-module-boundary-types': 'off',
      '@typescript-eslint/no-non-null-assertion': 'warn',

      // Code quality
      'no-console': 'off',
      'no-debugger': 'error',
      'prefer-const': 'error',
      'no-var': 'error',
      eqeqeq: 'error',
      curly: 'error',
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'no-trailing-spaces': 'error',

      // Better Tailwind CSS rules
      'better-tailwindcss/multiline': 'off',
      'better-tailwindcss/sort-classes': 'off',
      'better-tailwindcss/enforce-consistent-class-order': 'off',
      'better-tailwindcss/enforce-consistent-important-position': 'warn',
      'better-tailwindcss/enforce-consistent-line-wrapping': 'off',
      'better-tailwindcss/enforce-shorthand-classes': 'warn',
      'better-tailwindcss/no-conflicting-classes': 'warn',
      'better-tailwindcss/no-deprecated-classes': 'warn',
      'better-tailwindcss/no-duplicate-classes': 'warn',
      'better-tailwindcss/no-unnecessary-whitespace': 'warn',
      'better-tailwindcss/no-unregistered-classes': 'off',
    },
  },
]
