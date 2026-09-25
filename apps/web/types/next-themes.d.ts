declare module 'next-themes' {
  export interface ThemeProviderProps {
    children: React.ReactNode;
    attribute?: string;
    defaultTheme?: string;
    enableSystem?: boolean;
    disableTransitionOnChange?: boolean;
    storageKey?: string;
  }
  export function ThemeProvider(props: ThemeProviderProps): React.ReactElement;
  export function useTheme(): { theme?: string; setTheme: (theme: string) => void };
}
