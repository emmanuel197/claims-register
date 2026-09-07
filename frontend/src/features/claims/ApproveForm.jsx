import { useState } from 'react';
import { MoneyInput } from '../../components/forms/Field.jsx';
import Button from '../../components/ui/Button.jsx';
import { parseApiError } from '../../api/client.js';
import { formatDateTime } from '../../utils/format.js';

/** Set or update the approved amount. Approval can be raised or lowered, never removed. */
export default function ApproveForm({ claim, onSubmit }) {
  const [amount, setAmount] = useState(claim.approved_amount ?? '');
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const approved = claim.approved_amount !== null;

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!(Number(amount) > 0)) return setError('Enter an amount greater than zero.');
    setSaving(true);
    setError(null);
    try {
      await onSubmit({ approved_amount: amount });
    } catch (err) {
      const parsed = parseApiError(err);
      setError(parsed.fields.approved_amount || parsed.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-3 sm:flex-row sm:items-end">
      <div className="flex-1">
        <MoneyInput
          label={approved ? 'Approved amount' : 'Set approved amount'}
          currency={claim.currency}
          value={amount}
          onChange={(e) => {
            setAmount(e.target.value);
            setError(null);
          }}
          error={error}
          helper={
            approved
              ? `First approved ${formatDateTime(claim.approved_at)}. Changing it re-derives the balance and status.`
              : 'Settling the claim moves it out of "Reserved" and starts tracking the outstanding balance.'
          }
        />
      </div>
      <Button type="submit" variant={approved ? 'outline' : 'primary'} loading={saving} className="sm:mb-[22px]">
        {approved ? 'Update approval' : 'Settle claim'}
      </Button>
    </form>
  );
}
