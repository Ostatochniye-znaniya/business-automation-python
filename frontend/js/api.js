const API_BASE = "/api";

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
