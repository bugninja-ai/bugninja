import React from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { FrontendTestCase, ExtraRule } from '../types';
import { EditableSection } from '../../../shared/components/EditableSection';

interface ExtraRulesSectionProps {
  testCase: FrontendTestCase;
  editableTestCase: FrontendTestCase | null;
  isEditing: boolean;
  onEdit: () => void;
  onSave: () => void;
  onCancel: () => void;
  onRulesChange: (rules: ExtraRule[]) => void;
}

export const ExtraRulesSection: React.FC<ExtraRulesSectionProps> = ({
  testCase,
  editableTestCase,
  isEditing,
  onEdit,
  onSave,
  onCancel,
  onRulesChange
}) => {
  const addNewRule = () => {
    if (editableTestCase) {
      const newRule: ExtraRule = {
        id: `rule-${Date.now()}`,
        ruleNumber: editableTestCase.extraRules.length + 1,
        description: ''
      };
      onRulesChange([...editableTestCase.extraRules, newRule]);
    }
  };

  const removeRule = (index: number) => {
    if (editableTestCase) {
      const newRules = editableTestCase.extraRules.filter((_, i) => i !== index);
      // Renumber remaining rules
      const renumberedRules = newRules.map((r, i) => ({ ...r, ruleNumber: i + 1 }));
      onRulesChange(renumberedRules);
    }
  };

  const updateRule = (index: number, description: string) => {
    if (editableTestCase) {
      const newRules = [...editableTestCase.extraRules];
      newRules[index] = { ...newRules[index], description };
      onRulesChange(newRules);
    }
  };

  // Only show section if there are rules or we're editing
  if (testCase.extraRules.length === 0 && !isEditing) {
    return null;
  }

  return (
    <EditableSection
      title="Extra instructions (steps)"
      isEditing={isEditing}
      onEdit={onEdit}
      onSave={onSave}
      onCancel={onCancel}
      editTitle="Edit extra instructions (steps)"
    >
      <div className="space-y-3">
        {isEditing ? (
          <>
            {editableTestCase?.extraRules.map((rule, index) => (
              <div key={rule.id} className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-8 h-8 bg-indigo-100 rounded-lg flex items-center justify-center text-sm font-medium text-indigo-600 mt-1">
                  {rule.ruleNumber}
                </div>
                <div className="flex-1">
                  <textarea
                    value={rule.description}
                    onChange={(e) => updateRule(index, e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
                    rows={2}
                    placeholder="Enter instruction or step description"
                  />
                </div>
                <button
                  onClick={() => removeRule(index)}
                  className="flex-shrink-0 p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition-colors mt-1"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
            
            <button
              onClick={addNewRule}
              className="w-full py-3 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-indigo-300 hover:text-indigo-600 transition-colors flex items-center justify-center space-x-2"
            >
              <Plus className="w-4 h-4" />
              <span>Add step</span>
            </button>
          </>
        ) : (
          testCase.extraRules.map((rule) => (
            <div key={rule.id} className="flex items-start space-x-3">
              <div className="flex-shrink-0 w-8 h-8 bg-indigo-100 rounded-lg flex items-center justify-center text-sm font-medium text-indigo-600 mt-1">
                {rule.ruleNumber}
              </div>
              <div className="flex-1">
                <div className="px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg text-gray-800">
                  {rule.description}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </EditableSection>
  );
};
