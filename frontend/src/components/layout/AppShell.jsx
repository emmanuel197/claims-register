import { Link, NavLink } from 'react-router-dom';
import { FileText, Plus } from 'lucide-react';
import { cn } from '../../utils/cn.js';

export default function AppShell({ children }) {
  return (
    <div className="flex min-h-svh flex-col">
      <header className="sticky top-0 z-30 border-b border-neutral-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-14 w-full max-w-7xl items-center justify-between px-4 sm:px-6">
          <Link to="/" className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-500 text-white">
              <FileText className="h-4 w-4" aria-hidden="true" />
            </span>
            <span className="text-[15px] font-bold tracking-tight text-neutral-900">Claims Register</span>
          </Link>
          <nav className="flex items-center gap-1">
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                cn('rounded-md px-3 py-1.5 text-sm font-medium', isActive ? 'bg-neutral-100 text-neutral-900' : 'text-neutral-600 hover:bg-neutral-50')
              }
            >
              Claims
            </NavLink>
            <NavLink
              to="/claims/new"
              className={({ isActive }) =>
                cn(
                  'inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-semibold',
                  isActive ? 'bg-primary-600 text-white' : 'bg-primary-500 text-white hover:bg-primary-600'
                )
              }
            >
              <Plus className="h-4 w-4" aria-hidden="true" />
              New claim
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6">{children}</main>
      <footer className="border-t border-neutral-200 py-4 text-center text-xs text-neutral-400">
        Mini claims register · money is computed server-side in the claim’s currency
      </footer>
    </div>
  );
}
