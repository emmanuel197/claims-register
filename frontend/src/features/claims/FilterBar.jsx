import { useEffect, useState } from 'react';
import { Search, X } from 'lucide-react';
import { Input, Select } from '../../components/forms/Field.jsx';
import Button from '../../components/ui/Button.jsx';
import { STATUS_OPTIONS } from '../../utils/statuses.js';

const DATE_FIELDS = [
  { value: 'loss_date', label: 'Loss date' },
  { value: 'date_notified', label: 'Date notified' },
];

export const EMPTY_FILTERS = { date_field: 'loss_date', date_from: '', date_to: '', status: '', currency: '', search: '' };

/**
 * Controlled filter bar. Every change calls onChange immediately except the
 * search box, which is debounced so we don't hit the API per keystroke.
 */
export default function FilterBar({ value, onChange, currencies = [] }) {
  const [search, setSearch] = useState(value.search);

  useEffect(() => setSearch(value.search), [value.search]);

  useEffect(() => {
    if (search === value.search) return undefined;
    const t = setTimeout(() => onChange({ ...value, search }), 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const set = (key) => (e) => onChange({ ...value, [key]: e.target.value });
  const isDirty = Object.keys(EMPTY_FILTERS).some((k) => value[k] !== EMPTY_FILTERS[k]);

  return (
    <section aria-label="Filters" className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-7">
        <Select label="Date field" options={DATE_FIELDS} value={value.date_field} onChange={set('date_field')} />
        <Input label="From" type="date" value={value.date_from} onChange={set('date_from')} max={value.date_to || undefined} />
        <Input label="To" type="date" value={value.date_to} onChange={set('date_to')} min={value.date_from || undefined} helper="Inclusive" />
        <Select label="Status" placeholder="All statuses" options={STATUS_OPTIONS} value={value.status} onChange={set('status')} />
        <Select label="Currency" placeholder="All currencies" options={currencies} value={value.currency} onChange={set('currency')} />
        <div className="col-span-2 md:col-span-1 xl:col-span-2">
          <Input
            label="Search"
            type="search"
            placeholder="Policy number or insured name"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            prefix={<Search className="h-3.5 w-3.5" aria-hidden="true" />}
          />
        </div>
      </div>
      {isDirty && (
        <div className="mt-3 flex justify-end">
          <Button variant="ghost" size="sm" onClick={() => onChange(EMPTY_FILTERS)}>
            <X className="h-3.5 w-3.5" aria-hidden="true" /> Clear filters
          </Button>
        </div>
      )}
    </section>
  );
}
