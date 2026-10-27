import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from '@/components/layout/AppLayout';
import ProtectedRoute from '@/components/layout/ProtectedRoute';
import { Toaster } from '@/components/ui/toast';

// Page components
import LoginPage from '@/pages/LoginPage';
import DashboardPage from '@/pages/DashboardPage';
import FDRRecordsPage from '@/pages/FDRRecordsPage';
import NewFDRPage from '@/pages/NewFDRPage';
import FDRDetailPage from '@/pages/FDRDetailPage';
import DuplicateReviewPage from '@/pages/DuplicateReviewPage';
import MaturityAlertsPage from '@/pages/MaturityAlertsPage';
import RenewalsPage from '@/pages/RenewalsPage';
import AIAssistantPage from '@/pages/AIAssistantPage';
import ReportsPage from '@/pages/ReportsPage';
import AuditTrailPage from '@/pages/AuditTrailPage';
import UserManagementPage from '@/pages/UserManagementPage';

export const App: React.FC = () => {
  return (
    <>
      <Routes>
        {/* Public authentication route */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected Application Routes wrapped with AppLayout */}
        <Route
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          {/* Default redirect to Dashboard */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />

          {/* Primary Operations */}
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/fdrs" element={<FDRRecordsPage />} />
          <Route path="/fdrs/new" element={<NewFDRPage />} />
          <Route path="/fdrs/:id" element={<FDRDetailPage />} />

          {/* Regulatory & Risk Modules */}
          <Route
            path="/duplicates"
            element={
              <ProtectedRoute allowedRoles={['reviewer', 'admin']}>
                <DuplicateReviewPage />
              </ProtectedRoute>
            }
          />
          <Route path="/maturity" element={<MaturityAlertsPage />} />
          <Route path="/renewals" element={<RenewalsPage />} />
          <Route path="/ai-assistant" element={<AIAssistantPage />} />

          {/* Administrative & Reporting Modules */}
          <Route
            path="/reports"
            element={
              <ProtectedRoute allowedRoles={['reviewer', 'approving_authority', 'admin']}>
                <ReportsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/audit"
            element={
              <ProtectedRoute allowedRoles={['admin', 'approving_authority']}>
                <AuditTrailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/users"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <UserManagementPage />
              </ProtectedRoute>
            }
          />
        </Route>

        {/* Catch-all redirect */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>

      {/* Global Toast Notifications */}
      <Toaster position="top-right" richColors />
    </>
  );
};

export default App;
