"use client";

import { useMemo, useState } from "react";

/**
 * Пагинация списка на клиенте для компонента Pagination.
 * Если список сократился (например, после фильтра), текущая страница
 * сама прижимается к последней существующей.
 */
export function usePagination<T>(items: T[], pageSize: number) {
    const [page, setPage] = useState(1);
    const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
    const currentPage = Math.min(page, totalPages);

    const pageItems = useMemo(
        () => items.slice((currentPage - 1) * pageSize, currentPage * pageSize),
        [items, currentPage, pageSize]
    );

    return { currentPage, totalPages, pageItems, setPage };
}
