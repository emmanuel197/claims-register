import { useNavigate } from 'react-router-dom';
import { ArrowDown, ArrowUp, ArrowUpDown, Info } from 'lucide-react';
import { StatusBadge } from '../../components/ui/Badge.jsx';
import { Skeleton } from '../../components/ui/Feedback.jsx';
import { cn } from '../../utils/cn.js';
import { formatDate, formatMoney, isNegative } from '../../utils/format.js';

const COLUMNS = [
  { key: 'claim_number', label: 'Claim' },
  { key: 'policy_number', label: 'Policy' },
  { key: 'insured_name', label: 'Insured' },
  { key: 'loss_date', label: 'Loss date', sortable: true },
  { key: 'date_notified', label: 'Notified', sortable: true },
  { key: 'loss_nature_label', label: 'Nature' },
  { key: 'currency', label: 'Ccy' },
  { key: 'estimated_loss_amount', label: 'Estimated', num: true, sortable: true },
  { key: 'approved_amount', label: 'Approved', num: true },
  { key: 'total_paid', label: 'Paid', num: true },
  { key: 'outstanding_balance', label: 'Outstanding', num: true, sortable: true },
  { key: 'status', label: 'Status' },
];

function SortIcon({ active, desc }) {
  if (!active) return <ArrowUpDown className="h-3 w-3 text-neutral-300" aria-hidden="true" />;
  return desc ? <ArrowDown className="h-3 w-3" aria-hidden="true" /> : <ArrowUp className="h-3 w-3" aria-hidden="true" />;
}

function Money({ value, currency, className }) {
  return <span className={cn(isNegative(value) && 'text-error-text font-semibold', className)}>{formatMoney(value, currency)}</span>;
}

export default function ClaimsTable({ claims, totals, outflows, loading, ordering, onSort }) {
  const navigate = useNavigate();
  const desc = ordering?.startsWith('-');
  const activeKey = desc ? ordering.slice(1) : ordering;

  return (
    <div className="overflow-x-auto rounded-lg border border-neutral-200 bg-white shadow-sm">
      <table className="w-full min-w-[1080px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-neutral-200 bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">
            {COLUMNS.map((c) => (
              <th key={c.key} scope="col" className={cn('px-3 py-2.5 whitespace-nowrap', c.num && 'text-right')}>
                {c.sortable ? (
                  <button
                    type="button"
                    onClick={() => onSort(c.key)}
                    className={cn('inline-flex items-center gap-1 hover:text-neutral-800', activeKey === c.key && 'text-primary-700')}
                    aria-label={`Sort by ${c.label}`}
                  >
                    {c.label}
                    <SortIcon active={activeKey === c.key} desc={desc} />
                  </button>
                ) : (
                  c.label
                )}
              </th>
            ))}
          </tr>
        </thead>

        <tbody>
          {loading &&
            Array.from({ length: 8 }).map((_, i) => (
              <tr key={i} className="border-b border-neutral-100">
                {COLUMNS.map((c) => (
                  <td key={c.key} className="px-3 py-3">
                    <Skeleton className="h-4 w-full" />
                  </td>
                ))}
              </tr>
            ))}

          {!loading &&
            claims.map((c) => (
              <tr
                key={c.id}
                onClick={() => navigate(`/claims/${c.id}`)}
                onKeyDown={(e) => e.key === 'Enter' && navigate(`/claims/${c.id}`)}
                tabIndex={0}
                className="cursor-pointer border-b border-neutral-100 transition-colors hover:bg-primary-50/40 focus-visible:bg-primary-50/60 focus-visible:outline-none"
              >
                <td className="px-3 py-2.5 font-semibold text-primary-700 whitespace-nowrap">{c.claim_number}</td>
                <td className="px-3 py-2.5 font-mono text-xs text-neutral-600 whitespace-nowrap">{c.policy_number}</td>
                <td className="px-3 py-2.5 text-neutral-800 max-w-[220px] truncate" title={c.insured_name}>{c.insured_name}</td>
                <td className="px-3 py-2.5 num text-left text-neutral-700">{formatDate(c.loss_date)}</td>
                <td className="px-3 py-2.5 num text-left text-neutral-700">{formatDate(c.date_notified)}</td>
                <td className="px-3 py-2.5 text-neutral-700">{c.loss_nature_label}</td>
                <td className="px-3 py-2.5 font-semibold text-neutral-600">{c.currency}</td>
                <td className="px-3 py-2.5 num text-neutral-700">{formatMoney(c.estimated_loss_amount)}</td>
                <td className="px-3 py-2.5 num text-neutral-700">{formatMoney(c.approved_amount)}</td>
                <td className="px-3 py-2.5 num text-neutral-700">{formatMoney(c.total_paid)}</td>
                <td className="px-3 py-2.5 num font-medium text-neutral-900"><Money value={c.outstanding_balance} /></td>
                <td className="px-3 py-2.5 whitespace-nowrap"><StatusBadge status={c.status} short /></td>
              </tr>
            ))}
        </tbody>

        {!loading && totals.length > 0 && (
          <tfoot className="border-t-2 border-neutral-300 bg-neutral-50 font-semibold text-neutral-900">
            {totals.map((t) => (
              <tr key={t.currency} className="border-b border-neutral-100 last:border-0">
                <td colSpan={6} className="px-3 py-2.5 text-xs uppercase tracking-wider text-neutral-500">
                  Totals — {t.currency}{' '}
                  <span className="font-medium normal-case tracking-normal">
                    ({t.claims} claim{t.claims === 1 ? '' : 's'})
                  </span>
                </td>
                <td className="px-3 py-2.5 text-neutral-600">{t.currency}</td>
                <td className="px-3 py-2.5 num">{formatMoney(t.estimated_loss_amount)}</td>
                <td className="px-3 py-2.5 num">{formatMoney(t.approved_amount)}</td>
                <td className="px-3 py-2.5 num">
                  <span className="inline-flex items-center justify-end gap-1">
                    {formatMoney(t.total_paid)}
                    {Number(t.paid_on_reserved) !== 0 && (
                      <span
                        className="text-neutral-400"
                        title={`${formatMoney(t.paid_on_reserved, t.currency)} of this was paid on claims not yet approved, so it is not deducted from Outstanding.`}
                      >
                        <Info className="h-3.5 w-3.5" aria-label="Includes payments on reserved claims" />
                      </span>
                    )}
                  </span>
                </td>
                <td className="px-3 py-2.5 num">
                  <span className="inline-flex items-center justify-end gap-1">
                    <Money value={t.outstanding_balance} />
                    {Number(t.overpaid) !== 0 && (
                      <span className="text-neutral-400" title={`Includes ${formatMoney(t.overpaid, t.currency)} overpaid on settled claims (netted).`}>
                        <Info className="h-3.5 w-3.5" aria-label="Includes overpayments" />
                      </span>
                    )}
                  </span>
                </td>
                <td className="px-3 py-2.5" />
              </tr>
            ))}
            {outflows.length > 0 && (
              <tr className="bg-white">
                <td colSpan={COLUMNS.length} className="px-3 py-2 text-xs font-medium text-neutral-500">
                  Actually paid out, by payment currency:{' '}
                  {outflows.map((o, i) => (
                    <span key={o.currency} className="num inline">
                      {i > 0 && ' · '}
                      {formatMoney(o.amount, o.currency)}
                    </span>
                  ))}
                </td>
              </tr>
            )}
          </tfoot>
        )}
      </table>
    </div>
  );
}
