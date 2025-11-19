import { useState, useEffect, useCallback, useRef } from 'react';
import { TestRun } from '../../test-runs/types';
import { TestCaseService } from '../../test-cases/services/testCaseService';

export interface UseTestRunDetailResult {
  testRun: TestRun | null;
  loading: boolean;
  error: string | null;
  modalOpen: boolean;
  selectedScreenshot: string;
  selectedActionData: any;
  isPolling: boolean;
  openScreenshotModal: (screenshot: string, actionData: any) => void;
  closeModal: () => void;
  refetch: (runId: string) => Promise<void>;
}

export const useTestRunDetail = (runId?: string): UseTestRunDetailResult => {
  const [testRun, setTestRun] = useState<TestRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedScreenshot, setSelectedScreenshot] = useState<string>('');
  const [selectedActionData, setSelectedActionData] = useState<any>(null);
  const [isPolling, setIsPolling] = useState(false);
  
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const scrollPositionRef = useRef<number>(0);
  const shouldScrollToBottomRef = useRef<boolean>(false);

  const transformBackendTestRun = useCallback((backendData: any): TestRun => {
    // Map status from current_state
    const statusMap: { [key: string]: 'passed' | 'failed' | 'pending' } = {
      'PASSED': 'passed',
      'FAILED': 'failed',
      'PENDING': 'pending',
      'RUNNING': 'pending', // Keep RUNNING as pending to continue polling
      'FINISHED': 'passed', // Assuming FINISHED means successful completion
      'ERROR': 'failed'
    };

    // Extract browser information
    const browserConfig = backendData.browser_config?.browser_config;
    const userAgent = browserConfig?.user_agent || '';
    const viewport = browserConfig?.viewport || { width: 1920, height: 1080 };
    
    // Determine browser name from user agent
    let browserName = 'Unknown Browser';
    if (userAgent.includes('Safari') && !userAgent.includes('Chrome')) {
      browserName = 'Safari';
    } else if (userAgent.includes('Chrome')) {
      browserName = 'Chrome';
    } else if (userAgent.includes('Firefox')) {
      browserName = 'Firefox';
    } else if (userAgent.includes('Edge')) {
      browserName = 'Edge';
    }

    // Transform brain states to steps
    // For replay runs, we should show simplified steps without AI brain state details
    const isReplayRun = backendData.run_type === 'REPLAY';
    const steps = backendData.brain_states?.map((brainState: any, index: number) => {
      // Get the first history element for basic step info

      
      // Determine step status based on history elements
      const hasFailedElement = brainState.history_elements?.some((he: any) => he.history_element_state === 'FAILED');
      const stepStatus = hasFailedElement ? 'failed' : 'passed';
      
      // Transform history elements to actions
      const actions = brainState.history_elements?.map((historyElement: any) => {
        const action = historyElement.action;
        let actionType = 'Unknown Action';
        let actionDetails: any = {};
        
        // Determine action type from the action object
        if (action.go_to_url) {
          actionType = 'Navigate to URL';
          actionDetails.url = action.go_to_url.url;
        } else if (action.input_text) {
          actionType = 'Fill text input';
          let inputText = action.input_text.text;
          
          // Handle secrets - extract secret name and mark as secret
          const secretMatch = inputText.match(/<secret>([^<]+)<\/secret>/);
          if (secretMatch) {
            const secretName = secretMatch[1];
            actionDetails.inputText = secretName;
            actionDetails.isSecret = true;
            actionType = 'Fill password/secret input';
          } else {
            actionDetails.inputText = inputText;
            actionDetails.isSecret = false;
          }
          
          actionDetails.xpath = historyElement.dom_element_data?.xpath;
        } else if (action.click_element_by_index) {
          actionType = 'Click element';
          actionDetails.xpath = historyElement.dom_element_data?.xpath;
        } else if (action.done) {
          actionType = 'Test completed';
          actionDetails.resultMessage = action.done.text;
        }
        
        return {
          id: historyElement.id,
          actionType,
          status: historyElement.history_element_state === 'FAILED' ? 'failed' : 'passed',
          screenshot: historyElement.screenshot || null,
          xpath: actionDetails.xpath,
          url: actionDetails.url,
          inputText: actionDetails.inputText,
          resultMessage: actionDetails.resultMessage,
          isSecret: actionDetails.isSecret,
          evaluatePreviousGoal: brainState.evaluation_previous_goal,
          nextGoal: brainState.next_goal,
          memory: brainState.memory
        };
      }) || [];

      return {
        id: brainState.id,
        stepNumber: index + 1,
        description: brainState.next_goal || `Step ${index + 1}`,
        status: stepStatus,
        duration: 0, // Not provided in backend data
        brainState: { // Always include brain state, but ActionStep will handle display logic
          id: brainState.id,
          evaluatePreviousGoal: brainState.evaluation_previous_goal,
          nextGoal: brainState.next_goal,
          memory: brainState.memory,
          actions
        }
      };
    }) || [];

    // Calculate totals
    const totalSteps = steps.length;
    const passedSteps = steps.filter((step: any) => step.status === 'passed').length;
    const failedSteps = steps.filter((step: any) => step.status === 'failed').length;

    // Use real test case data from backend if available
    const realTestCase = backendData.test_case;
    const testCase: any = {
      id: realTestCase?.id || backendData.test_traversal_id,
      code: realTestCase?.id ? `TC-${realTestCase.id.slice(-8)}` : `TR-${backendData.id.slice(-8)}`,
      title: realTestCase?.test_name || `Test Run - ${backendData.id.slice(-8)}`,
      description: realTestCase?.test_description || 'Automated test execution',
      goal: realTestCase?.test_goal || 'Execute test case objectives',
      browserConfigs: [{
        id: backendData.browser_config?.id || 'unknown',
        browserChannel: `${browserName} - ${viewport.width}x${viewport.height}`,
        userAgent: userAgent,
        viewport: viewport,
        geolocation: browserConfig?.geolocation
      }]
    };

    // Calculate duration if we have both start and finish times
    let duration = 0;
    if (backendData.finished_at && backendData.started_at) {
      duration = (new Date(backendData.finished_at).getTime() - new Date(backendData.started_at).getTime()) / 1000;
    }

    return {
      id: backendData.id,
      testCaseId: backendData.test_case?.id || backendData.test_traversal_id,
      testCase,
      status: statusMap[backendData.current_state] || 'pending',
      startedAt: new Date(backendData.started_at),
      finishedAt: backendData.finished_at ? new Date(backendData.finished_at) : undefined,
      duration: duration,
      environment: backendData.origin === 'CI/CD' ? 'production' : 'development',
      browser: browserName,
      userAgent: userAgent,
      totalSteps,
      passedSteps,
      failedSteps,
      steps,
      gif: backendData.run_gif || null,
      runType: backendData.run_type || 'AGENTIC' // Add run type to frontend model
    };
  }, []);

  const loadTestRun = useCallback(async (id: string, isPollingCall = false) => {
    try {
      if (!isPollingCall) {
        setLoading(true);
      }
      setError(null);
      const backendData = await TestCaseService.getTestRun(id);
      const transformedRun = transformBackendTestRun(backendData);
      
      setTestRun(transformedRun);
      
      // For polling calls, always scroll to bottom if test is still running
      if (isPollingCall) {
        const isStillRunning = ['pending'].includes(transformedRun.status);
        if (isStillRunning) {
          console.log('Polling update - scrolling to bottom');
          shouldScrollToBottomRef.current = true;
        }
      }
      
      // Check if test is still running to determine if we should continue polling
      const isStillRunning = ['pending'].includes(transformedRun.status);
      
      if (isPollingCall && !isStillRunning) {
        // Test completed, stop polling
        setIsPolling(false);
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
      }
      
      return isStillRunning;
    } catch (error) {
      console.error('Failed to load test run:', error);
      setError('Failed to load test run details');
      return false;
    } finally {
      if (!isPollingCall) {
        setLoading(false);
      }
    }
  }, [transformBackendTestRun]);

  const openScreenshotModal = useCallback((screenshot: string, actionData: any) => {
    // Save current scroll position before opening modal
    scrollPositionRef.current = window.scrollY;
    setSelectedScreenshot(screenshot);
    setSelectedActionData(actionData);
    setModalOpen(true);
  }, []);

  const closeModal = useCallback(() => {
    setModalOpen(false);
    setSelectedScreenshot('');
    setSelectedActionData(null);
    
    // Restore scroll position after modal closes
    setTimeout(() => {
      window.scrollTo({
        top: scrollPositionRef.current,
        behavior: 'auto'
      });
    }, 50);
  }, []);

  const refetch = useCallback(async (id: string) => {
    await loadTestRun(id);
  }, [loadTestRun]);

  const startPolling = useCallback((id: string) => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
    }
    
    setIsPolling(true);
    pollingIntervalRef.current = setInterval(async () => {
      const isStillRunning = await loadTestRun(id, true);
      if (!isStillRunning) {
        setIsPolling(false);
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
      }
    }, 3000); // Poll every 3 seconds
  }, [loadTestRun]);

  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  // Handle auto-scroll when new content is added
  useEffect(() => {
    if (shouldScrollToBottomRef.current && testRun) {
      shouldScrollToBottomRef.current = false;
      
      // Use multiple approaches to ensure scroll happens
      const scrollToBottom = () => {
        const scrollHeight = Math.max(
          document.documentElement.scrollHeight,
          document.body.scrollHeight
        );
        
        window.scrollTo({
          top: scrollHeight,
          behavior: 'smooth'
        });
        
        console.log(`Auto-scrolled to bottom - scrollHeight: ${scrollHeight}`);
      };
      
      // Try multiple times with different delays to ensure it works
      requestAnimationFrame(() => {
        setTimeout(scrollToBottom, 100);
        setTimeout(scrollToBottom, 300);
        setTimeout(scrollToBottom, 500);
      });
    }
  }, [testRun]);

  // Load test run when runId changes
  useEffect(() => {
    if (runId) {
      loadTestRun(runId).then((isStillRunning) => {
        if (isStillRunning) {
          startPolling(runId);
        }
      });
    }
    
    // Cleanup polling on unmount or runId change
    return () => {
      stopPolling();
    };
  }, [runId, loadTestRun, startPolling, stopPolling]);

  return {
    testRun,
    loading,
    error,
    modalOpen,
    selectedScreenshot,
    selectedActionData,
    isPolling,
    openScreenshotModal,
    closeModal,
    refetch
  };
};
