import React from 'react';
import { Filter, Search, Calendar, ArrowUp, ArrowDown } from 'lucide-react';
import { TestPriority, TestCategory } from '../types';
import { CustomDropdown } from '../../../shared/components/CustomDropdown';

interface TestCaseFiltersProps {
  search: string;
  priority?: TestPriority;
  category?: TestCategory;
  sortOrder: 'asc' | 'desc';
  onSearchChange: (search: string) => void;
  onPriorityChange: (priority?: TestPriority) => void;
  onCategoryChange: (category?: TestCategory) => void;
  onSortOrderChange: (sortOrder: 'asc' | 'desc') => void;
  priorityDropdownOpen: boolean;
  setPriorityDropdownOpen: (open: boolean) => void;
  categoryDropdownOpen: boolean;
  setCategoryDropdownOpen: (open: boolean) => void;
}

const priorityOptions = [
  { value: 'all', label: 'All priorities' },
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
];

const categoryOptions = [
  { value: 'all', label: 'All categories' },
  { value: 'authentication', label: 'Authentication' },
  { value: 'banking', label: 'Banking' },
  { value: 'payments', label: 'Payments' },
  { value: 'security', label: 'Security' },
  { value: 'ui', label: 'UI' },
  { value: 'api', label: 'API' },
];

export const TestCaseFilters: React.FC<TestCaseFiltersProps> = ({
  search,
  priority,
  category,
  sortOrder,
  onSearchChange,
  onPriorityChange,
  onCategoryChange,
  onSortOrderChange,
  priorityDropdownOpen,
  setPriorityDropdownOpen,
  categoryDropdownOpen,
  setCategoryDropdownOpen,
}) => {
  return (
    <div className="bg-white rounded-lg p-6 border border-gray-200">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0">
        <div className="flex items-center space-x-2">
          <Filter className="w-5 h-5 text-gray-500" />
          <span className="font-medium text-gray-800">Filter test cases</span>
        </div>
        
        <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search test cases..."
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              className="pl-10 pr-4 py-2 w-full sm:w-64 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white"
            />
          </div>

          {/* Priority Filter */}
          <CustomDropdown
            options={priorityOptions}
            value={priority || 'all'}
            onChange={(value) => onPriorityChange(value === 'all' ? undefined : value as TestPriority)}
            isOpen={priorityDropdownOpen}
            setIsOpen={setPriorityDropdownOpen}
            placeholder="All priorities"
          />

          {/* Category Filter */}
          <CustomDropdown
            options={categoryOptions}
            value={category || 'all'}
            onChange={(value) => onCategoryChange(value === 'all' ? undefined : value as TestCategory)}
            isOpen={categoryDropdownOpen}
            setIsOpen={setCategoryDropdownOpen}
            placeholder="All categories"
          />

          {/* Sort by Last Run Date */}
          <button
            onClick={() => onSortOrderChange(sortOrder === 'desc' ? 'asc' : 'desc')}
            className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            title={`Sort by last run date ${sortOrder === 'desc' ? 'ascending' : 'descending'}`}
          >
            <Calendar className="w-4 h-4 text-gray-400" />
            {sortOrder === 'desc' ? (
              <ArrowDown className="w-3 h-3 ml-1 text-gray-500" />
            ) : (
              <ArrowUp className="w-3 h-3 ml-1 text-gray-500" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
