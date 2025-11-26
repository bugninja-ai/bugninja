import React, { useRef, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';

export interface DropdownOption {
  value: string;
  label: string;
}

export interface CustomDropdownProps {
  options: DropdownOption[];
  value: string;
  onChange: (value: string) => void;
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  placeholder: string;
  className?: string;
  dropdownClassName?: string;
  fullWidth?: boolean;
}

export const CustomDropdown: React.FC<CustomDropdownProps> = ({
  options,
  value,
  onChange,
  isOpen,
  setIsOpen,
  placeholder,
  className = '',
  dropdownClassName = '',
  fullWidth = false
}) => {
  const dropdownRef = useRef<HTMLDivElement>(null);
  const selectedOption = options.find(option => option.value === value);
  const buttonWidth = fullWidth ? 'w-full' : 'w-40';

  // Handle click outside
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, setIsOpen]);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`${buttonWidth} bg-white border border-gray-300 rounded-lg px-4 py-2 text-left flex items-center justify-between hover:border-gray-400 hover:shadow-sm transition-all duration-200 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 focus:outline-none ${className}`}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label={placeholder}
      >
        <span className="text-gray-800 whitespace-nowrap overflow-hidden text-ellipsis">{selectedOption?.label || placeholder}</span>
        <ChevronDown 
          className={`w-4 h-4 text-gray-400 transition-transform duration-200 flex-shrink-0 ${isOpen ? 'rotate-180' : ''}`} 
        />
      </button>
      
      {isOpen && (
        <div 
          className={`absolute top-full left-0 right-0 mt-1 bg-white border border-gray-300 rounded-lg overflow-hidden shadow-xl z-[9999] ${dropdownClassName}`}
          style={{
            maxHeight: '240px',
            overflowY: 'auto'
          }}
          role="listbox"
          aria-label={placeholder}
        >
          {options.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => {
                onChange(option.value);
                setIsOpen(false);
              }}
              className={`w-full px-4 py-2 text-left transition-colors duration-150 text-gray-800 hover:bg-gray-50 active:bg-gray-100 focus:bg-gray-50 focus:outline-none ${
                option.value === value ? 'bg-indigo-50 text-indigo-700' : ''
              }`}
              role="option"
              aria-selected={option.value === value}
            >
              <span className="whitespace-nowrap">{option.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}; 