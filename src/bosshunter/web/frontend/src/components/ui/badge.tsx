import { cn } from '@/lib/utils'
import { cva, type VariantProps } from 'class-variance-authority'
import { HTMLAttributes } from 'react'

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border',
  {
    variants: {
      variant: {
        default: 'bg-secondary text-muted border-card-border',
        pending: 'bg-surface text-muted border-card-border',
        scored: 'bg-info-soft text-info border-info-border',
        ready: 'bg-cyan-soft text-cyan border-cyan-border',
        approved: 'bg-warning-soft text-warning border-warning-border',
        skipped: 'bg-surface text-muted border-card-border',
        sent: 'bg-success-soft text-success border-success-border',
        replied: 'bg-success-soft text-success border-success-border',
        resume_sent: 'bg-purple-soft text-purple border-purple-border',
        needs_resume: 'bg-warning-soft text-warning-strong border-warning-border',
        follow_up_sent: 'bg-sky-soft text-sky border-sky-border',
        reply_pending: 'bg-warning-soft text-warning border-warning-border',
        auto_replied: 'bg-success-soft text-success border-success-border',
        rejected: 'bg-danger-soft text-danger-strong border-danger-border',
        error: 'bg-danger-soft text-danger-strong border-danger-border',
        filtered: 'bg-surface text-muted border-card-border',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
)

export interface BadgeProps extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}
