import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Plus, Undo2 } from 'lucide-react';
import { createPayment, getClaim, getMeta, updateClaim } from '../api/claims.api.js';
import useApi from '../hooks/useApi.js';
import { StatusBadge } from '../components/ui/Badge.jsx';
import Button from '../components/ui/Button.jsx';
import Modal from '../components/ui/Modal.jsx';
import { Alert, EmptyState, Skeleton, SlowApiHint } from '../components/ui/Feedback.jsx';
import { useToast } from '../components/ui/Toast.jsx';
import ApproveForm from '../features/claims/ApproveForm.jsx';
import PaymentForm from '../features/claims/PaymentForm.jsx';
import { cn } from '../utils/cn.js';
import { formatDate, formatMoney, formatRate, isNegative } from '../utils/format.js';

function MoneyCell({ label, value, currency, emphasis = false }) {
  return (
    <div className="rounded-md bg-neutral-50 px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-wider text-neutral-500">{label}</p>
      <p className={cn('num mt-1 text-left text-lg font-bold', isNegative(value) ? 'text-error-text' : 'text-neutral-900', emphasis && 'text-xl')}>
        {formatMoney(value, currency)}
      </p>
    </div>
  );
}

function Fact({ label, value, mono = false }) {
  return (
    <div>
      <p className="text-xs text-neutral-500">{label}</p>
      <p className={cn('mt-0.5 text-sm font-medium text-neutral-800', mono && 'font-mono text-xs')}>{value || '—'}</p>
    </div>
  );
}

export default function ClaimDetailPage() {
  const { id } = useParams();
  const toast = useToast();
  const meta = useApi(getMeta, []);
  const claim = useApi(() => getClaim(id), [id]);
  const [modal, setModal] = useState(null); // null | { reverse?: payment }

  const c = claim.data;

  const handleApprove = async (payload) => {
    const updated = await updateClaim(id, payload);
    toast.success(`Approved amount set to ${formatMoney(updated.approved_amount, updated.currency)} — ${updated.status_label}.`);
    claim.reload();
  };

  const handlePayment = async (payload) => {
    const result = await createPayment(id, payload);
    const p = result.payment;
    const converted = p.currency !== result.claim.currency ? ` (= ${formatMoney(p.amount_in_claim_currency, result.claim.currency)})` : '';
    toast.success(`Recorded ${formatMoney(p.amount, p.currency)}${converted}. Outstanding: ${formatMoney(result.claim.outstanding_balance, result.claim.currency)}.`);
    setModal(null);
    claim.reload();
  };

  if (claim.error) {
    return (
      <div className="mx-auto max-w-3xl space-y-4">
        <Link to="/" className="inline-flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-800">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to claims
        </Link>
        <Alert title={claim.error.message === 'No Claim matches the given query.' ? 'Claim not found' : 'Could not load claim'}>{claim.error.message}</Alert>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-5 animate-fade-in">
      <Link to="/" className="inline-flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-800">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to claims
      </Link>

      {/* Header card */}
      <section className="rounded-lg border border-neutral-200 bg-white p-5 shadow-sm sm:p-6">
        {claim.loading || !c ? (
          <div className="space-y-4">
            <Skeleton className="h-7 w-64" />
            <Skeleton className="h-4 w-96" />
            <div className="grid gap-3 sm:grid-cols-4">
              {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-16" />)}
            </div>
            <SlowApiHint show={claim.slow} />
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex flex-wrap items-center gap-3">
                  <h1 className="text-2xl font-bold tracking-tight text-neutral-900">{c.claim_number}</h1>
                  <StatusBadge status={c.status} />
                </div>
                <p className="mt-1 text-sm text-neutral-600">
                  {c.insured_name} · policy <span className="font-mono text-xs">{c.policy_number}</span>
                </p>
              </div>
              <Button onClick={() => setModal({})}>
                <Plus className="h-4 w-4" aria-hidden="true" /> Record payment
              </Button>
            </div>

            <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <MoneyCell label="Estimated loss" value={c.estimated_loss_amount} currency={c.currency} />
              <MoneyCell label="Approved" value={c.approved_amount} currency={c.currency} />
              <MoneyCell label="Total paid" value={c.total_paid} currency={c.currency} />
              <MoneyCell label="Outstanding" value={c.outstanding_balance} currency={c.currency} emphasis />
            </div>

            <div className="mt-5 grid grid-cols-2 gap-4 border-t border-neutral-100 pt-5 sm:grid-cols-4">
              <Fact label="Loss date" value={formatDate(c.loss_date)} />
              <Fact label="Date notified" value={formatDate(c.date_notified)} />
              <Fact label="Nature of loss" value={c.loss_nature_label} />
              <Fact label="Reserve currency" value={c.currency} />
            </div>
          </>
        )}
      </section>

      {c && (
        <section className="rounded-lg border border-neutral-200 bg-white p-5 shadow-sm sm:p-6">
          <h2 className="text-base font-bold text-neutral-900">Settlement</h2>
          <p className="mb-4 mt-0.5 text-sm text-neutral-500">
            Status is derived: no approved amount → Reserved; balance above zero → payment outstanding; zero or below → paid.
          </p>
          <ApproveForm key={c.approved_amount ?? 'none'} claim={c} onSubmit={handleApprove} />
        </section>
      )}

      {c && (
        <section className="rounded-lg border border-neutral-200 bg-white shadow-sm">
          <div className="flex items-center justify-between px-5 py-4 sm:px-6">
            <div>
              <h2 className="text-base font-bold text-neutral-900">Payments</h2>
              <p className="mt-0.5 text-sm text-neutral-500">
                {c.payments.length === 0 ? 'No payments recorded yet.' : `${c.payments.length} payment${c.payments.length === 1 ? '' : 's'} · converted into ${c.currency} at the rate recorded on each payment.`}
              </p>
            </div>
          </div>

          {c.payments.length === 0 ? (
            <EmptyState
              title="Nothing paid against this claim"
              description="Payments can be recorded in any supported currency; each is converted into the claim currency at the rate you confirm."
              action={
                <Button variant="outline" onClick={() => setModal({})}>
                  <Plus className="h-4 w-4" aria-hidden="true" /> Record the first payment
                </Button>
              }
            />
          ) : (
            <div className="overflow-x-auto border-t border-neutral-100">
              <table className="w-full min-w-[720px] text-sm">
                <thead>
                  <tr className="bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">
                    <th className="px-5 py-2.5 sm:px-6">Date</th>
                    <th className="px-3 py-2.5 text-right">Amount paid</th>
                    <th className="px-3 py-2.5 text-right">Rate</th>
                    <th className="px-3 py-2.5 text-right">In {c.currency}</th>
                    <th className="px-3 py-2.5">Reference</th>
                    <th className="px-3 py-2.5" />
                  </tr>
                </thead>
                <tbody>
                  {c.payments.map((p) => (
                    <tr key={p.id} className="border-t border-neutral-100">
                      <td className="num px-5 py-2.5 text-left text-neutral-700 sm:px-6">{formatDate(p.payment_date)}</td>
                      <td className={cn('num px-3 py-2.5', isNegative(p.amount) ? 'text-error-text font-semibold' : 'text-neutral-800')}>
                        {formatMoney(p.amount, p.currency)}
                      </td>
                      <td className="num px-3 py-2.5 text-neutral-500">
                        {p.currency === c.currency ? '—' : `1 ${p.currency} = ${formatRate(p.exchange_rate)} ${c.currency}`}
                      </td>
                      <td className={cn('num px-3 py-2.5 font-medium', isNegative(p.amount_in_claim_currency) ? 'text-error-text' : 'text-neutral-900')}>
                        {formatMoney(p.amount_in_claim_currency)}
                      </td>
                      <td className="px-3 py-2.5 text-neutral-600">{p.reference || <span className="text-neutral-300">—</span>}</td>
                      <td className="px-3 py-2.5 text-right">
                        <Button variant="ghost" size="sm" title="Record a reversing payment at the same rate" onClick={() => setModal({ reverse: p })}>
                          <Undo2 className="h-3.5 w-3.5" aria-hidden="true" /> Reverse
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="border-t-2 border-neutral-300 bg-neutral-50 font-semibold text-neutral-900">
                  <tr>
                    <td colSpan={3} className="px-5 py-2.5 text-xs uppercase tracking-wider text-neutral-500 sm:px-6">Total paid</td>
                    <td className={cn('num px-3 py-2.5', isNegative(c.total_paid) && 'text-error-text')}>{formatMoney(c.total_paid)}</td>
                    <td colSpan={2} />
                  </tr>
                </tfoot>
              </table>
            </div>
          )}
        </section>
      )}

      {modal && c && (
        <Modal title={modal.reverse ? `Reverse payment of ${formatMoney(modal.reverse.amount, modal.reverse.currency)}` : `Record payment · ${c.claim_number}`} onClose={() => setModal(null)} size="lg">
          <PaymentForm
            claim={c}
            meta={meta.data}
            initial={
              modal.reverse
                ? {
                    amount: String(-Number(modal.reverse.amount)),
                    currency: modal.reverse.currency,
                    exchange_rate: modal.reverse.exchange_rate,
                    reference: `Reversal of payment #${modal.reverse.id}`,
                  }
                : null
            }
            onSubmit={handlePayment}
            onCancel={() => setModal(null)}
          />
        </Modal>
      )}
    </div>
  );
}
