declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const component: DefineComponent<{}, {}, any>
  export default component
}

// Global type declarations for libraries
declare module 'sql.js' {
  export interface Database {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    exec(sql: string, params?: any[]): QueryExecResult[]
    close(): void
  }

  export interface QueryExecResult {
    columns: string[]
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    values: any[][]
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
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
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    accept(cb: (mod: any) => void): void
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    accept(deps: string[], cb: (mods: any[]) => void): void
    dispose(cb: () => void): void
    decline(): void
    invalidate(): void
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    on(event: string, cb: (...args: any[]) => void): void
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    off(event: string, cb: (...args: any[]) => void): void
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    send(event: string, data?: any): void
  }
}
