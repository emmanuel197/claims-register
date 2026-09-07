import { cn } from '../../utils/cn.js';
import { STATUS } from '../../utils/statuses.js';

const variants = {
  success: 'bg-success-bg text-success-text',
  warning: 'bg-warning-bg text-warning-text',
  error: 'bg-error-bg text-error-text',
  info: 'bg-info-bg text-info-text',
  neutral: 'bg-neutral-100 text-neutral-600',
};

const dots = {
  success: 'bg-success',
  warning: 'bg-warning',
  error: 'bg-error',
  info: 'bg-info',
  neutral: 'bg-neutral-400',
};

export function Badge({ variant = 'neutral', dot = false, className, children }) {
  return (
    <span className={cn('inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold', variants[variant], className)}>
      {dot && <span className={cn('h-1.5 w-1.5 rounded-full', dots[variant])} aria-hidden="true" />}
      {children}
    </span>
  );
}

export function StatusBadge({ status, short = false }) {
  const s = STATUS[status] || { label: status, short: status, variant: 'neutral' };
  return (
    <Badge variant={s.variant} dot>
      {short ? s.short : s.label}
    </Badge>
  );
}
