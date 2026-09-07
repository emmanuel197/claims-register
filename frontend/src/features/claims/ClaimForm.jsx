import { useState } from 'react';
import { Input, MoneyInput, Select } from '../../components/forms/Field.jsx';
import Button from '../../components/ui/Button.jsx';
import { Alert } from '../../components/ui/Feedback.jsx';
import { parseApiError } from '../../api/client.js';
import { todayIso } from '../../utils/format.js';

const EMPTY = {
  policy_number: '',
  insured_name: '',
  loss_date: '',
  date_notified: '',
  loss_nature: '',
  loss_description: '',
  currency: 'GHS',
  estimated_loss_amount: '',
  approved_amount: '',
};

/**
 * Register a claim (fields in the order the brief lists them). Client-side
 * checks catch the obvious; the server is the authority and its field-keyed
 * 400s are rendered under the matching inputs.
 */
export default function ClaimForm({ meta, onSubmit, submitLabel = 'Register claim' }) {
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState(null);
  const [saving, setSaving] = useState(false);
  const today = todayIso();

  const set = (key) => (e) => {
    setForm((f) => ({ ...f, [key]: e.target.value }));
    setErrors((er) => ({ ...er, [key]: undefined }));
  };

  const validate = () => {
    const e = {};
    if (!form.policy_number.trim()) e.policy_number = 'Policy number is required.';
    if (!form.insured_name.trim()) e.insured_name = 'Insured name is required.';
    if (!form.loss_date) e.loss_date = 'Loss date is required.';
    if (!form.date_notified) e.date_notified = 'Date notified is required.';
    if (form.loss_date && form.date_notified && form.date_notified < form.loss_date) e.date_notified = 'Cannot be before the loss date.';
    if (!form.loss_nature) e.loss_nature = 'Choose the nature of loss.';
    if (form.loss_nature === 'other' && !form.loss_description.trim()) e.loss_description = 'Describe the loss when the nature is "Other".';
    if (!form.currency) e.currency = 'Choose a currency.';
    if (!(Number(form.estimated_loss_amount) > 0)) e.estimated_loss_amount = 'Enter an amount greater than zero.';
    if (form.approved_amount !== '' && !(Number(form.approved_amount) > 0)) e.approved_amount = 'Leave blank, or enter an amount greater than zero.';
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
        ...form,
        policy_number: form.policy_number.trim(),
        insured_name: form.insured_name.trim(),
        loss_description: form.loss_description.trim(),
      };
      if (payload.approved_amount === '') delete payload.approved_amount;
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
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      {message && <Alert title="The claim could not be saved">{message}</Alert>}

      <div className="grid gap-4 sm:grid-cols-2">
        <Input label="Policy number" required value={form.policy_number} onChange={set('policy_number')} error={errors.policy_number} maxLength={50} placeholder="e.g. GH-MOT-10021" autoFocus />
        <Input label="Insured name" required value={form.insured_name} onChange={set('insured_name')} error={errors.insured_name} maxLength={120} />
        <Input label="Loss date" required type="date" max={today} value={form.loss_date} onChange={set('loss_date')} error={errors.loss_date} />
        <Input label="Date notified" required type="date" min={form.loss_date || undefined} max={today} value={form.date_notified} onChange={set('date_notified')} error={errors.date_notified} helper="On or after the loss date" />
        <Select label="Nature of loss" required placeholder="Select…" options={meta?.loss_natures ?? []} value={form.loss_nature} onChange={set('loss_nature')} error={errors.loss_nature} />
        <Select label="Currency" required options={meta?.currencies ?? []} value={form.currency} onChange={set('currency')} error={errors.currency} helper="The claim is reserved in this currency" />
        <div className="sm:col-span-2">
          <Input
            label="Description of loss"
            required={form.loss_nature === 'other'}
            value={form.loss_description}
            onChange={set('loss_description')}
            error={errors.loss_description}
            maxLength={200}
            placeholder={form.loss_nature === 'other' ? 'What happened? e.g. Lightning strike killed 1,200 birds' : 'Optional — a short note on what happened'}
            helper={form.loss_nature === 'other' ? 'Required when the nature of loss is "Other"' : undefined}
          />
        </div>
        <MoneyInput label="Estimated loss amount" required currency={form.currency} value={form.estimated_loss_amount} onChange={set('estimated_loss_amount')} error={errors.estimated_loss_amount} />
        <MoneyInput label="Approved amount" currency={form.currency} value={form.approved_amount} onChange={set('approved_amount')} error={errors.approved_amount} helper="Optional — leave blank to keep the claim reserved" />
      </div>

      <div className="flex justify-end gap-2 border-t border-neutral-100 pt-4">
        <Button type="submit" loading={saving}>
          {submitLabel}
        </Button>
      </div>
    </form>
  );
}
