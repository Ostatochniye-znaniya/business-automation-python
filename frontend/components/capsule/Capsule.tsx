"use client";

import { ReactNode } from "react";

type CapsuleVariant = "default" | "success" | "warning" | "danger" | "info";

type CapsuleProps = {
  children: ReactNode;
  icon?: ReactNode;
  iconPosition?: "left" | "right";
  variant?: CapsuleVariant;
  className?: string;
};

export default function Capsule({
  children,
  icon,
  iconPosition = "left",
  variant = "default",
  className = "",
}: CapsuleProps) {
  return (
    <span className={`capsule capsule-${variant} ${className}`}>
      {icon && iconPosition === "left" && (
        <span className="capsule-icon">{icon}</span>
      )}

      <span>{children}</span>

      {icon && iconPosition === "right" && (
        <span className="capsule-icon">{icon}</span>
      )}
    </span>
  );
}
