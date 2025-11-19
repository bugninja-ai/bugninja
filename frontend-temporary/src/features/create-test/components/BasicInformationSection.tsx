import React from 'react';
import { CustomDropdown } from '../../../shared/components/CustomDropdown';

interface BasicInformationSectionProps {
  formData: {
    title: string;
    description: string;
    priority: string;
    category: string;
    goal: string;
  };
  onInputChange: (field: string, value: string) => void;
  priorityOptions: { value: string; label: string; }[];
  categoryOptions: { value: string; label: string; }[];
  priorityDropdownOpen: boolean;
  setPriorityDropdownOpen: (open: boolean) => void;
  categoryDropdownOpen: boolean;
  setCategoryDropdownOpen: (open: boolean) => void;
}

export const BasicInformationSection: React.FC<BasicInformationSectionProps> = ({
  formData,
  onInputChange,
  priorityOptions,
  categoryOptions,
  priorityDropdownOpen,
  setPriorityDropdownOpen,
  categoryDropdownOpen,
  setCategoryDropdownOpen
}) => {
  return (
    <div className="bg-white/80 backdrop-blur-sm rounded-lg p-6 border border-gray-200 overflow-visible relative z-0">
      <h2 className="text-lg font-semibold text-gray-800 mb-4">Basic Information</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 overflow-visible">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Test Case Title *
          </label>
          <input
            type="text"
            required
            value={formData.title}
            onChange={(e) => onInputChange('title', e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white"
            placeholder="e.g., User Login Authentication"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Priority *
          </label>
          <CustomDropdown
            options={priorityOptions}
            value={formData.priority}
            onChange={(value) => onInputChange('priority', value)}
            isOpen={priorityDropdownOpen}
            setIsOpen={setPriorityDropdownOpen}
            placeholder="Select Priority"
            fullWidth={true}
          />
        </div>

        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Category *
          </label>
          <CustomDropdown
            options={categoryOptions}
            value={formData.category}
            onChange={(value) => onInputChange('category', value)}
            isOpen={categoryDropdownOpen}
            setIsOpen={setCategoryDropdownOpen}
            placeholder="Select Category"
            fullWidth={true}
          />
        </div>

        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Description *
          </label>
          <textarea
            required
            rows={3}
            value={formData.description}
            onChange={(e) => onInputChange('description', e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white"
            placeholder="Describe what this test case validates..."
          />
        </div>

        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Test Goal *
          </label>
          <textarea
            required
            rows={2}
            value={formData.goal}
            onChange={(e) => onInputChange('goal', e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white"
            placeholder="What should this test achieve or verify?"
          />
        </div>
      </div>
    </div>
  );
};
