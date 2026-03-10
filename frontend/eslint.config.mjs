import js from '@eslint/js'
import typescript from '@typescript-eslint/eslint-plugin'
import typescriptParser from '@typescript-eslint/parser'
import react from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import globals from 'globals'

export default [
  // Global ignores
  {
    ignores: ['dist', 'dev-dist', 'node_modules', 'build', '.vite', 'coverage', 'cypress/**', '**/*.d.ts']
  },
  
  // Node.js JavaScript config files (.js files)
  {
    files: [
      'tailwind.config.js',
      'postcss.config.js',
      'cypress.config.js',
      'jest.config.js',
      '**/*.config.js',
      'scripts/**/*.js'
    ],
    languageOptions: {
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module'
      },
      globals: {
        ...globals.node
      }
    },
    plugins: {
      '@typescript-eslint': typescript
    },
    rules: {
      ...js.configs.recommended.rules,
      'no-undef': 'off', // Node.js globals are provided via globals.node
      'no-console': 'off',
      'no-unused-vars': 'off',
      '@typescript-eslint/no-require-imports': 'off' // Allow require() in Node.js .js files
    }
  },
  
  // Node.js TypeScript config files (.ts files)
  {
    files: [
      'vite.config.mts',
      'vitest.config.ts', 
      'playwright.config.ts',
      '**/*.config.ts',
      'scripts/**/*.ts'
    ],
    languageOptions: {
      parser: typescriptParser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module'
      },
      globals: {
        ...globals.node
      }
    },
    rules: {
      ...js.configs.recommended.rules,
      'no-undef': 'off', // Node.js globals are provided via globals.node
      'no-console': 'off',
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-require-imports': 'off', // Allow require() in Node.js files
      'no-unused-vars': 'off',
      '@typescript-eslint/no-unused-vars': 'off'
    }
  },
  
  // TypeScript/TSX source files (browser environment)
  {
    files: ['**/*.{ts,tsx}', '!**/*.config.{ts,tsx}', '!**/node_modules/**', '!**/dist/**'],
    ignores: ['scripts/**'],
    languageOptions: {
      parser: typescriptParser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        ecmaFeatures: {
          jsx: true
        }
      },
      globals: {
        ...globals.browser,
        ...globals.es2021
      }
    },
    plugins: {
      '@typescript-eslint': typescript,
      'react': react,
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh
    },
    settings: {
      react: {
        version: 'detect'
      }
    },
    rules: {
      // Disable base JS rules that TypeScript handles
      'no-undef': 'off', // TypeScript handles this
      'no-unused-vars': 'off', // TypeScript handles this via @typescript-eslint/no-unused-vars
      
      // TypeScript rules
      ...typescript.configs.recommended.rules,
      '@typescript-eslint/no-require-imports': 'off', // Allow require() in Node.js files (shouldn't apply to browser files, but disable to be safe)
      '@typescript-eslint/no-unused-vars': 'off',
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/explicit-function-return-type': 'off',
      '@typescript-eslint/explicit-module-boundary-types': 'off',
      
      // React rules
      ...react.configs.recommended.rules,
      'react/prop-types': 'off',
      'react/react-in-jsx-scope': 'off',
      'react/no-unescaped-entities': 'off', // Allow quotes/apostrophes in JSX text
      'react/no-unknown-property': ['error', { 
        ignore: [
          'geometry', 'material', 'position', 'rotation', 'scale', 
          'args', 'attach', 'castShadow', 'receiveShadow', 'visible',
          'color', 'intensity', 'distance', 'decay', 'angle', 'penumbra',
          'vertexColors', 'transparent', 'opacity', 'wireframe', 'side'
        ] 
      }], // Allow Three.js and other 3D library props
      'react/display-name': 'off', // Allow anonymous components (common with arrow functions)
      'react-refresh/only-export-components': 'off',
      
      // General rules
      'no-console': 'off',
      'prefer-const': 'error',
      'no-var': 'error'
    }
  }
]
