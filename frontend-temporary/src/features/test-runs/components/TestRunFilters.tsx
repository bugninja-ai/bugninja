import React from 'react';
import { Filter, Search, Calendar, ArrowUp, ArrowDown, X } from 'lucide-react';
import { CustomDropdown } from '../../../shared/components/CustomDropdown';

interface TestRunFiltersProps {
  search: string;
  status?: string;
  testCaseId?: string;
  selectedBrowserId?: string;
  sortOrder: 'asc' | 'desc';
  onSearchChange: (search: string) => void;
  onStatusChange: (status?: string) => void;
  onTestCaseChange: (testCaseId?: string) => void;
  onBrowserChange: (browserId?: string) => void;
  onSortOrderChange: (order: 'asc' | 'desc') => void;
  onClearFilters: () => void;
  // Dropdown states
  statusDropdownOpen: boolean;
  setStatusDropdownOpen: (open: boolean) => void;
  testCaseDropdownOpen: boolean;
  setTestCaseDropdownOpen: (open: boolean) => void;
  browserDropdownOpen: boolean;
  setBrowserDropdownOpen: (open: boolean) => void;
  // Options
  testCaseOptions: Array<{ value: string; label: string }>;
  browserOptions: Array<{ value: string; label: string }>;
}

const statusOptions = [
  { value: 'all', label: 'All statuses' },
  { value: 'FINISHED', label: 'Finished' },
  { value: 'FAILED', label: 'Failed' },
  { value: 'PENDING', label: 'Pending' },
];

export const TestRunFilters: React.FC<TestRunFiltersProps> = ({
  search,
  status,
  testCaseId,
  selectedBrowserId,
  sortOrder,
  onSearchChange,
  onStatusChange,
  onTestCaseChange,
  onBrowserChange,
  onSortOrderChange,
  onClearFilters,
  statusDropdownOpen,
  setStatusDropdownOpen,
  testCaseDropdownOpen,
  setTestCaseDropdownOpen,
  browserDropdownOpen,
  setBrowserDropdownOpen,
  testCaseOptions,
  browserOptions,
}) => {
  const hasActiveFilters = search || status || testCaseId || selectedBrowserId;

  return (
    <div className="bg-white rounded-lg p-6 border border-gray-200">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0">
        <div className="flex items-center space-x-2">
          <Filter className="w-5 h-5 text-gray-400" />
          <span className="font-medium text-gray-800">Filter test runs</span>
        </div>
        
        <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search test runs..."
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              className="pl-10 pr-4 py-2 w-full sm:w-64 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white"
            />
          </div>

          {/* Sort by Date Toggle */}
          <button
            onClick={() => onSortOrderChange(sortOrder === 'desc' ? 'asc' : 'desc')}
            className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            title={`Sort by date ${sortOrder === 'desc' ? 'ascending' : 'descending'}`}
          >
            <Calendar className="w-4 h-4 text-gray-400" />
            {sortOrder === 'desc' ? (
              <ArrowDown className="w-3 h-3 ml-1 text-gray-500" />
            ) : (
              <ArrowUp className="w-3 h-3 ml-1 text-gray-500" />
            )}
          </button>

          {/* Test Case Filter */}
          <CustomDropdown
            options={testCaseOptions}
            value={testCaseId || 'all'}
            onChange={(value) => onTestCaseChange(value === 'all' ? undefined : value)}
            isOpen={testCaseDropdownOpen}
            setIsOpen={setTestCaseDropdownOpen}
            placeholder="All test cases"
            dropdownClassName="!left-0 !right-auto w-72"
          />

          {/* Browser/Viewport Filter */}
          <CustomDropdown
            options={browserOptions}
            value={selectedBrowserId || 'all'}
            onChange={(value) => onBrowserChange(value === 'all' ? undefined : value)}
            isOpen={browserDropdownOpen}
            setIsOpen={setBrowserDropdownOpen}
            placeholder="All browsers"
            dropdownClassName="!left-0 !right-auto w-56"
          />

          {/* Status Filter */}
          <CustomDropdown
            options={statusOptions}
            value={status || 'all'}
            onChange={(value) => onStatusChange(value === 'all' ? undefined : value)}
            isOpen={statusDropdownOpen}
            setIsOpen={setStatusDropdownOpen}
            placeholder="All statuses"
          />

          {/* Remove All Filters Button */}
          {hasActiveFilters && (
            <button
              onClick={onClearFilters}
              className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              title="Clear all filters"
            >
              <X className="w-4 h-4 text-gray-400" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
