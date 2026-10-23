"use client";

import React from "react";

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  siblingCount?: number;
  showFirstLast?: boolean;
}

const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  onPageChange,
  siblingCount = 1,
}) => {
  const getPageNumbers = () => {
    const totalNumbers = siblingCount * 2 + 3;
    const totalBlocks = totalNumbers + 2;

    if (totalPages <= totalBlocks) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }

    const leftSiblingIndex = Math.max(currentPage - siblingCount, 1);
    const rightSiblingIndex = Math.min(currentPage + siblingCount, totalPages);

    const shouldShowLeftDots = leftSiblingIndex > 2;
    const shouldShowRightDots = rightSiblingIndex < totalPages - 2;

    const firstPageIndex = 1;
    const lastPageIndex = totalPages;

    if (!shouldShowLeftDots && shouldShowRightDots) {
      const leftItemCount = 3 + 2 * siblingCount;
      const leftRange = Array.from({ length: leftItemCount }, (_, i) => i + 1);
      return [...leftRange, "...", totalPages];
    }

    if (shouldShowLeftDots && !shouldShowRightDots) {
      const rightItemCount = 3 + 2 * siblingCount;
      const rightRange = Array.from(
        { length: rightItemCount },
        (_, i) => totalPages - rightItemCount + i + 1,
      );
      return [firstPageIndex, "...", ...rightRange];
    }

    if (shouldShowLeftDots && shouldShowRightDots) {
      const middleRange = Array.from(
        { length: rightSiblingIndex - leftSiblingIndex + 1 },
        (_, i) => leftSiblingIndex + i,
      );
      return [firstPageIndex, "...", ...middleRange, "...", lastPageIndex];
    }

    return [];
  };

  const pages = getPageNumbers();

  return (
    <nav
      className="pagination-container"
      style={{
        margin: "0px",
      }}
    >
      <ul className="pagination-list">
        <li className="pagination-item">
          <button
            className={`pagination-button ${currentPage === 1 ? "disabled" : ""}`}
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage === 1}
          >
            <svg
              className="pagination-arrow"
              width="8"
              height="12"
              viewBox="0 0 8 12"
              fill="none"
            >
              <path d="M6 2L2 6L6 10" stroke="currentColor" strokeWidth="2" />
            </svg>
          </button>
        </li>

        {pages.map((page, index) => (
          <li key={index} className="pagination-item">
            {page === "..." ? (
              <span className="pagination-dots">...</span>
            ) : (
              <button
                className={`pagination-button ${currentPage === page ? "active" : ""}`}
                onClick={() => onPageChange(page as number)}
              >
                {page}
              </button>
            )}
          </li>
        ))}

        <li className="pagination-item">
          <button
            className={`pagination-button ${currentPage === totalPages ? "disabled" : ""}`}
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
          >
            <svg
              className="pagination-arrow"
              width="8"
              height="12"
              viewBox="0 0 8 12"
              fill="none"
            >
              <path d="M2 2L6 6L2 10" stroke="currentColor" strokeWidth="2" />
            </svg>
          </button>
        </li>
      </ul>
    </nav>
  );
};

export default Pagination;
