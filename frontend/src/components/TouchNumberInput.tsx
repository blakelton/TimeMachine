/**
 * Touch-friendly number input with increment/decrement buttons
 * Designed for touchscreen use without requiring a keyboard
 */

import "./TouchNumberInput.css";

interface TouchNumberInputProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  label?: string;
  disabled?: boolean;
  className?: string;
}

export function TouchNumberInput({
  value,
  onChange,
  min = 1,
  max = 999,
  step = 1,
  label,
  disabled = false,
  className = "",
}: TouchNumberInputProps) {
  const handleDecrement = () => {
    const newValue = Math.max(min, value - step);
    onChange(newValue);
  };

  const handleIncrement = () => {
    const newValue = Math.min(max, value + step);
    onChange(newValue);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = parseInt(e.target.value, 10);
    if (!isNaN(newValue)) {
      onChange(Math.min(max, Math.max(min, newValue)));
    }
  };

  return (
    <div className={`touch-number-input ${className}`}>
      {label && <label className="touch-number-input__label">{label}</label>}
      <div className="touch-number-input__controls">
        <button
          type="button"
          className="touch-number-input__btn touch-number-input__btn--decrement"
          onClick={handleDecrement}
          disabled={disabled || value <= min}
          aria-label="Decrease value"
        >
          <span className="touch-number-input__btn-icon">-</span>
        </button>
        <input
          type="number"
          className="touch-number-input__value"
          value={value}
          onChange={handleChange}
          min={min}
          max={max}
          disabled={disabled}
          inputMode="numeric"
        />
        <button
          type="button"
          className="touch-number-input__btn touch-number-input__btn--increment"
          onClick={handleIncrement}
          disabled={disabled || value >= max}
          aria-label="Increase value"
        >
          <span className="touch-number-input__btn-icon">+</span>
        </button>
      </div>
    </div>
  );
}
