import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { createClaim, getMeta } from '../api/claims.api.js';
import useApi from '../hooks/useApi.js';
import ClaimForm from '../features/claims/ClaimForm.jsx';
import { useToast } from '../components/ui/Toast.jsx';

export default function NewClaimPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const meta = useApi(getMeta, []);

  const handleSubmit = async (payload) => {
    const claim = await createClaim(payload);
    toast.success(`Claim ${claim.claim_number} registered for ${claim.insured_name}.`);
    navigate(`/claims/${claim.id}`);
  };

  return (
    <div className="mx-auto max-w-3xl space-y-4 animate-fade-in">
      <Link to="/" className="inline-flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-800">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to claims
      </Link>
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-neutral-900">Register a claim</h1>
        <p className="mt-0.5 text-sm text-neutral-500">Capture the policy, the loss and the reserve. Payments are recorded on the claim afterwards.</p>
      </div>
      <div className="rounded-lg border border-neutral-200 bg-white p-5 shadow-sm sm:p-6">
        <ClaimForm meta={meta.data} onSubmit={handleSubmit} />
      </div>
    </div>
  );
}
