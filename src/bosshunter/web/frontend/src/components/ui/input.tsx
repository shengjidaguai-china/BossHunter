import { cn } from '@/lib/utils'
import { forwardRef, InputHTMLAttributes } from 'react'

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      className={cn(
        'flex h-9 w-full rounded-md border border-card-border bg-card px-3 py-1 text-sm text-foreground placeholder:text-muted/60 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary disabled:cursor-not-allowed disabled:bg-surface disabled:text-muted',
        className
      )}
      ref={ref}
      {...props}
    />
  )
)
Input.displayName = 'Input'
