declare module 'remark-math' {
  import { Plugin } from 'unified'
  const remarkMath: Plugin
  export default remarkMath
}

declare module 'rehype-katex' {
  import { Plugin } from 'unified'
  const rehypeKatex: Plugin
  export default rehypeKatex
}

declare module 'mermaid' {
  export interface MermaidConfig {
    startOnLoad?: boolean
    theme?: string
    securityLevel?: string
    [key: string]: unknown
  }

  export function initialize(config?: MermaidConfig): void
  export function render(id: string, code: string): Promise<{ svg: string }>
  export default mermaid
}
