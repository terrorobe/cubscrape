import js from '@eslint/js'
import vue from 'eslint-plugin-vue'
import * as vueParser from 'vue-eslint-parser'
import prettier from 'eslint-plugin-prettier'
import prettierConfig from 'eslint-config-prettier'
import betterTailwind from 'eslint-plugin-better-tailwindcss'
import typescript from '@typescript-eslint/eslint-plugin'
import typescriptParser from '@typescript-eslint/parser'
import globals from 'globals'

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
        ...globals.browser,
        ...globals.es2021,
        ...globals.node,
      },
    },
    rules: {
      // Prettier integration
      'prettier/prettier': 'error',

      // General JavaScript rules
      'no-console': 'warn',
      'no-debugger': 'error',
      'no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      'prefer-const': 'error',
      'no-var': 'error',

      // Modern JavaScript best practices
      'object-shorthand': 'error',
      'prefer-destructuring': ['error', { array: false, object: true }],
      'prefer-template': 'error',
      'prefer-arrow-callback': 'error',
      'arrow-body-style': ['error', 'as-needed'],

      // Code quality
      eqeqeq: ['error', 'always', { null: 'ignore' }],
      curly: 'error',
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'no-trailing-spaces': 'error',
      'no-multiple-empty-lines': ['error', { max: 1, maxEOF: 0 }],
      'no-irregular-whitespace': 'error',
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
        tsconfigRootDir: import.meta.dirname,
      },
      globals: {
        ...globals.browser,
        ...globals.es2021,
        ...globals.node,
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
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      '@typescript-eslint/no-redeclare': 'error',
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/explicit-function-return-type': 'off',
      '@typescript-eslint/explicit-module-boundary-types': 'off',
      '@typescript-eslint/no-non-null-assertion': 'warn',
      '@typescript-eslint/no-var-requires': 'error',

      // Additional TypeScript best practices
      '@typescript-eslint/prefer-nullish-coalescing': 'error',
      '@typescript-eslint/prefer-optional-chain': 'error',
      '@typescript-eslint/no-unnecessary-type-assertion': 'error',
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/await-thenable': 'error',
      '@typescript-eslint/no-misused-promises': 'error',
      '@typescript-eslint/prefer-as-const': 'error',

      // Code quality
      eqeqeq: ['error', 'always', { null: 'ignore' }],
      curly: 'error',
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'no-trailing-spaces': 'error',
      'no-console': 'warn',
      'no-debugger': 'error',
      'no-multiple-empty-lines': ['error', { max: 1, maxEOF: 0 }],
      'no-irregular-whitespace': 'error',

      // Modern JavaScript best practices
      'object-shorthand': 'error',
      'prefer-destructuring': ['error', { array: false, object: true }],
      'prefer-template': 'error',
      'prefer-arrow-callback': 'error',
      'arrow-body-style': ['error', 'as-needed'],
    },
  },

  // CLI Scripts - allow console statements
  {
    files: ['scripts/**/*.js'],
    rules: {
      'no-console': 'off', // CLI scripts need console output
    },
  },

  // Debug utility - allow console statements
  {
    files: ['src/utils/debug.ts'],
    rules: {
      'no-console': 'off', // Debug utility wraps console methods
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
        parser: {
          // Script parser for `<script>` blocks
          js: 'espree',
          ts: typescriptParser,
          '<template>': 'espree',
        },
        extraFileExtensions: ['.vue'],
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: {
        ...globals.browser,
        ...globals.es2021,
        ...globals.node,
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

      // Vue 3 Composition API specific rules
      'vue/multi-word-component-names': 'off',
      'vue/no-unused-vars': 'error',
      'vue/no-multiple-template-root': 'off', // Vue 3 allows multiple roots
      'vue/max-attributes-per-line': 'off', // Handled by Prettier
      'vue/singleline-html-element-content-newline': 'off', // Handled by Prettier
      'vue/html-self-closing': 'off', // Handled by Prettier
      'vue/attributes-order': 'off', // Personal preference

      // Enhanced Vue 3 rules (available in eslint-plugin-vue)
      'vue/prefer-import-from-vue': 'error',
      'vue/prefer-separate-static-class': 'error',
      'vue/prefer-true-attribute-shorthand': 'error',
      'vue/component-name-in-template-casing': ['error', 'PascalCase'],
      'vue/component-definition-name-casing': ['error', 'PascalCase'],
      'vue/custom-event-name-casing': ['error', 'camelCase'],
      'vue/no-empty-component-block': 'error',
      'vue/no-template-target-blank': 'error',
      'vue/no-useless-mustaches': 'error',
      'vue/no-useless-v-bind': 'error',
      'vue/padding-line-between-blocks': 'error',
      'vue/prefer-template': 'error',
      'vue/block-order': ['error', { order: ['script', 'template', 'style'] }],

      // Disable base ESLint rules that conflict with TypeScript
      'no-unused-vars': 'off',
      'no-undef': 'off',
      'no-redeclare': 'off', // TypeScript handles function overloads

      // TypeScript rules for Vue files
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      '@typescript-eslint/no-redeclare': 'error',
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/explicit-function-return-type': 'off',
      '@typescript-eslint/explicit-module-boundary-types': 'off',
      '@typescript-eslint/no-non-null-assertion': 'warn',
      '@typescript-eslint/prefer-as-const': 'error',
      '@typescript-eslint/no-var-requires': 'error',

      // Code quality
      'no-console': 'warn',
      'no-debugger': 'error',
      'prefer-const': 'error',
      'no-var': 'error',
      eqeqeq: ['error', 'always', { null: 'ignore' }],
      curly: 'error',
      'no-eval': 'error',
      'no-implied-eval': 'error',
      'no-trailing-spaces': 'error',
      'no-multiple-empty-lines': ['error', { max: 1, maxEOF: 0 }],
      'no-irregular-whitespace': 'error',

      // Modern JavaScript best practices
      'object-shorthand': 'error',
      'prefer-destructuring': ['error', { array: false, object: true }],
      'prefer-template': 'error',
      'prefer-arrow-callback': 'error',
      'arrow-body-style': ['error', 'as-needed'],

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
