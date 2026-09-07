/**
 * Display-only formatting. The API sends money as strings ("1250.00");
 * we convert to Number *only* to format, never to calculate.
 */

const numberFormat = new Intl.NumberFormat('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function formatMoney(value, currency) {
  if (value === null || value === undefined || value === '') return '—';
  const n = Number(value);
  if (Number.isNaN(n)) return '—';
  const sign = n < 0 ? '−' : '';
  const body = numberFormat.format(Math.abs(n));
  return currency ? `${sign}${currency} ${body}` : `${sign}${body}`;
}

export function isNegative(value) {
  return value !== null && value !== undefined && Number(value) < 0;
}

export function formatRate(value) {
  if (value === null || value === undefined) return '—';
  const n = Number(value);
  // Trim trailing zeros but keep at least 2 dp (15.20000000 -> 15.20).
  const s = n.toFixed(8).replace(/0+$/, '');
  const [int, dec = ''] = s.split('.');
  return `${int}.${dec.padEnd(2, '0')}`;
}

const dateFormat = new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });

export function formatDate(iso) {
  if (!iso) return '—';
  const [y, m, d] = iso.split('-').map(Number);
  return dateFormat.format(new Date(y, m - 1, d));
}

export function formatDateTime(iso) {
  if (!iso) return '—';
  return new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(iso));
}

export function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

/** Round half-up to 2 dp for the payment preview. Server value is authoritative. */
export function previewConversion(amount, rate) {
  const a = Number(amount);
  const r = Number(rate);
  if (!Number.isFinite(a) || !Number.isFinite(r)) return null;
  const scaled = Math.abs(a * r) * 100;
  const rounded = Math.round(scaled + Number.EPSILON) / 100;
  return (a * r < 0 ? -rounded : rounded).toFixed(2);
}
