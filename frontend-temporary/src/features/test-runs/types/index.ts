import { TestStatus, TestCase } from '../../test-cases/types';

export interface BrainAction {
  id: string;
  actionType: string; // e.g., "Navigate to URL", "Fill text input", "Click login button"
  icon?: string;
  xpath?: string;
  url?: string; // The URL where this action was performed
  inputText?: string; // Text that was entered
  secretUsed?: string; // Name of secret that was used
  evaluatePreviousGoal: string;
  nextGoal: string;
  memory: string;
  status: 'passed' | 'failed';
  screenshot?: string;
}

export interface BrainState {
  id: string;
  stepNumber: number;
  description: string;
  actions: BrainAction[];
  status: TestStatus;
  duration: number;
}

export interface TestStep {
  id: string;
  stepNumber: number;
  description: string;
  expected?: string; // Optional for brain state steps
  actual?: string; // Optional for brain state steps
  status: TestStatus;
  duration: number; // in seconds
  screenshot?: string;
  error?: string;
  brainState?: BrainState; // This step is a brain state with multiple actions
}

export interface TestRun {
  id: string;
  testCaseId: string;
  testCase: TestCase;
  status: TestStatus;
  startedAt: Date;
  finishedAt?: Date;
  duration: number; // in seconds
  steps: TestStep[];
  passedSteps: number;
  failedSteps: number;
  totalSteps: number;
  environment: string;
  browser: string;
  userAgent: string;
  error?: string;
  gif?: string;
  runType?: string; // Type of run: 'AGENTIC', 'REPLAY', 'REPLAY_WITH_HEALING'
}

export interface TestStatistics {
  totalTests: number;
  passedTests: number;
  failedTests: number;
  pendingTests: number;
  skippedTests: number;
  passRate: number;
}
