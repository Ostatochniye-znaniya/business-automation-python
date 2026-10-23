// components/input/Input.tsx
"use client";

import React from "react";

interface InputProps {
  hint: string;
  value: string;
  onChange: (value: string) => void;
  multiline?: boolean;
  rows?: number;
  type?: string;
  autoComplete?: string;
}

const Input: React.FC<InputProps> = ({
  hint,
  value,
  onChange,
  multiline = false,
  rows = 4,
  type = "text",
  autoComplete,
}) => {
  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
  ) => {
    onChange(e.target.value);
  };

  if (multiline) {
    return (
      <textarea
        className="input-field"
        placeholder={hint}
        value={value}
        onChange={handleChange}
        rows={rows}
      />
    );
  }

  return (
    <input
      className="input-field"
      type={type}
      placeholder={hint}
      value={value}
      onChange={handleChange}
      autoComplete={autoComplete}
    />
  );
};

export default Input;
