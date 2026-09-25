import { useEffect, useState } from 'react'

type Breakpoint = 'sm' | 'md' | 'lg' | 'xl' | '2xl'

const breakpointMap: Record<Breakpoint, number> = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
}

export function useMediaQuery(breakpoint: Breakpoint) {
  const [matches, setMatches] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth >= breakpointMap[breakpoint] : false
  )

  useEffect(() => {
    if (typeof window === 'undefined') return

    const mql = window.matchMedia(`(min-width: ${breakpointMap[breakpoint]}px)`)
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches)

    setMatches(mql.matches)
    mql.addEventListener('change', handler)

    return () => mql.removeEventListener('change', handler)
  }, [breakpoint])

  return matches
}

export function useBreakpoints() {
  const isSm = useMediaQuery('sm')
  const isMd = useMediaQuery('md')
  const isLg = useMediaQuery('lg')
  const isXl = useMediaQuery('xl')
  const is2Xl = useMediaQuery('2xl')

  return {
    isSm,
    isMd,
    isLg,
    isXl,
    is2Xl,
    isMobile: !isMd,
    isTablet: isMd && !isLg,
    isDesktop: isLg,
  }
}
