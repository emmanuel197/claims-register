import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Accessible dialog: Escape closes, Tab is trapped inside, focus returns to the opener on close. */
export default function Modal({ title, onClose, children, size = 'md' }) {
  const panel = useRef(null);

  useEffect(() => {
    const opener = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    // Focus the first field (skip the close button) once the panel has rendered.
    const focusables = () => Array.from(panel.current?.querySelectorAll(FOCUSABLE) ?? []);
    const first = focusables().find((el) => el.tagName !== 'BUTTON') || focusables()[0];
    first?.focus();

    const onKey = (e) => {
      if (e.key === 'Escape') return onClose?.();
      if (e.key !== 'Tab') return;
      const items = focusables();
      if (items.length === 0) return;
      const firstEl = items[0];
      const lastEl = items[items.length - 1];
      if (e.shiftKey && document.activeElement === firstEl) {
        e.preventDefault();
        lastEl.focus();
      } else if (!e.shiftKey && document.activeElement === lastEl) {
        e.preventDefault();
        firstEl.focus();
      }
    };
    document.addEventListener('keydown', onKey);

    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = previousOverflow;
      if (opener instanceof HTMLElement) opener.focus();
    };
  }, [onClose]);

  const width = size === 'lg' ? 'max-w-2xl' : 'max-w-md';

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-neutral-900/40 p-4 backdrop-blur-[2px] animate-fade-in"
      onMouseDown={(e) => e.target === e.currentTarget && onClose?.()}
    >
      <div ref={panel} role="dialog" aria-modal="true" aria-label={title} className={`my-8 w-full ${width} rounded-xl bg-white shadow-lg animate-scale-in`}>
        <div className="flex items-center justify-between border-b border-neutral-100 px-5 py-4">
          <h2 className="text-[15px] font-bold text-neutral-900">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close" className="flex h-8 w-8 items-center justify-center rounded-full text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}
