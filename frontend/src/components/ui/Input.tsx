import { useState, type InputHTMLAttributes } from "react";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: string;
  error?: string;
  revealable?: boolean;
};

export default function Input({
  label,
  hint,
  error,
  id,
  className = "",
  revealable = false,
  type = "text",
  ...props
}: InputProps) {
  const inputId = id ?? props.name;
  const [revealed, setRevealed] = useState(false);
  const isPassword = type === "password";
  const resolvedType = revealable && isPassword && revealed ? "text" : type;

  return (
    <div className="space-y-1">
      <label htmlFor={inputId} className="block text-sm font-medium text-ink">
        {label}
      </label>
      <div className="relative">
        <input
          id={inputId}
          type={resolvedType}
          className={`field-control ${revealable && isPassword ? "pr-12" : ""} ${
            error ? "border-danger" : ""
          } ${className}`}
          aria-invalid={error ? true : undefined}
          aria-describedby={
            error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined
          }
          {...props}
        />
        {revealable && isPassword ? (
          <button
            type="button"
            className="absolute inset-y-0 right-0 px-3 text-xs font-medium text-ink-muted hover:text-ink"
            onClick={() => setRevealed((current) => !current)}
            aria-label={revealed ? "Hide password" : "Show password"}
          >
            {revealed ? "Hide" : "Show"}
          </button>
        ) : null}
      </div>
      {hint && !error ? (
        <p id={`${inputId}-hint`} className="text-xs text-ink-muted">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={`${inputId}-error`} className="text-xs text-danger" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
