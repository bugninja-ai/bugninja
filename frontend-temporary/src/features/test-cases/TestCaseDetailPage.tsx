import React from 'react';
import { useParams } from 'react-router-dom';
import { Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';

import { useTestCaseDetail } from './hooks/useTestCaseDetail';
import { TestCaseHeader } from './components/TestCaseHeader';
import { TestCaseGoal } from './components/TestCaseGoal';
import { TestCaseBasicInfo } from './components/TestCaseBasicInfo';
import { TestCaseConfiguration } from './components/TestCaseConfiguration';
import { ExtraRulesSection } from './components/ExtraRulesSection';
import { BrowserConfigurationSection } from './components/BrowserConfigurationSection';
import { SecretsSection } from './components/SecretsSection';
import { RecentTestRuns } from './components/RecentTestRuns';
import { ExecutionSummary } from './components/ExecutionSummary';
import { DeleteTestCaseSection } from './components/DeleteTestCaseSection';
import { DeleteConfirmationModal } from './components/DeleteConfirmationModal';
import { RunTestModal } from './components/RunTestModal';

const TestCaseDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const {
    // Main state
    testCase,
    editableTestCase,
    loading,
    error,
    
    // Edit states
    editingGoal,
    setEditingGoal,
    editingBasicInfo,
    setEditingBasicInfo,
    editingConfig,
    setEditingConfig,
    editingRules,
    setEditingRules,
    editingBrowsers,
    setEditingBrowsers,
    editingSecrets,
    setEditingSecrets,
    
    // Dropdown states
    categoryDropdownOpen,
    setCategoryDropdownOpen,
    priorityDropdownOpen,
    setPriorityDropdownOpen,
    existingBrowserConfigDropdownOpen,
    setExistingBrowserConfigDropdownOpen,
    existingSecretDropdownOpen,
    setExistingSecretDropdownOpen,
    browserChannelDropdowns,
    setBrowserChannelDropdowns,
    userAgentDropdowns,
    setUserAgentDropdowns,
    viewportDropdowns,
    setViewportDropdowns,
    
    // Data
    browserConfigOptions,
    existingBrowserConfigs,
    existingSecrets,
    recentTestRuns,
    testRunsLoading,
    
    // Secrets
    visibleSecrets,
    copiedSecret,
    toggleSecretVisibility,
    copySecret,
    
    // Delete modal
    showDeleteModal,
    deleteLoading,
    deleteError,
    
    // Run test modal
    showRunTestModal,
    
    // Handlers
    handleGoalChange,
    handleCategoryChange,
    handlePriorityChange,
    handleStartingUrlChange,
    handleAllowedDomainsChange,
    handleRulesChange,
    handleBrowserConfigsChange,
    handleExistingBrowserConfigsAdd,
    handleSecretsChange,
    handleExistingSecretsAdd,
    
    // Save handlers
    saveGoal,
    saveBasicInfo,
    saveConfig,
    saveRules,
    saveBrowsers,
    saveSecrets,
    
    // Cancel handler
    cancelEdit,
    
    // Delete handlers
    handleDeleteTestCase,
    confirmDeleteTestCase,
    cancelDeleteTestCase,
    
    // Run test handlers
    handleRunTest,
    handleCloseRunTestModal,
    handleTestStarted,
    
    // Reload function
    loadTestCase
  } = useTestCaseDetail(id);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading test case details...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-800 mb-2">Failed to load test case</h3>
          <p className="text-gray-600 mb-4">{error}</p>
          <div className="space-x-3">
            <button
              onClick={() => id && loadTestCase(id)}
              className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Try again
            </button>
            <Link
              to="/"
              className="inline-flex items-center px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
            >
              Back to test cases
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!testCase) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-800 mb-2">Test case not found</h3>
          <p className="text-gray-600 mb-4">The requested test case could not be found.</p>
          <Link
            to="/"
            className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Back to test cases
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <TestCaseHeader testCase={testCase} onRunTest={handleRunTest} />

      {/* Test Goal */}
      <TestCaseGoal
        testCase={testCase}
        editableTestCase={editableTestCase}
        isEditing={editingGoal}
        onEdit={() => setEditingGoal(true)}
        onSave={saveGoal}
        onCancel={() => cancelEdit('goal')}
        onGoalChange={handleGoalChange}
      />

      {/* Extra instructions (steps) */}
      <ExtraRulesSection
        testCase={testCase}
        editableTestCase={editableTestCase}
        isEditing={editingRules}
        onEdit={() => setEditingRules(true)}
        onSave={saveRules}
        onCancel={() => cancelEdit('rules')}
        onRulesChange={handleRulesChange}
      />

      {/* Basic Information */}
      <TestCaseBasicInfo
        testCase={testCase}
        editableTestCase={editableTestCase}
        isEditing={editingBasicInfo}
        onEdit={() => setEditingBasicInfo(true)}
        onSave={saveBasicInfo}
        onCancel={() => cancelEdit('basicInfo')}
        onCategoryChange={handleCategoryChange}
        onPriorityChange={handlePriorityChange}
        categoryDropdownOpen={categoryDropdownOpen}
        setCategoryDropdownOpen={setCategoryDropdownOpen}
        priorityDropdownOpen={priorityDropdownOpen}
        setPriorityDropdownOpen={setPriorityDropdownOpen}
      />

      {/* Test Configuration */}
      <TestCaseConfiguration
        testCase={testCase}
        editableTestCase={editableTestCase}
        isEditing={editingConfig}
        onEdit={() => setEditingConfig(true)}
        onSave={saveConfig}
        onCancel={() => cancelEdit('config')}
        onStartingUrlChange={handleStartingUrlChange}
        onAllowedDomainsChange={handleAllowedDomainsChange}
      />

      {/* Browser Configurations */}
      <BrowserConfigurationSection
        testCase={testCase}
        editableTestCase={editableTestCase}
        isEditing={editingBrowsers}
        onEdit={() => setEditingBrowsers(true)}
        onSave={saveBrowsers}
        onCancel={() => cancelEdit('browsers')}
        onConfigChange={handleBrowserConfigsChange}
        onExistingConfigAdd={handleExistingBrowserConfigsAdd}
        browserConfigOptions={browserConfigOptions}
        existingBrowserConfigs={existingBrowserConfigs}
        existingBrowserConfigDropdownOpen={existingBrowserConfigDropdownOpen}
        setExistingBrowserConfigDropdownOpen={setExistingBrowserConfigDropdownOpen}
        browserChannelDropdowns={browserChannelDropdowns}
        setBrowserChannelDropdowns={setBrowserChannelDropdowns}
        userAgentDropdowns={userAgentDropdowns}
        setUserAgentDropdowns={setUserAgentDropdowns}
        viewportDropdowns={viewportDropdowns}
        setViewportDropdowns={setViewportDropdowns}
      />

      {/* Secrets */}
      <SecretsSection
        testCase={testCase}
        editableTestCase={editableTestCase}
        isEditing={editingSecrets}
        onEdit={() => setEditingSecrets(true)}
        onSave={saveSecrets}
        onCancel={() => cancelEdit('secrets')}
        onSecretsChange={handleSecretsChange}
        onExistingSecretsAdd={handleExistingSecretsAdd}
        existingSecrets={existingSecrets}
        existingSecretDropdownOpen={existingSecretDropdownOpen}
        setExistingSecretDropdownOpen={setExistingSecretDropdownOpen}
        visibleSecrets={visibleSecrets}
        onToggleSecretVisibility={toggleSecretVisibility}
        copiedSecret={copiedSecret}
        onCopySecret={copySecret}
      />

      {/* Recent Test Runs */}
      <RecentTestRuns
        testCase={testCase}
        recentTestRuns={recentTestRuns}
        testRunsLoading={testRunsLoading}
        onRunTest={handleRunTest}
      />

      {/* Execution Summary */}
      <ExecutionSummary testCase={testCase} />

      {/* Delete Test Case Section */}
      <DeleteTestCaseSection
        testCase={testCase}
        onDelete={handleDeleteTestCase}
      />

      {/* Delete Confirmation Modal */}
      <DeleteConfirmationModal
        isOpen={showDeleteModal}
        testCase={testCase}
        loading={deleteLoading}
        error={deleteError}
        onConfirm={confirmDeleteTestCase}
        onCancel={cancelDeleteTestCase}
      />

      {/* Run Test Modal */}
      <RunTestModal
        isOpen={showRunTestModal}
        onClose={handleCloseRunTestModal}
        testCase={testCase}
        onTestStarted={handleTestStarted}
      />
    </div>
  );
};

export default TestCaseDetailPage;
