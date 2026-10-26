"use client";

import React, { useState } from "react";

interface Column<T> {
  header: React.ReactNode;
  accessor: keyof T | ((row: T) => React.ReactNode);
  sortFn?: (a: T, b: T) => number; // если есть - можно сортировать, если нет - нельзя
  style?: React.CSSProperties;
  className?: string;
  rowSpan?: (row: T, rowIndex: number, rows: T[]) => number;
}

interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  style?: React.CSSProperties;
}

const Table = <T,>({ columns, data, style }: TableProps<T>) => {
  const [sortColumn, setSortColumn] = useState<number | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  const handleSort = (colIndex: number) => {
    const column = columns[colIndex];
    // Сортируем только если есть sortFn
    if (!column.sortFn) return;

    if (sortColumn === colIndex) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortColumn(colIndex);
      setSortDirection("asc");
    }
  };

  const getSortedData = () => {
    if (sortColumn === null) return data;

    const column = columns[sortColumn];
    if (!column.sortFn) return data;

    return [...data].sort((a, b) => {
      return sortDirection === "asc"
        ? column.sortFn!(a, b)
        : column.sortFn!(b, a);
    });
  };

  const sortedData = getSortedData();

  return (
    <div className="table-wrapper" style={style}>
      <table className="table-container" style={style}>
        <thead>
          <tr>
            {columns.map((col, i) => (
              <th
                key={i}
                onClick={() => handleSort(i)}
                className={col.className}
                style={{
                  cursor: col.sortFn ? "pointer" : "default",
                  ...col.style,
                }}
              >
                {col.header}
                {col.sortFn && sortColumn === i && (
                  <span>{sortDirection === "asc" ? " ↑" : " ↓"}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedData.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {columns.map((col, colIndex) => {
                const rowSpan = col.rowSpan?.(row, rowIndex, sortedData) ?? 1;
                if (rowSpan === 0) return null;

                const value =
                  typeof col.accessor === "function"
                    ? col.accessor(row)
                    : (row[col.accessor] as React.ReactNode);
                return (
                  <td
                    key={colIndex}
                    rowSpan={rowSpan}
                    className={col.className}
                    style={col.style}
                  >
                    {value}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default Table;
export type { Column };
