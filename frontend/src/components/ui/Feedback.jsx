import { AlertCircle, Inbox } from 'lucide-react';
import { cn } from '../../utils/cn.js';

export function Alert({ variant = 'error', title, children, className }) {
  const styles = {
    error: 'border-error/30 bg-error-bg text-error-text',
    info: 'border-info/30 bg-info-bg text-info-text',
    warning: 'border-warning/30 bg-warning-bg text-warning-text',
  };
  return (
    <div role="alert" className={cn('flex gap-3 rounded-lg border p-3.5 text-sm', styles[variant], className)}>
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <div>
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className={title ? 'mt-0.5' : ''}>{children}</div>}
      </div>
    </div>
  );
}

export function EmptyState({ title, description, action, icon: Icon = Inbox }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-16 text-center animate-fade-in">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-neutral-100">
        <Icon className="h-7 w-7 text-neutral-400" aria-hidden="true" />
      </div>
      <p className="font-semibold text-neutral-700">{title}</p>
      {description && <p className="mt-1.5 max-w-sm text-sm text-neutral-500">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function Skeleton({ className }) {
  return <div className={cn('animate-shimmer rounded-md', className)} aria-hidden="true" />;
}

export function SlowApiHint({ show }) {
  if (!show) return null;
  return (
    <p className="mt-3 text-center text-xs text-neutral-500 animate-fade-in">
      Waking the API — it runs on a free tier and sleeps when idle. This can take up to a minute the first time.
    </p>
  );
}
