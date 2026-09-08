import { Route, Routes } from 'react-router-dom';
import { Analytics } from '@vercel/analytics/react';
import AppShell from './components/layout/AppShell.jsx';
import ClaimsListPage from './pages/ClaimsListPage.jsx';
import ClaimDetailPage from './pages/ClaimDetailPage.jsx';
import NewClaimPage from './pages/NewClaimPage.jsx';
import NotFoundPage from './pages/NotFoundPage.jsx';

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<ClaimsListPage />} />
        <Route path="/claims/new" element={<NewClaimPage />} />
        <Route path="/claims/:id" element={<ClaimDetailPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
      <Analytics />
    </AppShell>
  );
}
