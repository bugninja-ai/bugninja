import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Plus, AlertCircle, FileText } from 'lucide-react';
import { useCreateTest } from './hooks/useCreateTest';
import { MethodSelection } from './components/MethodSelection';
import { FileUploadSection } from './components/FileUploadSection';
import { BasicInformationSection } from './components/BasicInformationSection';
import { TestConfigurationSection } from './components/TestConfigurationSection';
import { ExtraRulesSection } from './components/ExtraRulesSection';
import { SuccessModal } from './components/SuccessModal';
import { NoProjectWarning } from './components/NoProjectWarning';
import { BrowserConfigurationsSection } from './components/BrowserConfigurationsSection';
import { SecretsSection } from './components/SecretsSection';
import { useProjects } from '../../shared/hooks/useProjects';


const CreateTestPage: React.FC = () => {
  const navigate = useNavigate();
  const { selectedProject } = useProjects();
  const {
    method,
    setMethod,
    formData,
    file,
    setFile,
    fileProcessing,
    fileProcessed,
    browserConfigOptions,
    existingBrowserConfigs,
    existingSecrets,
    loadingData,
    dropdowns,
    handleInputChange,
    handleRuleChange,
    addRule,
    removeRule,
    handleDomainChange,
    addDomain,
    removeDomain,
    handleNewBrowserConfigChange,
    addNewBrowserConfig,
    removeNewBrowserConfig,
    removeExistingBrowserConfig,
    addExistingBrowserConfig,
    handleNewSecretChange,
    addNewSecret,
    removeNewSecret,
    removeExistingSecret,
    addExistingSecret,
    handleFileChange,
    processUploadedFile,
    loading,
    success,
    error,
    handleSubmit,
    priorityOptions,
    categoryOptions,
  } = useCreateTest();

  // Simple fix: just use the dropdowns directly with the correct keys
  const browserChannelDropdowns = { [formData.newBrowserConfigs[0]?.id || '1']: dropdowns.isOpen(`browserChannel-${formData.newBrowserConfigs[0]?.id || '1'}`) };
  const setBrowserChannelDropdowns = (update: any) => {
    if (typeof update === 'function') {
      const current = { [formData.newBrowserConfigs[0]?.id || '1']: dropdowns.isOpen(`browserChannel-${formData.newBrowserConfigs[0]?.id || '1'}`) };
      const newState = update(current);
      Object.entries(newState).forEach(([key, isOpen]) => {
        if (isOpen) dropdowns.open(`browserChannel-${key}`);
        else dropdowns.close(`browserChannel-${key}`);
      });
    } else {
      Object.entries(update).forEach(([key, isOpen]) => {
        if (isOpen) dropdowns.open(`browserChannel-${key}`);
        else dropdowns.close(`browserChannel-${key}`);
      });
    }
  };

  const userAgentDropdowns = { [formData.newBrowserConfigs[0]?.id || '1']: dropdowns.isOpen(`userAgent-${formData.newBrowserConfigs[0]?.id || '1'}`) };
  const setUserAgentDropdowns = (update: any) => {
    if (typeof update === 'function') {
      const current = { [formData.newBrowserConfigs[0]?.id || '1']: dropdowns.isOpen(`userAgent-${formData.newBrowserConfigs[0]?.id || '1'}`) };
      const newState = update(current);
      Object.entries(newState).forEach(([key, isOpen]) => {
        if (isOpen) dropdowns.open(`userAgent-${key}`);
        else dropdowns.close(`userAgent-${key}`);
      });
    } else {
      Object.entries(update).forEach(([key, isOpen]) => {
        if (isOpen) dropdowns.open(`userAgent-${key}`);
        else dropdowns.close(`userAgent-${key}`);
      });
    }
  };

  const viewportDropdowns = { [formData.newBrowserConfigs[0]?.id || '1']: dropdowns.isOpen(`viewport-${formData.newBrowserConfigs[0]?.id || '1'}`) };
  const setViewportDropdowns = (update: any) => {
    if (typeof update === 'function') {
      const current = { [formData.newBrowserConfigs[0]?.id || '1']: dropdowns.isOpen(`viewport-${formData.newBrowserConfigs[0]?.id || '1'}`) };
      const newState = update(current);
      Object.entries(newState).forEach(([key, isOpen]) => {
        if (isOpen) dropdowns.open(`viewport-${key}`);
        else dropdowns.close(`viewport-${key}`);
      });
    } else {
      Object.entries(update).forEach(([key, isOpen]) => {
        if (isOpen) dropdowns.open(`viewport-${key}`);
        else dropdowns.close(`viewport-${key}`);
      });
    }
  };

  const existingBrowserConfigDropdowns = { main: dropdowns.isOpen('existingBrowserConfig-main') };
  const setExistingBrowserConfigDropdowns = (update: any) => {
    if (typeof update === 'function') {
      const current = { main: dropdowns.isOpen('existingBrowserConfig-main') };
      const newState = update(current);
      Object.entries(newState).forEach(([key, isOpen]) => {
        if (isOpen) dropdowns.open(`existingBrowserConfig-${key}`);
        else dropdowns.close(`existingBrowserConfig-${key}`);
      });
    } else {
      Object.entries(update).forEach(([key, isOpen]) => {
        if (isOpen) dropdowns.open(`existingBrowserConfig-${key}`);
        else dropdowns.close(`existingBrowserConfig-${key}`);
      });
    }
  };

  const existingSecretsDropdowns = { main: dropdowns.isOpen('existingSecrets-main') };
  const setExistingSecretsDropdowns = (update: any) => {
    if (typeof update === 'function') {
      const current = { main: dropdowns.isOpen('existingSecrets-main') };
      const newState = update(current);
      Object.entries(newState).forEach(([key, isOpen]) => {
        if (isOpen) dropdowns.open(`existingSecrets-${key}`);
        else dropdowns.close(`existingSecrets-${key}`);
      });
    } else {
      Object.entries(update).forEach(([key, isOpen]) => {
        if (isOpen) dropdowns.open(`existingSecrets-${key}`);
        else dropdowns.close(`existingSecrets-${key}`);
      });
    }
  };

  if (success) {
    return <SuccessModal />;
  }

  if (!selectedProject) {
    return <NoProjectWarning />;
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-800">Create Test Case</h1>
        <p className="mt-1 text-gray-600">Create a new automated test case for your application</p>
      </div>

      {/* Method Selection */}
      <MethodSelection method={method} onMethodChange={setMethod} />

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
            <AlertCircle className="w-5 h-5 text-red-600 mr-2" />
            <p className="text-red-800">{error}</p>
          </div>
        </div>
      )}

      {/* Form Content */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {method === 'upload' && !fileProcessed ? (
          <FileUploadSection
            file={file}
            onFileChange={handleFileChange}
            onFileRemove={() => setFile(null)}
            onProcessFile={processUploadedFile}
            fileProcessing={fileProcessing}
            fileProcessed={fileProcessed}
          />
        ) : (
          <div className="space-y-8">
            {/* Show file info if processed from upload */}
            {method === 'upload' && fileProcessed && file && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center space-x-2 mb-2">
                  <FileText className="w-5 h-5 text-green-600" />
                  <span className="font-medium text-green-800">File processed: {file.name}</span>
                  <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
                    AI Processed
                  </span>
                </div>
                <p className="text-sm text-green-700">
                  The form below has been automatically populated with data extracted from your file. 
                  You can review and modify any fields before creating the test case.
                </p>
              </div>
            )}
            
            {loadingData ? (
              <div className="bg-white/80 backdrop-blur-sm rounded-lg p-6 border border-gray-200 relative z-0">
                <div className="flex items-center justify-center">
                  <Loader2 className="w-6 h-6 animate-spin text-indigo-600 mr-2" />
                  <span className="text-gray-600">Loading browser types and existing configurations...</span>
                </div>
              </div>
            ) : (
              <>
                {/* Basic Information */}
                <BasicInformationSection
                  formData={{
                    title: formData.title,
                    description: formData.description,
                    priority: formData.priority,
                    category: formData.category,
                    goal: formData.goal,
                  }}
                  onInputChange={handleInputChange}
                  priorityOptions={priorityOptions}
                  categoryOptions={categoryOptions}
                  priorityDropdownOpen={dropdowns.isOpen('priority')}
                  setPriorityDropdownOpen={(open: boolean) => open ? dropdowns.open('priority') : dropdowns.close('priority')}
                  categoryDropdownOpen={dropdowns.isOpen('category')}
                  setCategoryDropdownOpen={(open: boolean) => open ? dropdowns.open('category') : dropdowns.close('category')}
                />

                {/* Extra instructions (steps) */}
                <ExtraRulesSection
                  extraRules={formData.extraRules}
                  onRuleChange={handleRuleChange}
                  onAddRule={addRule}
                  onRemoveRule={removeRule}
                />

                {/* Test Configuration */}
                <TestConfigurationSection
                  formData={{
                    startingUrl: formData.startingUrl,
                    allowedDomains: formData.allowedDomains,
                  }}
                  onInputChange={handleInputChange}
                  onDomainChange={handleDomainChange}
                  onAddDomain={addDomain}
                  onRemoveDomain={removeDomain}
                />

                {/* Browser Configurations */}
                <BrowserConfigurationsSection
                  newBrowserConfigs={formData.newBrowserConfigs}
                  existingBrowserConfigIds={formData.existingBrowserConfigIds}
                  existingBrowserConfigs={existingBrowserConfigs}
                  browserConfigOptions={browserConfigOptions}
                  onNewBrowserConfigChange={handleNewBrowserConfigChange}
                  onAddNewBrowserConfig={addNewBrowserConfig}
                  onRemoveNewBrowserConfig={removeNewBrowserConfig}
                  onRemoveExistingBrowserConfig={removeExistingBrowserConfig}
                  onAddExistingBrowserConfig={addExistingBrowserConfig}
                  browserChannelDropdowns={browserChannelDropdowns}
                  setBrowserChannelDropdowns={setBrowserChannelDropdowns}
                  userAgentDropdowns={userAgentDropdowns}
                  setUserAgentDropdowns={setUserAgentDropdowns}
                  viewportDropdowns={viewportDropdowns}
                  setViewportDropdowns={setViewportDropdowns}
                  existingBrowserConfigDropdowns={existingBrowserConfigDropdowns}
                  setExistingBrowserConfigDropdowns={setExistingBrowserConfigDropdowns}
                />

                {/* Secrets */}
                <SecretsSection
                  newSecrets={formData.newSecrets}
                  existingSecretIds={formData.existingSecretIds}
                  existingSecrets={existingSecrets}
                  onNewSecretChange={handleNewSecretChange}
                  onAddNewSecret={addNewSecret}
                  onRemoveNewSecret={removeNewSecret}
                  onRemoveExistingSecret={removeExistingSecret}
                  onAddExistingSecret={addExistingSecret}
                  existingSecretsDropdowns={existingSecretsDropdowns}
                  setExistingSecretsDropdowns={setExistingSecretsDropdowns}
                />
              </>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center justify-between pt-6">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="px-6 py-3 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Cancel
          </button>
          
          <button
            type="submit"
            disabled={loading || (method === 'upload' && !file) || (method === 'manual' && (!formData.title || !formData.description || !formData.goal || !formData.startingUrl || formData.allowedDomains.some(domain => !domain.trim())))}
            className="inline-flex items-center px-6 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <Plus className="w-4 h-4 mr-2" />
                Create Test Case
              </>
            )}
          </button>
        </div>
      </form>

      {/* Help Information */}
      <div className="bg-blue-50 rounded-lg p-6 border border-blue-200">
        <div className="flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5" />
          <div>
            <h3 className="text-sm font-semibold text-blue-900 mb-1">Need Help?</h3>
            <p className="text-sm text-blue-800">
              Test cases should be clear, specific, and include all necessary steps to validate the expected behavior. 
              For file uploads, we support CSV, JSON, TXT, DOC, DOCX, PDF, XLSX, XLS, Python (.py), JavaScript (.js), TypeScript (.ts), TOML, and Markdown (.md) formats. Our AI will intelligently parse the content and generate appropriate test cases.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CreateTestPage;
