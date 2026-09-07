import { useCallback, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Plus } from 'lucide-react';
import { listClaims, getMeta } from '../api/claims.api.js';
import useApi from '../hooks/useApi.js';
import FilterBar, { EMPTY_FILTERS } from '../features/claims/FilterBar.jsx';
import ClaimsTable from '../features/claims/ClaimsTable.jsx';
import Button from '../components/ui/Button.jsx';
import { Alert, EmptyState, SlowApiHint } from '../components/ui/Feedback.jsx';

const DEFAULT_ORDERING = '-date_notified';

export default function ClaimsListPage() {
  const [params, setParams] = useSearchParams();

  // Filter state lives in the URL so a filtered view is shareable/refreshable.
  const filters = useMemo(() => {
    const f = { ...EMPTY_FILTERS };
    for (const key of Object.keys(EMPTY_FILTERS)) if (params.has(key)) f[key] = params.get(key);
    return f;
  }, [params]);
  const ordering = params.get('ordering') || DEFAULT_ORDERING;

  const update = useCallback(
    (next, nextOrdering = ordering) => {
      const p = new URLSearchParams();
      for (const [k, v] of Object.entries(next)) if (v && v !== EMPTY_FILTERS[k]) p.set(k, v);
      if (nextOrdering !== DEFAULT_ORDERING) p.set('ordering', nextOrdering);
      setParams(p, { replace: true });
    },
    [ordering, setParams]
  );

  const query = useMemo(() => {
    const q = { ordering };
    for (const [k, v] of Object.entries(filters)) if (v) q[k] = v;
    if (!filters.date_from && !filters.date_to) delete q.date_field;
    return q;
  }, [filters, ordering]);

  const meta = useApi(getMeta, []);
  const claims = useApi(() => listClaims(query), [JSON.stringify(query)]);

  const onSort = (key) => {
    const next = ordering === key ? `-${key}` : ordering === `-${key}` ? DEFAULT_ORDERING : key;
    update(filters, next);
  };

  const results = claims.data?.results ?? [];
  const totals = claims.data?.totals?.by_claim_currency ?? [];
  const outflows = claims.data?.totals?.paid_by_payment_currency ?? [];

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-neutral-900">Claims</h1>
          <p className="mt-0.5 text-sm text-neutral-500">
            {claims.data ? `${claims.data.count} claim${claims.data.count === 1 ? '' : 's'} match the current filters.` : 'Loading the register…'}
          </p>
        </div>
        <Link to="/claims/new">
          <Button>
            <Plus className="h-4 w-4" aria-hidden="true" /> Register claim
          </Button>
        </Link>
      </div>

      <FilterBar value={filters} onChange={(next) => update(next)} currencies={meta.data?.currencies ?? []} />

      {claims.error && (
        <Alert title="Could not load claims">
          {claims.error.message}{' '}
          <button type="button" className="underline" onClick={claims.reload}>
            Retry
          </button>
        </Alert>
      )}

      {!claims.error && !claims.loading && results.length === 0 ? (
        <div className="rounded-lg border border-neutral-200 bg-white shadow-sm">
          <EmptyState
            title="No claims match these filters"
            description="Try widening the date range or clearing the status and currency filters."
            action={
              <Button variant="outline" onClick={() => update(EMPTY_FILTERS)}>
                Clear filters
              </Button>
            }
          />
        </div>
      ) : (
        !claims.error && (
          <>
            <ClaimsTable claims={results} totals={totals} outflows={outflows} loading={claims.loading} ordering={ordering} onSort={onSort} />
            <SlowApiHint show={claims.loading && claims.slow} />
          </>
        )
      )}
    </div>
  );
}
