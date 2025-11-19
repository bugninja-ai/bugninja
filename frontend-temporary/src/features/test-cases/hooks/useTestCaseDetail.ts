import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { FrontendTestCase, TestCategory, TestPriority, BrowserConfig, TestSecret, ExtraRule } from '../types';
import { TestCaseService } from '../services/testCaseService';
import { BrowserService } from '../../settings/services/browserService';
import { BrowserConfigOptions, BrowserConfigData, SecretValue, UpdateBrowserConfigWithId, CreateBrowserConfigRequest, UpdateSecretValueWithId, CreateSecretValueRequest } from '../../settings/types';

export const useTestCaseDetail = (testCaseId: string | undefined) => {
  const navigate = useNavigate();
  
  // Main state
  const [testCase, setTestCase] = useState<FrontendTestCase | null>(null);
  const [editableTestCase, setEditableTestCase] = useState<FrontendTestCase | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Edit mode states
  const [editingGoal, setEditingGoal] = useState(false);
  const [editingBasicInfo, setEditingBasicInfo] = useState(false);
  const [editingConfig, setEditingConfig] = useState(false);
  const [editingRules, setEditingRules] = useState(false);
  const [editingBrowsers, setEditingBrowsers] = useState(false);
  const [editingSecrets, setEditingSecrets] = useState(false);
  
  // Dropdown states
  const [categoryDropdownOpen, setCategoryDropdownOpen] = useState(false);
  const [priorityDropdownOpen, setPriorityDropdownOpen] = useState(false);
  const [existingBrowserConfigDropdownOpen, setExistingBrowserConfigDropdownOpen] = useState(false);
  const [existingSecretDropdownOpen, setExistingSecretDropdownOpen] = useState(false);
  const [browserChannelDropdowns, setBrowserChannelDropdowns] = useState<Record<string, boolean>>({});
  const [userAgentDropdowns, setUserAgentDropdowns] = useState<Record<string, boolean>>({});
  const [viewportDropdowns, setViewportDropdowns] = useState<Record<string, boolean>>({});
  
  // Browser config data
  const [browserConfigOptions, setBrowserConfigOptions] = useState<BrowserConfigOptions | null>(null);
  const [existingBrowserConfigs, setExistingBrowserConfigs] = useState<BrowserConfigData[]>([]);
  
  // Secrets data
  const [existingSecrets, setExistingSecrets] = useState<SecretValue[]>([]);
  const [visibleSecrets, setVisibleSecrets] = useState<Set<string>>(new Set());
  const [copiedSecret, setCopiedSecret] = useState<string | null>(null);
  
  // Test runs
  const [recentTestRuns, setRecentTestRuns] = useState<any[]>([]);
  const [testRunsLoading, setTestRunsLoading] = useState(false);
  
  // Delete confirmation modal
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Run test modal
  const [showRunTestModal, setShowRunTestModal] = useState(false);

  // Load functions
  const loadTestCase = useCallback(async (id: string) => {
    try {
      setLoading(true);
      setError(null);
      const tc = await TestCaseService.getTestCase(id);
      setTestCase(tc);
      setEditableTestCase(tc);
      
      // Load additional data in parallel
      loadRecentTestRuns(id);
      loadExistingBrowserConfigs(tc.projectId);
      loadExistingSecrets(tc.projectId);
    } catch (error: any) {
      console.error('Failed to load test case:', error);
      setError(error.message || 'Failed to load test case');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadRecentTestRuns = useCallback(async (testCaseId: string) => {
    try {
      setTestRunsLoading(true);
      const runs = await TestCaseService.getRecentTestRuns(testCaseId, 3);
      setRecentTestRuns(runs);
    } catch (error: any) {
      console.error('Failed to load recent test runs:', error);
    } finally {
      setTestRunsLoading(false);
    }
  }, []);

  const loadBrowserConfigOptions = useCallback(async () => {
    try {
      const options = await BrowserService.getBrowserConfigOptions();
      setBrowserConfigOptions(options);
    } catch (error) {
      console.error('Failed to load browser config options:', error);
    }
  }, []);

  const loadExistingBrowserConfigs = useCallback(async (projectId: string) => {
    try {
      const browserConfigsData = await BrowserService.getBrowserConfigsByProject(projectId);
      setExistingBrowserConfigs(browserConfigsData);
    } catch (error) {
      console.error('Failed to load existing browser configs:', error);
      setExistingBrowserConfigs([]);
    }
  }, []);

  const loadExistingSecrets = useCallback(async (projectId: string) => {
    try {
      const secretsData = await BrowserService.getSecretsByProject(projectId);
      setExistingSecrets(secretsData);
    } catch (error) {
      console.error('Failed to load existing secrets:', error);
      setExistingSecrets([]);
    }
  }, []);

  // Edit handlers
  const handleGoalChange = useCallback((goal: string) => {
    setEditableTestCase(prev => prev ? { ...prev, goal } : null);
  }, []);

  const handleCategoryChange = useCallback((category: TestCategory) => {
    setEditableTestCase(prev => prev ? { ...prev, category } : null);
  }, []);

  const handlePriorityChange = useCallback((priority: TestPriority) => {
    setEditableTestCase(prev => prev ? { ...prev, priority } : null);
  }, []);

  const handleStartingUrlChange = useCallback((startingUrl: string) => {
    setEditableTestCase(prev => prev ? { ...prev, startingUrl } : null);
  }, []);

  const handleAllowedDomainsChange = useCallback((allowedDomains: string[]) => {
    setEditableTestCase(prev => prev ? { ...prev, allowedDomains } : null);
  }, []);

  const handleRulesChange = useCallback((extraRules: ExtraRule[]) => {
    setEditableTestCase(prev => prev ? { ...prev, extraRules } : null);
  }, []);

  const handleBrowserConfigsChange = useCallback((browserConfigs: BrowserConfig[]) => {
    setEditableTestCase(prev => prev ? { ...prev, browserConfigs } : null);
  }, []);

  const handleExistingBrowserConfigsAdd = useCallback((existingBrowserConfigIds: string[]) => {
    setEditableTestCase(prev => prev ? { ...prev, existingBrowserConfigIds } : null);
  }, []);

  const handleSecretsChange = useCallback((secrets: TestSecret[]) => {
    setEditableTestCase(prev => prev ? { ...prev, secrets } : null);
  }, []);

  const handleExistingSecretsAdd = useCallback((existingSecretIds: string[]) => {
    setEditableTestCase(prev => prev ? { ...prev, existingSecretIds } : null);
  }, []);

  // Secret visibility and copying
  const toggleSecretVisibility = useCallback((secretId: string) => {
    const newVisibleSecrets = new Set(visibleSecrets);
    if (newVisibleSecrets.has(secretId)) {
      newVisibleSecrets.delete(secretId);
    } else {
      newVisibleSecrets.add(secretId);
    }
    setVisibleSecrets(newVisibleSecrets);
  }, [visibleSecrets]);

  const copySecret = useCallback(async (value: string, secretId: string) => {
    try {
      await navigator.clipboard.writeText(value);
      setCopiedSecret(secretId);
      setTimeout(() => setCopiedSecret(null), 2000);
    } catch (error) {
      console.error('Failed to copy secret:', error);
    }
  }, []);

  // Save handlers
  const saveGoal = useCallback(async () => {
    if (!editableTestCase || !testCase) return;
    try {
      const updatedTestCase = await TestCaseService.updateTestCase(editableTestCase.id, {
        test_goal: editableTestCase.goal
      });
      
      // Merge to preserve stats and complex nested data
      const mergedTestCase = {
        ...testCase,
        ...updatedTestCase,
        // Preserve critical stats
        totalRuns: testCase.totalRuns,
        passedRuns: testCase.passedRuns,
        failedRuns: testCase.failedRuns,
        passRate: testCase.passRate,
        // Preserve complex nested data that might not come back from API
        browserConfigs: testCase.browserConfigs,
        secrets: testCase.secrets,
        extraRules: testCase.extraRules
      };
      
      setTestCase(mergedTestCase);
      setEditingGoal(false);
    } catch (error) {
      console.error('Failed to save test case goal:', error);
    }
  }, [editableTestCase, testCase]);

  const saveBasicInfo = useCallback(async () => {
    if (!editableTestCase || !testCase) return;
    try {
      const updatedTestCase = await TestCaseService.updateTestCase(editableTestCase.id, {
        priority: editableTestCase.priority,
        category: editableTestCase.category
      });
      
      // Merge the API response with existing data to preserve stats
      const mergedTestCase = {
        ...testCase,
        ...updatedTestCase,
        // Preserve important stats that might not come back from API
        totalRuns: testCase.totalRuns,
        passedRuns: testCase.passedRuns,
        failedRuns: testCase.failedRuns,
        passRate: testCase.passRate,
        // Preserve complex nested data that might not come back from API
        browserConfigs: testCase.browserConfigs,
        secrets: testCase.secrets,
        extraRules: testCase.extraRules
      };
      
      setTestCase(mergedTestCase);
      setEditingBasicInfo(false);
      setCategoryDropdownOpen(false);
      setPriorityDropdownOpen(false);
    } catch (error) {
      console.error('Failed to save basic information:', error);
    }
  }, [editableTestCase, testCase]);

  const saveConfig = useCallback(async () => {
    if (!editableTestCase || !testCase) return;
    try {
      const updatedTestCase = await TestCaseService.updateTestCase(editableTestCase.id, {
        url_route: editableTestCase.startingUrl,
        allowed_domains: editableTestCase.allowedDomains
      });
      
      // Merge to preserve stats and complex nested data
      const mergedTestCase = {
        ...testCase,
        ...updatedTestCase,
        // Preserve critical stats
        totalRuns: testCase.totalRuns,
        passedRuns: testCase.passedRuns,
        failedRuns: testCase.failedRuns,
        passRate: testCase.passRate,
        // Preserve complex nested data that might not come back from API
        browserConfigs: testCase.browserConfigs,
        secrets: testCase.secrets,
        extraRules: testCase.extraRules
      };
      
      setTestCase(mergedTestCase);
      setEditingConfig(false);
    } catch (error) {
      console.error('Failed to save test case:', error);
    }
  }, [editableTestCase, testCase]);

  const saveRules = useCallback(async () => {
    if (!editableTestCase || !testCase) return;
    try {
      const updatedTestCase = await TestCaseService.updateTestCase(editableTestCase.id, {
        extra_rules: editableTestCase.extraRules.map(rule => rule.description)
      });
      
      // Merge to preserve stats and complex nested data (except extraRules which we're updating)
      const mergedTestCase = {
        ...testCase,
        ...updatedTestCase,
        // Preserve critical stats
        totalRuns: testCase.totalRuns,
        passedRuns: testCase.passedRuns,
        failedRuns: testCase.failedRuns,
        passRate: testCase.passRate,
        // Preserve complex nested data that might not come back from API
        browserConfigs: testCase.browserConfigs,
        secrets: testCase.secrets
        // Note: Don't preserve extraRules since we're updating them
      };
      
      setTestCase(mergedTestCase);
      setEditingRules(false);
    } catch (error) {
      console.error('Failed to save extra rules:', error);
    }
  }, [editableTestCase, testCase]);

  const saveBrowsers = useCallback(async () => {
    if (!editableTestCase || !testCase) return;
    
    try {
      // Separate existing configs (to update) from new configs (to create)
      const existingConfigs: UpdateBrowserConfigWithId[] = [];
      const newConfigs: CreateBrowserConfigRequest[] = [];
      const configsToUnlink: string[] = [];

      // Get the original browser configs to compare
      const originalConfigIds = new Set(testCase.browserConfigs.map(c => c.id));
      const currentConfigIds = new Set(editableTestCase.browserConfigs.map(c => c.id));

      // Find configs that were removed (to unlink)
      originalConfigIds.forEach(id => {
        if (!currentConfigIds.has(id)) {
          configsToUnlink.push(id);
        }
      });

      // Process current configs
      editableTestCase.browserConfigs.forEach(config => {
        if (config.id.startsWith('config-')) {
          // This is a new config (temporary ID)
          newConfigs.push({
            test_case_id: testCase.id,
            browser_config: {
              browser_channel: config.browserChannel,
              user_agent: config.userAgent,
              viewport: {
                width: config.viewport.width,
                height: config.viewport.height
              },
              geolocation: config.geolocation
            }
          });
        } else {
          // This is an existing config to update
          existingConfigs.push({
            id: config.id,
            browser_config: {
              browser_channel: config.browserChannel,
              user_agent: config.userAgent,
              viewport: {
                width: config.viewport.width,
                height: config.viewport.height
              },
              geolocation: config.geolocation
            }
          });
        }
      });

      // Get existing browser config IDs to link (if any)
      const existingBrowserConfigIdsToAdd = editableTestCase.existingBrowserConfigIds || [];

      // Call the bulk update API with all operations
      const response = await BrowserService.bulkUpdateBrowserConfigs({
        browser_configs: existingConfigs,
        new_browser_configs: newConfigs,
        existing_browser_config_ids_to_add: existingBrowserConfigIdsToAdd,
        browser_config_ids_to_unlink: configsToUnlink,
        test_case_id: testCase.id
      });
      
      console.log('Browser configs operations completed:', response);
      
      // Combine updated, created, and linked configs for the UI
      const allUpdatedConfigs = [
        ...response.updated_browser_configs,
        ...response.created_browser_configs,
        ...response.linked_browser_configs
      ].map(backendConfig => ({
        id: backendConfig.id,
        browserChannel: backendConfig.browser_config.browser_channel || '',
        userAgent: backendConfig.browser_config.user_agent || '',
        viewport: backendConfig.browser_config.viewport || { width: 1920, height: 1080 },
        geolocation: backendConfig.browser_config.geolocation
      }));

      // Update the test case state
      const updatedTestCase = {
        ...editableTestCase,
        browserConfigs: allUpdatedConfigs,
        existingBrowserConfigIds: [] // Clear the linked IDs after saving
      };

      setTestCase(updatedTestCase);
      setEditingBrowsers(false);
      
      // Reset dropdown states
      setBrowserChannelDropdowns({});
      setUserAgentDropdowns({});
      setViewportDropdowns({});
      setExistingBrowserConfigDropdownOpen(false);
      
    } catch (error: any) {
      console.error('Failed to save browser configurations:', error);
      alert(`Failed to save browser configurations: ${error.message || 'Unknown error'}`);
    }
  }, [editableTestCase, testCase]);

  const saveSecrets = useCallback(async () => {
    if (!editableTestCase || !testCase) return;
    
    try {
      // Separate existing secrets (to update) from new secrets (to create)
      const existingSecrets: UpdateSecretValueWithId[] = [];
      const newSecrets: CreateSecretValueRequest[] = [];
      const secretsToUnlink: string[] = [];

      // Get the original secret IDs to compare
      const originalSecretIds = new Set(testCase.secrets.map(s => s.id));
      const currentSecretIds = new Set(editableTestCase.secrets.map(s => s.id));

      // Find secrets that were removed (to unlink)
      originalSecretIds.forEach(id => {
        if (!currentSecretIds.has(id)) {
          secretsToUnlink.push(id);
        }
      });

      // Process current secrets
      editableTestCase.secrets.forEach(secret => {
        if (secret.id.startsWith('secret-')) {
          // This is a new secret (temporary ID)
          newSecrets.push({
            test_case_id: testCase.id,
            secret_name: secret.secretName,
            secret_value: secret.value
          });
        } else {
          // This is an existing secret to update
          existingSecrets.push({
            id: secret.id,
            secret_name: secret.secretName,
            secret_value: secret.value
          });
        }
      });

      // Get existing secret IDs to link (if any)
      const existingSecretIdsToAdd = editableTestCase.existingSecretIds || [];

      // Call the bulk update API with all operations
      const response = await BrowserService.bulkUpdateSecretValues({
        secret_values: existingSecrets,
        new_secret_values: newSecrets,
        existing_secret_value_ids_to_add: existingSecretIdsToAdd,
        secret_value_ids_to_unlink: secretsToUnlink,
        test_case_id: testCase.id
      });
      
      console.log('Secret values operations completed:', response);
      
      // Combine updated, created, and linked secrets for the UI
      const allUpdatedSecrets = [
        ...response.updated_secret_values,
        ...response.created_secret_values,
        ...response.linked_secret_values
      ].map(backendSecret => ({
        id: backendSecret.id,
        secretName: backendSecret.secret_name,
        value: backendSecret.secret_value
      }));

      // Update the test case state
      const updatedTestCase = {
        ...editableTestCase,
        secrets: allUpdatedSecrets,
        existingSecretIds: [] // Clear the linked IDs after saving
      };

      setTestCase(updatedTestCase);
      setEditingSecrets(false);
      
      // Reset dropdown states
      setExistingSecretDropdownOpen(false);

    } catch (error: any) {
      console.error('Failed to save secrets:', error);
    }
  }, [editableTestCase, testCase]);

  // Cancel handlers
  const cancelEdit = useCallback((editType: string) => {
    setEditableTestCase({ ...testCase! });
    
    switch (editType) {
      case 'goal':
        setEditingGoal(false);
        break;
      case 'basicInfo':
        setEditingBasicInfo(false);
        setCategoryDropdownOpen(false);
        setPriorityDropdownOpen(false);
        break;
      case 'config':
        setEditingConfig(false);
        break;
      case 'rules':
        setEditingRules(false);
        break;
      case 'browsers':
        setEditingBrowsers(false);
        setBrowserChannelDropdowns({});
        setUserAgentDropdowns({});
        setViewportDropdowns({});
        setExistingBrowserConfigDropdownOpen(false);
        break;
      case 'secrets':
        setEditingSecrets(false);
        setExistingSecretDropdownOpen(false);
        break;
    }
  }, [testCase]);

  // Delete handlers
  const handleDeleteTestCase = useCallback(() => {
    setShowDeleteModal(true);
    setDeleteError(null);
  }, []);

  const confirmDeleteTestCase = useCallback(async () => {
    if (!testCase?.id) return;
    
    try {
      setDeleteLoading(true);
      setDeleteError(null);
      
      await TestCaseService.deleteTestCase(testCase.id);
      navigate('/');
    } catch (error: any) {
      console.error('Failed to delete test case:', error);
      setDeleteError(error.message || 'Failed to delete test case');
    } finally {
      setDeleteLoading(false);
    }
  }, [testCase, navigate]);

  const cancelDeleteTestCase = useCallback(() => {
    setShowDeleteModal(false);
    setDeleteError(null);
  }, []);

  // Run test handlers
  const handleRunTest = useCallback(() => {
    setShowRunTestModal(true);
  }, []);

  const handleCloseRunTestModal = useCallback(() => {
    setShowRunTestModal(false);
  }, []);

  const handleTestStarted = useCallback((testRunId: string) => {
    console.log('Test started with ID:', testRunId);
    // Optionally refresh recent test runs
    if (testCase?.id) {
      loadRecentTestRuns(testCase.id);
    }
  }, [testCase?.id, loadRecentTestRuns]);

  // Effects
  useEffect(() => {
    if (testCaseId) {
      loadTestCase(testCaseId);
    }
  }, [testCaseId, loadTestCase]);

  useEffect(() => {
    loadBrowserConfigOptions();
  }, [loadBrowserConfigOptions]);

  return {
    // State
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
  };
};
