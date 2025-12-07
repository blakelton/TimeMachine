/**
 * Reusable form field wrapper component
 */

import type { ReactNode, InputHTMLAttributes, TextareaHTMLAttributes, SelectHTMLAttributes } from "react";
import "./FormField.css";

interface BaseFormFieldProps {
  label?: string;
  error?: string;
  helperText?: string;
  required?: boolean;
  id?: string;
  className?: string;
}

interface InputFieldProps extends BaseFormFieldProps {
  element?: "input";
  type?: InputHTMLAttributes<HTMLInputElement>["type"];
  value?: string | number;
  onChange?: InputHTMLAttributes<HTMLInputElement>["onChange"];
  placeholder?: string;
  disabled?: boolean;
  name?: string;
  autoComplete?: string;
  min?: number;
  max?: number;
  step?: number;
}

interface TextareaFieldProps extends BaseFormFieldProps {
  element: "textarea";
  value?: string;
  onChange?: TextareaHTMLAttributes<HTMLTextAreaElement>["onChange"];
  placeholder?: string;
  disabled?: boolean;
  name?: string;
  rows?: number;
}

interface SelectFieldProps extends BaseFormFieldProps {
  element: "select";
  value?: string | number;
  onChange?: SelectHTMLAttributes<HTMLSelectElement>["onChange"];
  disabled?: boolean;
  name?: string;
  children: ReactNode;
}

type FormFieldProps = InputFieldProps | TextareaFieldProps | SelectFieldProps;

export function FormField(props: FormFieldProps) {
  const {
    label,
    error,
    helperText,
    required,
    id,
    className = "",
    element = "input",
  } = props;

  // Generate unique ID if not provided
  const fieldId = id || `field-${Math.random().toString(36).substr(2, 9)}`;
  const errorId = `${fieldId}-error`;
  const helperId = `${fieldId}-helper`;

  const hasError = Boolean(error);

  const renderInput = () => {
    if (element === "textarea") {
      const { value, onChange, placeholder, disabled, name, rows = 4 } = props as TextareaFieldProps;
      return (
        <textarea
          id={fieldId}
          className={`form-input ${hasError ? "has-error" : ""}`}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          disabled={disabled}
          name={name}
          rows={rows}
          required={required}
          aria-invalid={hasError}
          aria-describedby={
            error ? errorId : helperText ? helperId : undefined
          }
        />
      );
    }

    if (element === "select") {
      const { value, onChange, disabled, name, children } = props as SelectFieldProps;
      return (
        <select
          id={fieldId}
          className={`form-input ${hasError ? "has-error" : ""}`}
          value={value}
          onChange={onChange}
          disabled={disabled}
          name={name}
          required={required}
          aria-invalid={hasError}
          aria-describedby={
            error ? errorId : helperText ? helperId : undefined
          }
        >
          {children}
        </select>
      );
    }

    // Default to input
    const {
      type = "text",
      value,
      onChange,
      placeholder,
      disabled,
      name,
      autoComplete,
      min,
      max,
      step,
    } = props as InputFieldProps;

    return (
      <input
        id={fieldId}
        type={type}
        className={`form-input ${hasError ? "has-error" : ""}`}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        disabled={disabled}
        name={name}
        autoComplete={autoComplete}
        min={min}
        max={max}
        step={step}
        required={required}
        aria-invalid={hasError}
        aria-describedby={
          error ? errorId : helperText ? helperId : undefined
        }
      />
    );
  };

  return (
    <div className={`form-field ${className}`}>
      {label && (
        <label htmlFor={fieldId} className="form-label">
          {label}
          {required && <span className="form-required" aria-label="required">*</span>}
        </label>
      )}

      {renderInput()}

      {error && (
        <div id={errorId} className="form-error" role="alert">
          {error}
        </div>
      )}

      {helperText && !error && (
        <div id={helperId} className="form-helper">
          {helperText}
        </div>
      )}
    </div>
  );
}
