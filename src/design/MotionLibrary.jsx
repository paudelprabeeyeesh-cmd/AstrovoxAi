import { motion, AnimatePresence } from 'framer-motion'
import { useReducedMotion } from './DesignTokens'

export const MOTION_PRESETS = {
  fadeIn: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    exit: { opacity: 0 },
    transition: { duration: 0.2 }
  },
  slideUp: {
    initial: { opacity: 0, y: 10 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -10 },
    transition: { duration: 0.3, ease: 'easeOut' }
  },
  slideIn: {
    initial: { opacity: 0, x: -20 },
    animate: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: 20 },
    transition: { duration: 0.3, ease: 'easeOut' }
  },
  scaleIn: {
    initial: { opacity: 0, scale: 0.95 },
    animate: { opacity: 1, scale: 1 },
    exit: { opacity: 0, scale: 0.95 },
    transition: { duration: 0.2, ease: 'easeOut' }
  },
  bounceIn: {
    initial: { opacity: 0, scale: 0.3 },
    animate: { opacity: 1, scale: 1 },
    transition: { type: 'spring', stiffness: 300, damping: 20 }
  },
  stagger: {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    transition: { staggerChildren: 0.1, delayChildren: 0.2 }
  },
  pulse: {
    animate: { scale: [1, 1.05, 1] },
    transition: { duration: 2, repeat: Infinity, ease: 'easeInOut' }
  },
  typing: {
    initial: { width: 0 },
    animate: { width: '100%' },
    transition: { duration: 0.5, ease: 'easeOut' }
  }
}

export function AnimatedContainer({ children, preset = 'slideUp', className = '', respectReducedMotion = true, ...props }) {
  const reducedMotion = useReducedMotion()
  const motionPreset = MOTION_PRESETS[preset] || MOTION_PRESETS.slideUp

  const motionProps = respectReducedMotion && reducedMotion
    ? { initial: false, animate: { opacity: 1, x: 0, y: 0, scale: 1 }, transition: { duration: 0 } }
    : motionPreset

  return (
    <motion.div
      className={className}
      {...motionProps}
      {...props}
    >
      {children}
    </motion.div>
  )
}

export function AnimatedList({ children, preset = 'stagger', className = '', respectReducedMotion = true, ...props }) {
  const reducedMotion = useReducedMotion()
  const variants = MOTION_PRESETS[preset] || MOTION_PRESETS.stagger

  const motionProps = respectReducedMotion && reducedMotion
    ? { initial: false, animate: { opacity: 1, y: 0, x: 0, scale: 1 }, transition: { duration: 0 } }
    : variants

  return (
    <motion.div
      className={className}
      variants={motionProps}
      initial="initial"
      animate="animate"
      {...props}
    >
      {children}
    </motion.div>
  )
}

export function useAnimatedPresence() {
  const reducedMotion = useReducedMotion()
  return {
    mode: reducedMotion ? 'wait' : 'popLayout',
    initial: reducedMotion ? false : { opacity: 0, y: 10 },
    animate: { opacity: 1, y: 0 },
    exit: reducedMotion ? { opacity: 0 } : { opacity: 0, y: -10 }
  }
}

export { motion, AnimatePresence }
