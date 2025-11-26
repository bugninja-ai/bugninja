import React from 'react';
import { Plus, X } from 'lucide-react';

interface ExtraRulesSectionProps {
  extraRules: { id: string; ruleNumber: number; description: string; }[];
  onRuleChange: (index: number, value: string) => void;
  onAddRule: () => void;
  onRemoveRule: (index: number) => void;
}

export const ExtraRulesSection: React.FC<ExtraRulesSectionProps> = ({
  extraRules,
  onRuleChange,
  onAddRule,
  onRemoveRule
}) => {
  return (
    <div className="bg-white rounded-lg p-6 border border-gray-200">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-800">Extra instructions (steps)</h2>
        <button
          type="button"
          onClick={onAddRule}
          className="inline-flex items-center px-3 py-1.5 text-sm font-medium text-indigo-600 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
        >
          <Plus className="w-4 h-4 mr-1" />
          Add Step
        </button>
      </div>

      <div className="space-y-3">
        {extraRules.map((rule, index) => (
          <div key={rule.id} className="flex items-start space-x-3">
            <div className="flex-shrink-0 w-8 h-8 bg-indigo-100 rounded-lg flex items-center justify-center text-sm font-medium text-indigo-600 mt-1">
              {rule.ruleNumber}
            </div>
            <div className="flex-1">
              <textarea
                value={rule.description}
                onChange={(e) => onRuleChange(index, e.target.value)}
                placeholder={`Step ${rule.ruleNumber}: Describe the instruction or step...`}
                rows={2}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-white"
              />
            </div>
            {extraRules.length > 1 && (
              <button
                type="button"
                onClick={() => onRemoveRule(index)}
                className="flex-shrink-0 p-2 text-gray-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition-colors mt-1"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
