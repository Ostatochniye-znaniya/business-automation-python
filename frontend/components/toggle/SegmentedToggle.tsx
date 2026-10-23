"use client";

import React, { useEffect, useRef, useState } from "react";

export interface SegmentedOption {
  value: string;
  label: string;
}

interface SegmentedToggleProps {
  options: SegmentedOption[];
  value: string;
  onChange: (value: string) => void;
  /** Растянуть на всю доступную ширину вместо ширины по содержимому */
  fullWidth?: boolean;
}

/**
 * Переключатель из нескольких сегментов: обводка плавно переезжает на выбранный,
 * у остальных остаётся только текст, читаемый на фоне дорожки.
 */
const SegmentedToggle: React.FC<SegmentedToggleProps> = ({
  options,
  value,
  onChange,
  fullWidth = false,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [thumb, setThumb] = useState<{ left: number; width: number } | null>(
    null,
  );

  const activeIndex = Math.max(
    0,
    options.findIndex((option) => option.value === value),
  );

  // Обводку позиционируем по реальной ширине кнопки: подписи разной длины
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const measure = () => {
      const active = container.querySelectorAll<HTMLButtonElement>(
        ".segmented-toggle-option",
      )[activeIndex];
      if (!active) return;

      setThumb({ left: active.offsetLeft, width: active.offsetWidth });
    };

    measure();

    const observer = new ResizeObserver(measure);
    observer.observe(container);
    return () => observer.disconnect();
  }, [activeIndex, options]);

  return (
    <div
      ref={containerRef}
      className={`segmented-toggle${fullWidth ? " segmented-toggle-full" : ""}`}
      role="tablist"
    >
      {thumb && (
        <span
          className="segmented-toggle-thumb"
          style={{ left: `${thumb.left}px`, width: `${thumb.width}px` }}
          aria-hidden="true"
        />
      )}

      {options.map((option) => {
        const isActive = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={isActive}
            className={`segmented-toggle-option${
              isActive ? " segmented-toggle-option-active" : ""
            }`}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
};

export default SegmentedToggle;
