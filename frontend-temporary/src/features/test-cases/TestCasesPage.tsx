import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Plus, 
  CheckCircle,
  XCircle,
  Clock,
  FileText,
  Loader2,
  RefreshCw,
  AlertCircle
} from 'lucide-react';

import { useTestCases } from './hooks/useTestCases';
import { useProjects } from '../../shared/hooks/useProjects';
import { StatsCard } from '../../shared/components/StatsCard';
import { Pagination } from '../../shared/components/Pagination';
import { ViewSwitcher, ViewPreferenceModal, ViewType } from '../../shared/components';
import { TestCaseFilters } from './components/TestCaseFilters';
import { TestCaseListItem, TestCaseTableView } from './components';

const TestCasesPage: React.FC = () => {
  // Get selected project
  const { selectedProject } = useProjects();
  
  // View preferences state
  const [currentView, setCurrentView] = useState<ViewType>('list');
  const [showViewPreferenceModal, setShowViewPreferenceModal] = useState(false);
  
  // Get test cases for the selected project
  const {
    data: testCases,
    loading: testCasesLoading,
    error: testCasesError,
    totalCount,
    page,
    pageSize,
    totalPages,
    hasNext,
    hasPrevious,
    refetch,
    setPage,
    setSearch,
    setPriority,
    setCategory,
    setPageSize,
    setSortOrder,
    filters
  } = useTestCases({
    projectId: selectedProject?.id,
    pageSize: currentView === 'table' ? 25 : 15
  });

  // Dropdown states
  const [priorityDropdownOpen, setPriorityDropdownOpen] = useState(false);
  const [categoryDropdownOpen, setCategoryDropdownOpen] = useState(false);

  // Load view preference from localStorage on mount
  useEffect(() => {
    const savedView = localStorage.getItem('testCasesViewPreference') as ViewType;
    const viewPreferenceShown = localStorage.getItem('viewPreferenceModalShown');
    
    if (savedView) {
      setCurrentView(savedView);
    } else if (!viewPreferenceShown) {
      // Show view preference modal for first-time users
      setShowViewPreferenceModal(true);
    }
  }, []);

  // Update page size when view changes
  useEffect(() => {
    const newPageSize = currentView === 'table' ? 25 : 15;
    setPageSize(newPageSize);
  }, [currentView, setPageSize]);

  const handleViewChange = (view: ViewType) => {
    setCurrentView(view);
    localStorage.setItem('testCasesViewPreference', view);
    setPage(1); // Reset to first page when changing views
  };

  const handleViewPreferenceSelect = (view: ViewType) => {
    setCurrentView(view);
    localStorage.setItem('testCasesViewPreference', view);
  };

  const handleViewPreferenceDontShowAgain = () => {
    localStorage.setItem('viewPreferenceModalShown', 'true');
  };

  // Calculate statistics from test cases
  const stats = React.useMemo(() => {
    if (!testCases || testCases.length === 0) {
      return {
        totalTests: totalCount,
        passedTests: 0, // Keep passedTests for backward compatibility with UI components
        failedTests: 0,
        pendingTests: totalCount,
        skippedTests: 0,
        passRate: 0
      };
    }

    const finishedTests = testCases.filter(tc => tc.status === 'finished').length;
    const failedTests = testCases.filter(tc => tc.status === 'failed').length;
    const pendingTests = testCases.filter(tc => tc.status === 'pending').length;
    const skippedTests = testCases.filter(tc => tc.status === 'skipped').length;
    
    // Calculate overall pass rate from all test cases
    const totalRunsAcrossAllCases = testCases.reduce((sum, tc) => sum + tc.totalRuns, 0);
    const totalPassedRunsAcrossAllCases = testCases.reduce((sum, tc) => sum + tc.passedRuns, 0);
    const passRate = totalRunsAcrossAllCases > 0 
      ? Math.round((totalPassedRunsAcrossAllCases / totalRunsAcrossAllCases) * 100)
      : 0;

    return {
      totalTests: totalCount,
      passedTests: finishedTests, // Keep passedTests for backward compatibility with UI components
      failedTests,
      pendingTests,
      skippedTests,
      passRate
    };
  }, [testCases, totalCount]);

  const renderContent = () => {
    if (!selectedProject) {
      return (
        <div className="bg-white rounded-lg p-8 border border-gray-200 text-center">
          <p className="text-gray-600">Please select a project to view test cases.</p>
        </div>
      );
    }

    if (testCasesLoading) {
      return (
        <div className="bg-white rounded-lg p-8 border border-gray-200 text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-gray-400" />
          <p className="text-gray-600">Loading test cases...</p>
        </div>
      );
    }

    if (testCasesError) {
      return (
        <div className="bg-white rounded-lg p-8 border border-gray-200 text-center">
          <AlertCircle className="w-8 h-8 mx-auto mb-4 text-red-500" />
          <p className="text-red-600 mb-4">{testCasesError}</p>
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

    if (!testCases || testCases.length === 0) {
      return (
        <div className="bg-white rounded-lg p-8 border border-gray-200 text-center">
          <FileText className="w-12 h-12 mx-auto mb-4 text-gray-400" />
          <h3 className="text-lg font-medium text-gray-800 mb-2">No test cases found</h3>
          <p className="text-gray-600 mb-6">Get started by creating your first test case for this project.</p>
          <Link
            to="/create"
            className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >
            <Plus className="w-4 h-4 mr-2" />
            Create test case
          </Link>
        </div>
      );
    }

    return (
      <>
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">
            Showing {((page - 1) * pageSize) + 1}-{Math.min(page * pageSize, totalCount)} of {totalCount} test cases
          </h2>
        </div>

        {/* Render based on current view */}
        {currentView === 'list' ? (
          <div className="space-y-3">
            {testCases.map((testCase) => (
              <TestCaseListItem key={testCase.id} testCase={testCase} />
            ))}
          </div>
        ) : (
          <TestCaseTableView testCases={testCases} />
        )}

        {/* Pagination */}
        <Pagination
          currentPage={page}
          totalPages={totalPages}
          onPageChange={setPage}
          hasNext={hasNext}
          hasPrevious={hasPrevious}
        />
      </>
    );
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Test cases</h1>
          <p className="mt-1 text-gray-600">Manage and monitor your automated test cases</p>
        </div>
        <div className="mt-4 sm:mt-0 flex items-center space-x-4">
          <ViewSwitcher 
            currentView={currentView} 
            onViewChange={handleViewChange} 
          />
          <Link
            to="/create"
            className="inline-flex items-center px-6 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors"
          >
            <Plus className="w-5 h-5 mr-2" />
            Create test case
          </Link>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="Total cases"
          value={stats.totalTests}
          icon={CheckCircle}
          iconColor="text-indigo-600"
          iconBgColor="bg-indigo-100"
          subtitle={
            <><span className="text-emerald-600 font-medium">+12%</span><span className="text-gray-600 ml-1">from last month</span></>
          }
        />

        <StatsCard
          title="Finished"
          value={stats.passedTests}
          icon={CheckCircle}
          iconColor="text-emerald-600"
          iconBgColor="bg-emerald-100"
          subtitle={
            <><span className="text-emerald-600 font-medium">{stats.passRate}%</span><span className="text-gray-600 ml-1">success rate</span></>
          }
        />

        <StatsCard
          title="Failed"
          value={stats.failedTests}
          icon={XCircle}
          iconColor="text-red-600"
          iconBgColor="bg-red-100"
          subtitle={
            <><span className="text-red-600 font-medium">-5%</span><span className="text-gray-600 ml-1">from last week</span></>
          }
        />

        <StatsCard
          title="Pending"
          value={stats.pendingTests}
          icon={Clock}
          iconColor="text-blue-600"
          iconBgColor="bg-blue-100"
          subtitle="Active now"
          subtitleColor="text-blue-600 font-medium"
        />
      </div>

      {/* Filters and Search */}
      <TestCaseFilters
        search={filters.search}
        priority={filters.priority}
        category={filters.category}
        sortOrder={filters.sortOrder}
        onSearchChange={setSearch}
        onPriorityChange={(priority) => setPriority(priority)}
        onCategoryChange={(category) => setCategory(category)}
        onSortOrderChange={setSortOrder}
        priorityDropdownOpen={priorityDropdownOpen}
        setPriorityDropdownOpen={setPriorityDropdownOpen}
        categoryDropdownOpen={categoryDropdownOpen}
        setCategoryDropdownOpen={setCategoryDropdownOpen}
      />

      {/* Test Cases List */}
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

export default TestCasesPage;