import { SearchX } from 'lucide-react';
import Button from '../components/ui/Button.jsx';
import { EmptyState } from '../components/ui/Feedback.jsx';

export default function NotFoundPage() {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white shadow-sm">
      <EmptyState
        icon={SearchX}
        title="Page not found"
        description="That address does not exist in the register."
        action={
          <Button to="/" variant="outline">
            Back to claims
          </Button>
        }
      />
    </div>
  );
}
