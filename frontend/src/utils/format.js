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

/**
 * Preview of amount × rate rounded half-up to 2 dp, computed in integer
 * arithmetic (BigInt) so it matches the server's Decimal result even at the
 * .005 boundary. Display only — the stored value comes back from the API.
 */
export function previewConversion(amount, rate) {
  const a = parseDecimal(amount);
  const r = parseDecimal(rate);
  if (!a || !r) return null;
  // product has a.scale + r.scale decimal places; we want 2.
  const scale = a.scale + r.scale;
  let product = a.digits * r.digits;
  const negative = product < 0n;
  if (negative) product = -product;
  let cents;
  if (scale <= 2) {
    cents = product * 10n ** BigInt(2 - scale);
  } else {
    const divisor = 10n ** BigInt(scale - 2);
    cents = product / divisor;
    if ((product % divisor) * 2n >= divisor) cents += 1n; // half-up
  }
  const text = cents.toString().padStart(3, '0');
  return `${negative && cents !== 0n ? '-' : ''}${text.slice(0, -2)}.${text.slice(-2)}`;
}

/** "-12.345" -> { digits: -12345n, scale: 3 }; null if not a plain decimal. */
function parseDecimal(value) {
  const s = String(value ?? '').trim();
  const m = /^(-?)(\d*)(?:\.(\d*))?$/.exec(s);
  if (!m || (m[2] === '' && (m[3] ?? '') === '')) return null;
  const frac = m[3] ?? '';
  const digits = BigInt(`${m[1]}${m[2] || '0'}${frac}`);
  return { digits, scale: frac.length };
}
