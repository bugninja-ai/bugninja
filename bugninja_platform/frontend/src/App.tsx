
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './app/layout/Layout';
import TestCasesPage from './features/test-cases/TestCasesPage';
import { CreateTestPage } from './features/create-test';
import TestRunsPage from './features/test-runs/TestRunsPage';
import TestRunDetailPage from './features/test-run-detail/TestRunDetailPage';
import TestCaseDetailPage from './features/test-cases/TestCaseDetailPage';
import SettingsPage from './features/settings/SettingsPage';
import { ProjectProvider } from './app/providers/ProjectContext';
import { ErrorBoundary } from './shared/components/ErrorBoundary';


function App() {
  return (
    <ErrorBoundary>
      <ProjectProvider>
        <Router>
          <Layout>
            <ErrorBoundary>
              <Routes>
                <Route path="/" element={<TestCasesPage />} />
                <Route path="/create" element={<CreateTestPage />} />
                <Route path="/runs" element={<TestRunsPage />} />
                <Route path="/runs/:runId" element={<TestRunDetailPage />} />
                <Route path="/test-details/:id" element={<TestCaseDetailPage />} />
                <Route path="/dashboard" element={<div className="p-8 text-center"><h1 className="text-2xl font-bold text-gray-900">Dashboard</h1><p className="text-gray-600">Coming soon...</p></div>} />
                <Route path="/analytics" element={<div className="p-8 text-center"><h1 className="text-2xl font-bold text-gray-900">Analytics</h1><p className="text-gray-600">Coming soon...</p></div>} />
                <Route path="/settings" element={<SettingsPage />} />
              </Routes>
            </ErrorBoundary>
          </Layout>
        </Router>
      </ProjectProvider>
    </ErrorBoundary>
  );
}

export default App; 