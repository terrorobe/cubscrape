declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

// Global type declarations for libraries
declare module 'sql.js' {
  export interface Database {
    exec(sql: string, params?: any[]): QueryExecResult[]
    close(): void
  }

  export interface QueryExecResult {
    columns: string[]
    values: any[][]
  }

  export default function initSqlJs(config?: any): Promise<{
    Database: new (data?: Uint8Array) => Database
  }>
}

// Vite-specific type declarations
interface ImportMetaEnv {
  readonly DEV: boolean
  readonly PROD: boolean
  readonly MODE: string
  readonly BASE_URL: string
  readonly VITE_APP_TITLE?: string
  // Add other environment variables as needed
}

interface ImportMeta {
  readonly env: ImportMetaEnv
  readonly hot?: {
    accept(): void
    accept(cb: (mod: any) => void): void
    accept(deps: string[], cb: (mods: any[]) => void): void
    dispose(cb: () => void): void
    decline(): void
    invalidate(): void
    on(event: string, cb: (...args: any[]) => void): void
    off(event: string, cb: (...args: any[]) => void): void
    send(event: string, data?: any): void
  }
}
