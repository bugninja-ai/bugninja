import { useState, useEffect, useCallback } from 'react';
import { FrontendTestCase } from '../types';
import { TestCaseService } from '../services/testCaseService';
import { BrowserService } from '../../settings/services/browserService';
import { BrowserConfigOptions, BrowserConfigData, SecretValue } from '../../settings/types';
import { useTestCaseActions } from './useTestCaseActions';
import { useTestCaseSecrets } from './useTestCaseSecrets';
import { useTestCaseDelete } from './useTestCaseDelete';
import { useDropdowns } from '../../../shared/hooks/useDropdowns';
import { useAsyncOperation } from '../../../shared/hooks/useAsyncOperation';

export const useTestCaseDetailRefactored = (testCaseId: string | undefined) => {
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

  // Browser config data
  const [browserConfigOptions, setBrowserConfigOptions] = useState<BrowserConfigOptions | null>(null);
  const [existingBrowserConfigs, setExistingBrowserConfigs] = useState<BrowserConfigData[]>([]);
  const [existingSecrets, setExistingSecrets] = useState<SecretValue[]>([]);
  const [recentTestRuns, setRecentTestRuns] = useState<any[]>([]);
  const [testRunsLoading, setTestRunsLoading] = useState(false);

  // Use extracted hooks
  const dropdowns = useDropdowns();
  const secretsHook = useTestCaseSecrets();
  const deleteHook = useTestCaseDelete(testCase?.id);
  const actionsHook = useTestCaseActions({ setEditableTestCase });
  const saveOperations = useAsyncOperation();

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
    } catch (error: any) {
      console.error('Failed to load browser config options:', error);
    }
  }, []);

  const loadExistingBrowserConfigs = useCallback(async (projectId: string) => {
    try {
      const browserConfigsData = await BrowserService.getBrowserConfigsByProject(projectId);
      setExistingBrowserConfigs(browserConfigsData);
    } catch (error: any) {
      console.error('Failed to load browser configs:', error);
    }
  }, []);

  const loadExistingSecrets = useCallback(async (projectId: string) => {
    try {
      const secretsData = await BrowserService.getSecretsByProject(projectId);
      setExistingSecrets(secretsData);
    } catch (error: any) {
      console.error('Failed to load secrets:', error);
    }
  }, []);

  // Save handlers using async operation hook
  const saveGoal = useCallback(async () => {
    if (!editableTestCase || !testCase) return;
    
    await saveOperations.execute(async () => {
      const updated = await TestCaseService.updateTestCase(testCase.id, {
        test_goal: editableTestCase.goal
      });
      setTestCase(updated);
      setEditingGoal(false);
    });
  }, [editableTestCase, testCase, saveOperations]);

  const saveBasicInfo = useCallback(async () => {
    if (!editableTestCase || !testCase) return;
    
    await saveOperations.execute(async () => {
      const updated = await TestCaseService.updateTestCase(testCase.id, {
        category: editableTestCase.category,
        priority: editableTestCase.priority
      });
      setTestCase(updated);
      setEditingBasicInfo(false);
    });
  }, [editableTestCase, testCase, saveOperations]);

  const saveConfig = useCallback(async () => {
    if (!editableTestCase || !testCase) return;
    
    await saveOperations.execute(async () => {
      const updated = await TestCaseService.updateTestCase(testCase.id, {
        url_route: editableTestCase.startingUrl,
        allowed_domains: editableTestCase.allowedDomains
      });
      setTestCase(updated);
      setEditingConfig(false);
    });
  }, [editableTestCase, testCase, saveOperations]);

  const saveRules = useCallback(async () => {
    if (!editableTestCase || !testCase) return;
    
    await saveOperations.execute(async () => {
      const updated = await TestCaseService.updateTestCase(testCase.id, {
        extra_rules: editableTestCase.extraRules.map(rule => rule.description)
      });
      setTestCase(updated);
      setEditingRules(false);
    });
  }, [editableTestCase, testCase, saveOperations]);

  const saveBrowsers = useCallback(async () => {
    if (!editableTestCase || !testCase) return;
    
    await saveOperations.execute(async () => {
      // Browser configs need separate API calls - simplified for now
      setTestCase({ ...testCase, ...editableTestCase });
      setEditingBrowsers(false);
    });
  }, [editableTestCase, testCase, saveOperations]);

  const saveSecrets = useCallback(async () => {
    if (!editableTestCase || !testCase) return;
    
    await saveOperations.execute(async () => {
      // Secrets need separate API calls - simplified for now
      setTestCase({ ...testCase, ...editableTestCase });
      setEditingSecrets(false);
    });
  }, [editableTestCase, testCase, saveOperations]);

  const cancelEdit = useCallback((editType: string) => {
    setEditableTestCase({ ...testCase! });
    
    switch (editType) {
      case 'goal':
        setEditingGoal(false);
        break;
      case 'basicInfo':
        setEditingBasicInfo(false);
        break;
      case 'config':
        setEditingConfig(false);
        break;
      case 'rules':
        setEditingRules(false);
        break;
      case 'browsers':
        setEditingBrowsers(false);
        break;
      case 'secrets':
        setEditingSecrets(false);
        break;
    }
  }, [testCase]);

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
    dropdowns,
    
    // Data
    browserConfigOptions,
    existingBrowserConfigs,
    existingSecrets,
    recentTestRuns,
    testRunsLoading,
    
    // Secrets
    ...secretsHook,
    
    // Delete modal
    ...deleteHook,
    
    // Handlers
    ...actionsHook,
    
    // Save handlers
    saveGoal,
    saveBasicInfo,
    saveConfig,
    saveRules,
    saveBrowsers,
    saveSecrets,
    
    // Cancel handler
    cancelEdit,
    
    // Reload function
    loadTestCase,
    
    // Save loading state
    saveLoading: saveOperations.loading,
    saveError: saveOperations.error,
  };
};
