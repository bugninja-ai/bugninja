import React, { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { 
  Clock,
  AlertCircle,
  Loader2,
  RefreshCw
} from 'lucide-react';
import { useTestRuns } from './hooks/useTestRuns';
import { useProjects } from '../../shared/hooks/useProjects';
import { TestCaseService } from '../test-cases/services/testCaseService';
import { FrontendTestCase } from '../test-cases/types';
import { Pagination } from '../../shared/components/Pagination';
import { ViewSwitcher, ViewPreferenceModal, ViewType } from '../../shared/components';
import { TestRunFilters } from './components/TestRunFilters';
import { TestRunListItem } from './components/TestRunListItem';
import { TestRunStats } from './components/TestRunStats';
import { TestRunTableView } from './components/TestRunTableView';

const TestRunsPage: React.FC = () => {
  // Get URL search parameters
  const [searchParams] = useSearchParams();
  
  // Get selected project
  const { selectedProject } = useProjects();
  
  // Dropdown states
  const [statusDropdownOpen, setStatusDropdownOpen] = useState(false);
  const [testCaseDropdownOpen, setTestCaseDropdownOpen] = useState(false);
  const [browserDropdownOpen, setBrowserDropdownOpen] = useState(false);

  // View state
  const [currentView, setCurrentView] = useState<ViewType>('list');
  const [showViewPreferenceModal, setShowViewPreferenceModal] = useState(false);

  // Use the test runs hook
  const {
    data: testRuns,
    loading: testRunsLoading,
    error: testRunsError,
    totalCount,
    page,
    pageSize,
    totalPages,
    hasNext,
    hasPrevious,
    refetch,
    setPage,
    setSearch,
    setStatus,
    setSortOrder,
    setTestCaseId,
    filters
  } = useTestRuns({
    projectId: selectedProject?.id,
    pageSize: currentView === 'table' ? 25 : 10
  });

  // Browser filtering state
  const [selectedBrowserId, setSelectedBrowserId] = useState<string | undefined>();

  // State for all test cases in the project (for dropdown options)
  const [allTestCases, setAllTestCases] = useState<FrontendTestCase[]>([]);


  // Handle URL query parameters on component mount
  useEffect(() => {
    const testCaseParam = searchParams.get('testCase');
    if (testCaseParam) {
      setTestCaseId(testCaseParam);
    }
  }, [searchParams, setTestCaseId]);

  // Load view preference from localStorage
  useEffect(() => {
    const savedView = localStorage.getItem('testRunsViewPreference') as ViewType;
    const viewPreferenceShown = localStorage.getItem('viewPreferenceModalShown');

    if (savedView) {
      setCurrentView(savedView);
    } else if (!viewPreferenceShown) {
      setShowViewPreferenceModal(true);
    }
  }, []);

  // Fetch all test cases for the project (for dropdown options)
  useEffect(() => {
    const fetchAllTestCases = async () => {
      if (!selectedProject?.id) {
        return;
      }
      
      try {

        const response = await TestCaseService.getTestCases({
          project_id: selectedProject.id,
          page_size: 100 // Maximum allowed by backend
        });
        setAllTestCases(response.items);
      } catch (error) {
        console.error('Failed to fetch test cases for dropdown:', error);
        setAllTestCases([]);
      } finally {

      }
    };

    fetchAllTestCases();
  }, [selectedProject?.id]);

  // Apply client-side browser filtering (since backend doesn't support it)
  const filteredRuns = (testRuns || []).filter(run => {
    if (!selectedBrowserId) return true;
    const browserConfig = run.browser_config || run.browserConfig;
    return browserConfig?.id === selectedBrowserId;
  });

  // Calculate pagination for filtered results when browser filtering is applied
  const isBrowserFiltered = selectedBrowserId !== undefined;
  const currentPageSize = pageSize;
  const filteredTotalCount = filteredRuns.length;
  const filteredTotalPages = Math.ceil(filteredTotalCount / currentPageSize);
  const filteredCurrentPage = isBrowserFiltered ? 1 : page; // Reset to page 1 when filtering
  const filteredHasNext = isBrowserFiltered ? filteredCurrentPage < filteredTotalPages : hasNext;
  const filteredHasPrevious = isBrowserFiltered ? filteredCurrentPage > 1 : hasPrevious;

  // Use filtered pagination values when browser filtering is active
  const effectivePage = isBrowserFiltered ? filteredCurrentPage : page;
  const effectiveTotalPages = isBrowserFiltered ? filteredTotalPages : totalPages;
  const effectiveHasNext = isBrowserFiltered ? filteredHasNext : hasNext;
  const effectiveHasPrevious = isBrowserFiltered ? filteredHasPrevious : hasPrevious;

  // Apply pagination to filtered results when browser filtering is active
  const paginatedFilteredRuns = isBrowserFiltered 
    ? filteredRuns.slice((filteredCurrentPage - 1) * currentPageSize, filteredCurrentPage * currentPageSize)
    : filteredRuns;

  // Generate test case dropdown options
  const testCaseOptions = React.useMemo(() => {
    const testCaseMap = new Map<string, string>();
    
    // First, add test cases from current test runs
    if (testRuns) {
      testRuns.forEach(run => {
        const testCaseId = run.test_case?.id || run.testCase?.id;
        const testCaseName = run.test_case?.test_name || run.testCase?.title;
        if (testCaseId && testCaseName) {
          testCaseMap.set(testCaseId, testCaseName);
        }
      });
    }
    
    // Then, add all test cases from the project
    allTestCases.forEach(testCase => {
      if (testCase.id && testCase.title) {
        testCaseMap.set(testCase.id, testCase.title);
      }
    });
    
    return Array.from(testCaseMap.entries()).map(([id, name]) => ({ id, name }));
  }, [testRuns, allTestCases]);

  const browserOptions = React.useMemo(() => {
    if (!testRuns) return [];
    const browserConfigMap = new Map<string, string>();
    testRuns.forEach(run => {
      const browserConfig = run.browser_config || run.browserConfig;
      if (browserConfig) {
        const browserId = browserConfig.id;
        const userAgent = browserConfig.browser_config?.user_agent || browserConfig.userAgent;
        const viewport = browserConfig.browser_config?.viewport || browserConfig.viewport;
        let browserName = 'Unknown Browser';
        
        if (userAgent) {
          if (userAgent.includes('Chrome')) browserName = 'Chrome';
          else if (userAgent.includes('Firefox')) browserName = 'Firefox';
          else if (userAgent.includes('Safari')) browserName = 'Safari';
          else if (userAgent.includes('Edge')) browserName = 'Edge';
        }
        
        if (viewport) {
          browserName += ` (${viewport.width}x${viewport.height})`;
        }
        
        if (browserId) {
          browserConfigMap.set(browserId, browserName);
        }
      }
    });
    return Array.from(browserConfigMap.entries()).map(([id, name]) => ({ id, name }));
  }, [testRuns]);

  // Format options for dropdowns
  const testCaseDropdownOptions = React.useMemo(() => {
    return [
      { value: 'all', label: 'All test cases' },
      ...testCaseOptions.map(testCase => ({
        value: testCase.id,
        label: testCase.name
      }))
    ];
  }, [testCaseOptions]);

  const browserDropdownOptions = [
    { value: 'all', label: 'All browsers' },
    ...browserOptions.map(browserConfig => ({
      value: browserConfig.id,
      label: browserConfig.name
    }))
  ];

  const handleClearFilters = () => {
    setSearch('');
    setStatus(undefined);
    setTestCaseId(undefined);
    setSelectedBrowserId(undefined);
  };

  const handleViewChange = (view: ViewType) => {
    setCurrentView(view);
    localStorage.setItem('testRunsViewPreference', view);
    setPage(1); // Reset to first page when changing views
  };

  const handleViewPreferenceSelect = (view: ViewType) => {
    setCurrentView(view);
    localStorage.setItem('testRunsViewPreference', view);
    localStorage.setItem('viewPreferenceModalShown', 'true');
  };

  const handleViewPreferenceDontShowAgain = () => {
    localStorage.setItem('viewPreferenceModalShown', 'true');
    setShowViewPreferenceModal(false);
  };

  const renderContent = () => {
    if (testRunsLoading) {
      return (
        <div className="bg-white rounded-lg p-8 border border-gray-200 text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-gray-400" />
          <p className="text-gray-600">Loading test runs...</p>
        </div>
      );
    }

    if (testRunsError) {
      return (
        <div className="bg-white rounded-lg p-8 border border-gray-200 text-center">
          <AlertCircle className="w-8 h-8 mx-auto mb-4 text-gray-400" />
          <p className="text-red-600 mb-4">{testRunsError}</p>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Try again
          </button>
        </div>
      );
    }

    if (paginatedFilteredRuns.length === 0) {
      return (
        <div className="bg-white rounded-lg p-12 border border-gray-200 text-center">
          <div className="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center mx-auto mb-4">
            <Clock className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-semibold text-gray-800 mb-2">No test runs found</h3>
          <p className="text-gray-600 mb-6">Try adjusting your filters or run some tests to see results here.</p>
          <Link
            to="/"
            className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors"
          >
            View test cases
          </Link>
        </div>
      );
    }

    return (
      <>
        {currentView === 'list' ? (
          <div className="space-y-3">
            {paginatedFilteredRuns.map((run: any) => (
              <TestRunListItem key={run.id} run={run} />
            ))}
          </div>
        ) : (
          <TestRunTableView runs={paginatedFilteredRuns} />
        )}

        {/* Pagination */}
        <Pagination
          currentPage={effectivePage}
          totalPages={effectiveTotalPages}
          onPageChange={isBrowserFiltered ? () => {} : setPage} // Disable pagination when browser filtering
          hasNext={effectiveHasNext}
          hasPrevious={effectiveHasPrevious}
        />
      </>
    );
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Test runs</h1>
          <p className="mt-1 text-gray-600">
            {filters.testCaseId ? (
              <>Runs for test case: <span className="font-medium">{testCaseOptions.find(tc => tc.id === filters.testCaseId)?.name || filters.testCaseId}</span></>
            ) : (
              'View and analyze past test run results'
            )}
          </p>
        </div>
        <div className="mt-4 sm:mt-0 flex items-center space-x-4">
          <ViewSwitcher
            currentView={currentView}
            onViewChange={handleViewChange}
          />
          <div className="text-sm text-gray-500">
            {isBrowserFiltered ? (
              `Showing ${paginatedFilteredRuns.length} of ${filteredRuns.length} filtered test runs`
            ) : (
              `Showing ${((page - 1) * pageSize) + 1}-${Math.min(page * pageSize, totalCount)} of ${totalCount} test runs`
            )}
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <TestRunStats
        totalCount={totalCount}
        testRuns={testRuns}
        filteredRuns={filteredRuns}
        isBrowserFiltered={isBrowserFiltered}
      />

      {/* Filters */}
      <TestRunFilters
        search={filters.search}
        status={filters.status}
        testCaseId={filters.testCaseId}
        selectedBrowserId={selectedBrowserId}
        sortOrder={filters.sortOrder}
        onSearchChange={setSearch}
        onStatusChange={setStatus}
        onTestCaseChange={setTestCaseId}
        onBrowserChange={setSelectedBrowserId}
        onSortOrderChange={setSortOrder}
        onClearFilters={handleClearFilters}
        statusDropdownOpen={statusDropdownOpen}
        setStatusDropdownOpen={setStatusDropdownOpen}
        testCaseDropdownOpen={testCaseDropdownOpen}
        setTestCaseDropdownOpen={setTestCaseDropdownOpen}
        browserDropdownOpen={browserDropdownOpen}
        setBrowserDropdownOpen={setBrowserDropdownOpen}
        testCaseOptions={testCaseDropdownOptions}
        browserOptions={browserDropdownOptions}
      />

      {/* Test Runs List */}
      <div className="space-y-4">
        {renderContent()}
      </div>

      {/* View Preference Modal */}
      <ViewPreferenceModal
        isOpen={showViewPreferenceModal}
        onClose={() => setShowViewPreferenceModal(false)}
        onSelectView={handleViewPreferenceSelect}
        onDontShowAgain={handleViewPreferenceDontShowAgain}
      />
    </div>
  );
};

export default TestRunsPage;
