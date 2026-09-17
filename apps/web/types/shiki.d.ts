declare module 'shiki' {
  export interface Highlighter {}
  export function createHighlighter(options: any): Promise<Highlighter>;
}
