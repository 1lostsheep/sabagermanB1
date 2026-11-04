// Small wrapper around fetch for the local server.
async function call(method, url, data) {
  const opts = { method, headers: {} };
  if (data instanceof FormData) opts.body = data;
  else if (data !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(data);
  }
  const res = await fetch(url, opts);
  if (!res.ok) {
    const err = new Error(`${method} ${url} -> ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}
export const api = {
  get: (url) => call("GET", url),
  post: (url, data = {}) => call("POST", url, data),
};
