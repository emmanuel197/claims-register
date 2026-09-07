import { forwardRef, useId } from 'react';
import { cn } from '../../utils/cn.js';

const controlBase =
  'w-full rounded-md border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 ' +
  'placeholder:text-neutral-400 outline-none transition-all duration-150 hover:border-neutral-300 ' +
  'focus:border-primary-400 focus:ring-[3px] focus:ring-primary-100 disabled:bg-neutral-50 disabled:text-neutral-500';

const errorClasses = 'border-error bg-error-bg focus:border-error focus:ring-error/20';

const chevron =
  'appearance-none pr-8 bg-no-repeat bg-[length:16px] bg-[right_10px_center] ' +
  "bg-[url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E\")]";

function Wrapper({ id, label, required, helper, error, children }) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={id} className="text-[13px] font-semibold text-neutral-700">
          {label}
          {required && <span className="ml-0.5 text-error" aria-hidden="true">*</span>}
        </label>
      )}
      {children}
      {error && <p id={`${id}-error`} role="alert" className="text-xs text-error-text">{error}</p>}
      {!error && helper && <p id={`${id}-helper`} className="text-xs text-neutral-500">{helper}</p>}
    </div>
  );
}

export const Input = forwardRef(function Input({ label, required, helper, error, prefix, className, id, ...props }, ref) {
  const autoId = useId();
  const inputId = id || autoId;
  return (
    <Wrapper id={inputId} label={label} required={required} helper={helper} error={error}>
      <div className="relative">
        {prefix && (
          <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-xs font-semibold text-neutral-500">
            {prefix}
          </span>
        )}
        <input
          ref={ref}
          id={inputId}
          aria-invalid={!!error}
          aria-describedby={error ? `${inputId}-error` : helper ? `${inputId}-helper` : undefined}
          className={cn(controlBase, prefix && 'pl-12', error && errorClasses, className)}
          {...props}
        />
      </div>
    </Wrapper>
  );
});

export function Select({ label, required, helper, error, className, id, options = [], placeholder, ...props }) {
  const autoId = useId();
  const selectId = id || autoId;
  return (
    <Wrapper id={selectId} label={label} required={required} helper={helper} error={error}>
      <select
        id={selectId}
        aria-invalid={!!error}
        className={cn(controlBase, chevron, error && errorClasses, className)}
        {...props}
      >
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </Wrapper>
  );
}

/** Money input: decimal keyboard, up to 2 dp, currency code as a prefix. */
export const MoneyInput = forwardRef(function MoneyInput({ currency, className, ...props }, ref) {
  return (
    <Input
      ref={ref}
      type="text"
      inputMode="decimal"
      pattern="^-?\d+(\.\d{1,2})?$"
      placeholder="0.00"
      prefix={currency}
      className={cn('num', className)}
      {...props}
    />
  );
});
