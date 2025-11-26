import { useCallback } from 'react';
import { FrontendTestCase, TestCategory, TestPriority, BrowserConfig, TestSecret, ExtraRule } from '../types';

interface UseTestCaseActionsProps {
  setEditableTestCase: React.Dispatch<React.SetStateAction<FrontendTestCase | null>>;
}

export const useTestCaseActions = ({ 
  setEditableTestCase 
}: UseTestCaseActionsProps) => {
  const handleGoalChange = useCallback((goal: string) => {
    setEditableTestCase(prev => prev ? { ...prev, goal } : null);
  }, [setEditableTestCase]);

  const handleCategoryChange = useCallback((category: TestCategory) => {
    setEditableTestCase(prev => prev ? { ...prev, category } : null);
  }, [setEditableTestCase]);

  const handlePriorityChange = useCallback((priority: TestPriority) => {
    setEditableTestCase(prev => prev ? { ...prev, priority } : null);
  }, [setEditableTestCase]);

  const handleStartingUrlChange = useCallback((startingUrl: string) => {
    setEditableTestCase(prev => prev ? { ...prev, startingUrl } : null);
  }, [setEditableTestCase]);

  const handleAllowedDomainsChange = useCallback((allowedDomains: string[]) => {
    setEditableTestCase(prev => prev ? { ...prev, allowedDomains } : null);
  }, [setEditableTestCase]);

  const handleRulesChange = useCallback((extraRules: ExtraRule[]) => {
    setEditableTestCase(prev => prev ? { ...prev, extraRules } : null);
  }, [setEditableTestCase]);

  const handleBrowserConfigsChange = useCallback((browserConfigs: BrowserConfig[]) => {
    setEditableTestCase(prev => prev ? { ...prev, browserConfigs } : null);
  }, [setEditableTestCase]);

  const handleExistingBrowserConfigsAdd = useCallback((existingBrowserConfigIds: string[]) => {
    setEditableTestCase(prev => prev ? { ...prev, existingBrowserConfigIds } : null);
  }, [setEditableTestCase]);

  const handleSecretsChange = useCallback((secrets: TestSecret[]) => {
    setEditableTestCase(prev => prev ? { ...prev, secrets } : null);
  }, [setEditableTestCase]);

  const handleExistingSecretsAdd = useCallback((existingSecretIds: string[]) => {
    setEditableTestCase(prev => prev ? { ...prev, existingSecretIds } : null);
  }, [setEditableTestCase]);

  return {
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
  };
};
