"use client";

import React from "react";

interface ButtonProps {
  title?: string;
  color: string;
  onClick: () => void;
  disabled?: boolean;
  children?: React.ReactNode;
  style?: React.CSSProperties;
}

const Button: React.FC<ButtonProps> = ({
  title,
  color,
  onClick,
  disabled,
  children,
  style,
}) => {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`btn ${color}`}
      style={style}
    >
      {children ? children : title}
    </button>
  );
};

export default Button;
