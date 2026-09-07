import { cn } from '@/lib/utils'
import { cva, type VariantProps } from 'class-variance-authority'
import { HTMLAttributes } from 'react'

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border',
  {
    variants: {
      variant: {
        default: 'bg-[#FFF0E5] text-muted border-[#F2E7DE]',
        pending: 'bg-[#FFFCFA] text-muted border-card-border',
        scored: 'bg-blue-50 text-blue-700 border-blue-200',
        ready: 'bg-cyan-50 text-cyan-700 border-cyan-200',
        approved: 'bg-amber-50 text-amber-700 border-amber-200',
        skipped: 'bg-[#FFFCFA] text-muted border-card-border',
        sent: 'bg-green-50 text-green-700 border-green-200',
        replied: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        resume_sent: 'bg-purple-50 text-purple-700 border-purple-200',
        needs_resume: 'bg-yellow-50 text-yellow-700 border-yellow-200',
        follow_up_sent: 'bg-sky-50 text-sky-700 border-sky-200',
        reply_pending: 'bg-amber-50 text-amber-700 border-amber-200',
        auto_replied: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        rejected: 'bg-red-50 text-red-700 border-red-200',
        error: 'bg-red-50 text-red-700 border-red-200',
        filtered: 'bg-[#FFFCFA] text-muted border-card-border',
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
