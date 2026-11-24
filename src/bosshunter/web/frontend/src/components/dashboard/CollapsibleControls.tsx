import { useEffect, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface CollapsibleToggleButtonProps {
  sectionName: string
  collapsed: boolean
  controlsId: string
  onToggle: () => void
}

/**
 * Accessible collapse/expand toggle button whose visible text and aria-expanded
 * state stay synchronized across all collapsible dashboard sections.
 */
export function CollapsibleToggleButton({
  sectionName,
  collapsed,
  controlsId,
  onToggle,
}: CollapsibleToggleButtonProps) {
  const actionText = collapsed ? '展开' : '折叠'
  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      aria-expanded={!collapsed}
      aria-controls={controlsId}
      aria-label={`${actionText}${sectionName}`}
      onClick={onToggle}
      className="gap-1 text-xs"
    >
      <span>{actionText}</span>
      <ChevronDown
        aria-hidden="true"
        className={`h-3.5 w-3.5 shrink-0 motion-safe:transition-transform motion-safe:duration-200 ${collapsed ? '' : 'rotate-180'}`}
      />
    </Button>
  )
}

/** Track a CSS media query match state for responsive row calculations. */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() =>
    typeof window !== 'undefined' && typeof window.matchMedia === 'function'
      ? window.matchMedia(query).matches
      : false
  )

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return
    const mql = window.matchMedia(query)
    setMatches(mql.matches)
    const handler = (event: MediaQueryListEvent) => setMatches(event.matches)
    mql.addEventListener('change', handler)
    return () => mql.removeEventListener('change', handler)
  }, [query])

  return matches
}
