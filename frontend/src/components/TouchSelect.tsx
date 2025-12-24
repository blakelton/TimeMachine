/**
 * Touch-friendly select with segmented button style
 * Perfect for selecting from a small set of options without dropdown
 */

import "./TouchSelect.css";

interface TouchSelectOption<T extends string | number> {
  value: T;
  label: string;
}

interface TouchSelectProps<T extends string | number> {
  value: T;
  onChange: (value: T) => void;
  options: TouchSelectOption<T>[];
  label?: string;
  disabled?: boolean;
  className?: string;
}

export function TouchSelect<T extends string | number>({
  value,
  onChange,
  options,
  label,
  disabled = false,
  className = "",
}: TouchSelectProps<T>) {
  return (
    <div className={`touch-select ${className}`}>
      {label && <label className="touch-select__label">{label}</label>}
      <div className="touch-select__options">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`touch-select__option ${
              value === option.value ? "touch-select__option--active" : ""
            }`}
            onClick={() => onChange(option.value)}
            disabled={disabled}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}
