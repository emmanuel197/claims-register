import { useEffect, useMemo, useState } from 'react';
import { Input, MoneyInput, Select } from '../../components/forms/Field.jsx';
import Button from '../../components/ui/Button.jsx';
import { Alert } from '../../components/ui/Feedback.jsx';
import { parseApiError } from '../../api/client.js';
import { formatMoney, previewConversion, todayIso } from '../../utils/format.js';
import { indicativeRate } from '../../utils/statuses.js';

/**
 * Record a payment against a claim. When the payment currency differs from the
 * claim currency an exchange rate is required; we prefill an *indicative* rate
 * from /api/meta/ and the user confirms or edits it. `initial` supports the
 * "Reverse" action (negated amount, same currency and rate).
 */
export default function PaymentForm({ claim, meta, initial, onSubmit, onCancel }) {
  const [form, setForm] = useState({
    payment_date: initial?.payment_date ?? todayIso(),
    amount: initial?.amount ?? '',
    currency: initial?.currency ?? claim.currency,
    exchange_rate: initial?.exchange_rate ?? '',
    reference: initial?.reference ?? '',
  });
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState(null);
  const [saving, setSaving] = useState(false);

  const crossCurrency = form.currency !== claim.currency;
  const rates = meta?.indicative_rates;

  // Prefill the indicative rate whenever the currency pair changes (unless reversing).
  useEffect(() => {
    if (initial) return;
    setForm((f) => ({ ...f, exchange_rate: crossCurrency ? indicativeRate(rates?.in_ghs, f.currency, claim.currency) : '' }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.currency, claim.currency, rates]);

  const preview = useMemo(
    () => (crossCurrency ? previewConversion(form.amount, form.exchange_rate) : previewConversion(form.amount, 1)),
    [form.amount, form.exchange_rate, crossCurrency]
  );

  const set = (key) => (e) => {
    setForm((f) => ({ ...f, [key]: e.target.value }));
    setErrors((er) => ({ ...er, [key]: undefined }));
  };

  const validate = () => {
    const e = {};
    if (!form.payment_date) e.payment_date = 'Payment date is required.';
    else if (form.payment_date < claim.loss_date) e.payment_date = `Cannot be before the loss date (${claim.loss_date}).`;
    const amount = Number(form.amount);
    if (!form.amount || Number.isNaN(amount)) e.amount = 'Enter an amount.';
    else if (amount === 0) e.amount = 'Amount cannot be zero.';
    if (crossCurrency && !(Number(form.exchange_rate) > 0)) e.exchange_rate = 'Enter a rate greater than zero.';
    return e;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const e = validate();
    if (Object.keys(e).length) return setErrors(e);
    setSaving(true);
    setMessage(null);
    try {
      const payload = {
        payment_date: form.payment_date,
        amount: form.amount,
        currency: form.currency,
        reference: form.reference.trim(),
      };
      if (crossCurrency) payload.exchange_rate = form.exchange_rate;
      await onSubmit(payload);
    } catch (err) {
      const parsed = parseApiError(err);
      setErrors(parsed.fields);
      setMessage(parsed.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      {message && <Alert>{message}</Alert>}

      <div className="grid gap-4 sm:grid-cols-2">
        <Input label="Payment date" required type="date" min={claim.loss_date} max={todayIso()} value={form.payment_date} onChange={set('payment_date')} error={errors.payment_date} />
        <Select label="Paid in" required options={meta?.currencies ?? [{ value: claim.currency, label: claim.currency }]} value={form.currency} onChange={set('currency')} error={errors.currency} disabled={!!initial} />
        <MoneyInput label="Amount paid" required currency={form.currency} value={form.amount} onChange={set('amount')} error={errors.amount} helper="Negative amounts reverse an earlier payment" />
        {crossCurrency && (
          <Input
            label={`Exchange rate — 1 ${form.currency} = ? ${claim.currency}`}
            required
            type="text"
            inputMode="decimal"
            className="num"
            value={form.exchange_rate}
            onChange={set('exchange_rate')}
            error={errors.exchange_rate}
            disabled={!!initial}
            helper={
              initial
                ? 'Reversals reuse the original rate so the pair nets to zero.'
                : rates
                  ? `Prefilled from indicative rates as of ${rates.as_of} — confirm or edit before saving.`
                  : 'Rate used to convert into the claim currency.'
            }
          />
        )}
        <div className={crossCurrency ? 'sm:col-span-2' : ''}>
          <Input label="Reference" value={form.reference} onChange={set('reference')} error={errors.reference} maxLength={120} placeholder="Optional — invoice, payee, note" />
        </div>
      </div>

      <div className="rounded-md border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm">
        <span className="text-neutral-500">Applied to this claim: </span>
        <span className="num inline font-semibold text-neutral-900">
          {preview !== null ? formatMoney(preview, claim.currency) : '—'}
        </span>
        {crossCurrency && preview !== null && (
          <span className="text-neutral-500"> ({formatMoney(form.amount, form.currency)} × {form.exchange_rate || '?'}, rounded to 2 dp)</span>
        )}
      </div>

      <div className="flex justify-end gap-2 border-t border-neutral-100 pt-4">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" loading={saving}>
          {initial ? 'Record reversal' : 'Record payment'}
        </Button>
      </div>
    </form>
  );
}
