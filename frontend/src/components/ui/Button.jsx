import { Link } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { cn } from '../../utils/cn.js';

const base =
  'inline-flex items-center justify-center gap-2 font-semibold rounded-md transition-all duration-150 ' +
  'active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 ' +
  'disabled:pointer-events-none disabled:opacity-50 select-none whitespace-nowrap';

const variants = {
  primary: 'bg-primary-500 text-white shadow-sm hover:bg-primary-600 focus-visible:ring-primary-300',
  secondary: 'bg-primary-50 text-primary-700 hover:bg-primary-100 focus-visible:ring-primary-200',
  outline: 'border border-neutral-200 bg-white text-neutral-700 shadow-sm hover:bg-neutral-50 hover:border-neutral-300 focus-visible:ring-neutral-200',
  ghost: 'bg-transparent text-neutral-600 hover:bg-neutral-100 focus-visible:ring-neutral-200',
  danger: 'bg-error text-white shadow-sm hover:bg-error-text focus-visible:ring-error',
};

const sizes = {
  sm: 'h-8 px-3 text-[13px]',
  default: 'h-10 px-4 text-sm',
  lg: 'h-11 px-5 text-[15px]',
};

/** Button, or a router Link styled as one when `to` is given (avoids nesting <a> and <button>). */
export default function Button({ variant = 'primary', size = 'default', loading = false, to, className, children, ...props }) {
  const classes = cn(base, variants[variant], sizes[size], className);
  if (to) {
    return (
      <Link to={to} className={classes} {...props}>
        {children}
      </Link>
    );
  }
  return (
    <button className={classes} disabled={props.disabled || loading} {...props}>
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
      {children}
    </button>
  );
}
