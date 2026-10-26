"use client";
import { useCallback, useEffect, useState } from "react";
import { getAll } from "./api";
import { Period } from "./types";

export function useList<T>(path: string | null) {
  const [data, setData] = useState<T[]>([]),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(!!path),
    [version, setVersion] = useState(0);
  const reload = useCallback(() => setVersion((value) => value + 1), []);
  useEffect(() => {
    const controller = new AbortController();
    if (!path) {
      setData([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    getAll<T>(path, controller.signal)
      .then((rows) => {
        setData(rows);
        setLoading(false);
      })
      .catch((reason) => {
        if (!controller.signal.aborted) {
          setData([]);
          setError(reason.message);
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [path, version]);
  return { data, setData, error, loading, reload };
}
export function usePeriod() {
  const list = useList<Period>("/periods");
  const [id, setId] = useState("");
  useEffect(() => {
    if (list.data.length && !list.data.some((row) => String(row.id) === id))
      setId(
        String(
          list.data.find((row) => row.status === "OPEN")?.id || list.data[0].id,
        ),
      );
  }, [list.data, id]);
  return {
    ...list,
    id,
    setId,
    selected: list.data.find((row) => String(row.id) === id),
  };
}
export function useAction() {
  const [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [failed, setFailed] = useState(false);
  async function run(work: () => Promise<unknown>) {
    setBusy(true);
    setNotice("");
    setFailed(false);
    try {
      await work();
      setNotice("Готово.");
    } catch (error) {
      setFailed(true);
      setNotice(
        error instanceof Error
          ? error.message
          : "Не удалось выполнить действие",
      );
    } finally {
      setBusy(false);
    }
  }
  return { notice, busy, failed, run };
}
