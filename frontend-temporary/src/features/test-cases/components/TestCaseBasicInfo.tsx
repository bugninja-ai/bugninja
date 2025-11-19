import React from 'react';
import { Calendar } from 'lucide-react';
import { FrontendTestCase, TestCategory, TestPriority } from '../types';
import { EditableSection } from '../../../shared/components/EditableSection';
import { CustomDropdown } from '../../../shared/components/CustomDropdown';

interface TestCaseBasicInfoProps {
  testCase: FrontendTestCase;
  editableTestCase: FrontendTestCase | null;
  isEditing: boolean;
  onEdit: () => void;
  onSave: () => void;
  onCancel: () => void;
  onCategoryChange: (category: TestCategory) => void;
  onPriorityChange: (priority: TestPriority) => void;
  categoryDropdownOpen: boolean;
  setCategoryDropdownOpen: (open: boolean) => void;
  priorityDropdownOpen: boolean;
  setPriorityDropdownOpen: (open: boolean) => void;
}

export const TestCaseBasicInfo: React.FC<TestCaseBasicInfoProps> = ({
  testCase,
  editableTestCase,
  isEditing,
  onEdit,
  onSave,
  onCancel,
  onCategoryChange,
  onPriorityChange,
  categoryDropdownOpen,
  setCategoryDropdownOpen,
  priorityDropdownOpen,
  setPriorityDropdownOpen
}) => {
  const categoryOptions = [
    { value: 'authentication', label: 'Authentication' },
    { value: 'banking', label: 'Banking' },
    { value: 'payments', label: 'Payments' },
    { value: 'security', label: 'Security' },
    { value: 'ui', label: 'UI' },
    { value: 'api', label: 'API' }
  ];

  const priorityOptions = [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'critical', label: 'Critical' },
  ];

  return (
    <EditableSection
      title="Basic information"
      isEditing={isEditing}
      onEdit={onEdit}
      onSave={onSave}
      onCancel={onCancel}
      editTitle="Edit basic information"
      className={isEditing && (categoryDropdownOpen || priorityDropdownOpen) ? 'relative z-50' : ''}
    >
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Test case ID</label>
          <div className="px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-800">
            {testCase.id}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Project ID</label>
          <div className="px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-800">
            {testCase.projectId}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Category</label>
          {isEditing ? (
            <CustomDropdown
              options={categoryOptions}
              value={editableTestCase?.category || ''}
              onChange={(value) => onCategoryChange(value as TestCategory)}
              isOpen={categoryDropdownOpen}
              setIsOpen={setCategoryDropdownOpen}
              placeholder="Select Category"
              fullWidth={true}
            />
          ) : (
            <div className="px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-800 capitalize">
              {testCase.category}
            </div>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Priority</label>
          {isEditing ? (
            <CustomDropdown
              options={priorityOptions}
              value={editableTestCase?.priority || ''}
              onChange={(value) => onPriorityChange(value as TestPriority)}
              isOpen={priorityDropdownOpen}
              setIsOpen={setPriorityDropdownOpen}
              placeholder="Select Priority"
              fullWidth={true}
            />
          ) : (
            <div className="px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-800 capitalize">
              {testCase.priority}
            </div>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Created</label>
          <div className="flex items-center space-x-2 px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-800">
            <Calendar className="w-4 h-4 text-gray-400" />
            <span>{testCase.createdAt.toLocaleDateString()}</span>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Last updated</label>
          <div className="flex items-center space-x-2 px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-800">
            <Calendar className="w-4 h-4 text-gray-400" />
            <span>{testCase.updatedAt.toLocaleDateString()}</span>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Total runs</label>
          <div className="px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-800">
            {testCase.totalRuns}
          </div>
        </div>
      </div>
    </EditableSection>
  );
};
