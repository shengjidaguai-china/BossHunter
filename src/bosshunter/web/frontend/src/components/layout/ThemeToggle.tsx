import { Monitor, Moon, Sun } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useTheme, type ThemeMode } from '@/hooks/useTheme'

const OPTIONS: { value: ThemeMode; label: string; Icon: typeof Sun }[] = [
  { value: 'light', label: '浅色', Icon: Sun },
  { value: 'dark', label: '深色', Icon: Moon },
  { value: 'system', label: '跟随系统', Icon: Monitor },
]

export function ThemeToggle() {
  const { mode, setMode } = useTheme()

  return (
    <div
      role="group"
      aria-label="主题切换"
      className="flex items-center gap-0.5 rounded-full border border-card-border bg-secondary p-0.5"
    >
      {OPTIONS.map(({ value, label, Icon }) => (
        <button
          key={value}
          type="button"
          onClick={() => setMode(value)}
          title={label}
          aria-label={label}
          aria-pressed={mode === value}
          className={cn(
            'rounded-full p-1.5 transition-colors',
            mode === value
              ? 'bg-card text-primary shadow-sm'
              : 'text-muted hover:text-foreground'
          )}
        >
          <Icon className="h-3.5 w-3.5" />
        </button>
      ))}
    </div>
  )
}
