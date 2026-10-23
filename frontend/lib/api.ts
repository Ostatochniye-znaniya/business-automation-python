export const API = "/csh/api";

export async function request<T = unknown>(
  path: string,
  method = "GET",
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const form = body instanceof FormData;
  const response = await fetch(API + path, {
    method,
    signal,
    credentials: "same-origin",
    cache: "no-store",
    headers:
      body !== undefined && !form
        ? { "Content-Type": "application/json" }
        : undefined,
    body: body === undefined ? undefined : form ? body : JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const detail = error.detail;
    throw new Error(
      Array.isArray(detail)
        ? detail.map((item) => item.msg).join("; ")
        : detail || `Ошибка HTTP ${response.status}`,
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export async function getAll<T>(
  path: string,
  signal?: AbortSignal,
): Promise<T[]> {
  const records: T[] = [];
  for (let offset = 0; ; offset += 100) {
    const page = await request<T[]>(
      `${path}${path.includes("?") ? "&" : "?"}offset=${offset}&limit=100`,
      "GET",
      undefined,
      signal,
    );
    records.push(...page);
    if (page.length < 100) return records;
  }
}

export async function download(path: string, fallback: string): Promise<void> {
  const response = await fetch(API + path, { credentials: "same-origin" });
  if (!response.ok)
    throw new Error(
      (await response.json()).detail || "Не удалось скачать файл",
    );
  const header = response.headers.get("Content-Disposition") || "";
  const encoded = header.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  const plain = header.match(/filename="?([^";]+)/i)?.[1];
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = encoded ? decodeURIComponent(encoded) : plain || fallback;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
