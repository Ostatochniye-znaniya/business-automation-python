const API_BASE = window.APP_CONFIG?.apiBase || "/api";

// Пока endpoint не готов, страницу можно верстать на заглушках:
// включите USE_MOCK и добавьте ответы в MOCKS по ключу "МЕТОД /путь".
const USE_MOCK = false;
const MOCKS = {};

async function request(method, path, body) {
  const key = method + " " + path;
  if (USE_MOCK && Object.prototype.hasOwnProperty.call(MOCKS, key)) {
    return MOCKS[key];
  }

  const options = { method: method, headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  const response = await fetch(API_BASE + path, options);
  const text = await response.text();

  let payload = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch (error) {
      payload = null;
    }
  }

  if (!response.ok) {
    const detail = payload && payload.detail ? payload.detail : response.statusText;
    throw new Error(detail);
  }

  return payload;
}

function apiGet(path) {
  return request("GET", path);
}

function apiPost(path, body) {
  return request("POST", path, body);
}

// API lists are paginated: reference data must not stop at the first 100 rows.
async function apiGetAll(path) {
  const items = [];
  for (let offset = 0; ; offset += 100) {
    const separator = path.includes("?") ? "&" : "?";
    const page = await apiGet(`${path}${separator}offset=${offset}&limit=100`);
    if (!Array.isArray(page)) throw new Error("Сервер вернул некорректный список");
    items.push(...page);
    if (page.length < 100) return items;
  }
}
