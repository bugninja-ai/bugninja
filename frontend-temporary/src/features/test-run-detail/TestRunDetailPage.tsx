import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { AlertTriangle, Loader2 } from 'lucide-react';
import { useTestRunDetail } from './hooks/useTestRunDetail';
import { TestRunHeader } from './components/TestRunHeader';
import { TestGoalSection } from './components/TestGoalSection';
import { TestRunGif } from './components/TestRunGif';
import { RunInformation } from './components/RunInformation';
import { BrowserConfiguration } from './components/BrowserConfiguration';
import { TestExecutionSteps } from './components/TestExecutionSteps';
import { ErrorSection } from './components/ErrorSection';
import ScreenshotModal from '../../shared/components/ScreenshotModal';

const TestRunDetailPage: React.FC = () => {
  const { runId } = useParams<{ runId: string }>();
  const {
    testRun,
    loading,
    error,
    modalOpen,
    selectedScreenshot,
    selectedActionData,
    isPolling,
    openScreenshotModal,
    closeModal
  } = useTestRunDetail(runId);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="animate-spin h-8 w-8 border-4 border-indigo-600 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-gray-600">Loading test run details...</p>
        </div>
      </div>
    );
  }

  if (error || !testRun) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-800 mb-2">
            {error || 'Test run not found'}
          </h3>
          <p className="text-gray-600 mb-4">
            {error || 'The requested test run could not be found.'}
          </p>
          <Link
            to="/runs"
            className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Back to test runs
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <TestRunHeader testRun={testRun} />

      {/* Test Goal */}
      <TestGoalSection goal={testRun.testCase.goal} />

      {/* Test Run GIF */}
      {testRun.gif && <TestRunGif gif={testRun.gif} />}

      {/* Run Information */}
      <RunInformation testRun={testRun} />

      {/* Browser Configuration */}
      <BrowserConfiguration testRun={testRun} />

      {/* Test Execution Steps */}
      <TestExecutionSteps 
        testRun={testRun} 
        onScreenshotClick={openScreenshotModal}
      />

      {/* Global Error */}
      {testRun.error && <ErrorSection error={testRun.error} />}

      {/* Polling Indicator at Bottom */}
      {isPolling && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 sticky bottom-4 z-10">
          <div className="flex items-center justify-center space-x-2">
            <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
            <span className="text-sm text-blue-700 font-medium">
              Test is running - Auto-refreshing every 3 seconds...
            </span>
          </div>
        </div>
      )}

      {/* Screenshot Modal */}
      {selectedActionData && (
        <ScreenshotModal
          isOpen={modalOpen}
          onClose={closeModal}
          screenshot={selectedScreenshot}
          actionData={selectedActionData}
        />
      )}
    </div>
  );
};

export default TestRunDetailPage;
