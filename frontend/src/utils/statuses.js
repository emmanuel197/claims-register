export const STATUS = {
  reserved: { label: 'Reserved, not yet settled', short: 'Reserved', variant: 'warning' },
  settled_outstanding: { label: 'Settled, payment outstanding', short: 'Payment outstanding', variant: 'info' },
  settled_paid: { label: 'Settled and paid', short: 'Paid', variant: 'success' },
};

export const STATUS_OPTIONS = Object.entries(STATUS).map(([value, s]) => ({ value, label: s.label }));

/** Derive the rate for "1 <from> = x <to>" from a GHS-based indicative table. */
export function indicativeRate(inGhs, from, to) {
  if (!inGhs || !inGhs[from] || !inGhs[to]) return '';
  if (from === to) return '1';
  const rate = Number(inGhs[from]) / Number(inGhs[to]);
  return rate.toFixed(4).replace(/0+$/, '').replace(/\.$/, '.0');
}
