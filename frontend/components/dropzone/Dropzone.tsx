"use client";

import React, { useRef, useState } from "react";
import { UploadCloud } from "lucide-react";

interface DropzoneProps {
  onFile: (file: File) => void;
  disabled?: boolean;
  /** Крупная подпись внутри области */
  title: string;
  /** Пояснение под подписью */
  hint?: string;
  /** Фильтр для диалога выбора файла, например ".pdf" */
  accept?: string;
}

/**
 * Область для перетаскивания файла. Клик по ней открывает обычный выбор файла,
 * чтобы способ был не единственным: перетаскивание недоступно с клавиатуры.
 */
const Dropzone: React.FC<DropzoneProps> = ({
  onFile,
  disabled = false,
  title,
  hint,
  accept,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);
  // Счётчик, а не флаг: dragleave приходит и при переходе на вложенный элемент
  const dragDepth = useRef(0);
  const [isDragging, setIsDragging] = useState(false);

  const reset = () => {
    dragDepth.current = 0;
    setIsDragging(false);
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    reset();
    if (disabled) return;

    const file = event.dataTransfer.files?.[0];
    if (file) onFile(file);
  };

  const openFileDialog = () => {
    if (!disabled) inputRef.current?.click();
  };

  return (
    <div
      className={`dropzone${isDragging ? " dropzone-active" : ""}${
        disabled ? " dropzone-disabled" : ""
      }`}
      onDragEnter={(event) => {
        event.preventDefault();
        if (disabled) return;
        dragDepth.current += 1;
        setIsDragging(true);
      }}
      onDragOver={(event) => event.preventDefault()}
      onDragLeave={(event) => {
        event.preventDefault();
        dragDepth.current -= 1;
        if (dragDepth.current <= 0) reset();
      }}
      onDrop={handleDrop}
      onClick={openFileDialog}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openFileDialog();
        }
      }}
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled}
    >
      <UploadCloud className="dropzone-icon" size={32} />
      <span className="dropzone-title">{title}</span>
      {hint && <span className="dropzone-hint">{hint}</span>}

      <input
        ref={inputRef}
        type="file"
        aria-label={title}
        accept={accept}
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0];
          // Сбрасываем значение, иначе повторный выбор того же файла не вызовет change
          event.target.value = "";
          if (file) onFile(file);
        }}
      />
    </div>
  );
};

export default Dropzone;
