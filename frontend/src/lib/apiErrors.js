/**
 * Centralised helpers for normalising backend API error payloads
 * into safe, human-readable strings.
 *
 * Why this exists:
 *   FastAPI + Pydantic v2 returns 422 validation errors as
 *   `detail: Array<{ type, loc, msg, input, ctx, url }>`. Passing that
 *   array straight into a React child (e.g. `toast.error(data.detail)`)
 *   crashes the app with:
 *     "Objects are not valid as a React child"
 *
 * Always run server error payloads through `formatErrorDetail` before
 * passing them to UI components / toasts.
 */

export function formatErrorDetail(detail) {
  if (detail === null || detail === undefined) return '';
  if (typeof detail === 'string') return detail;

  if (Array.isArray(detail)) {
    return detail
      .map((entry) => {
        if (typeof entry === 'string') return entry;
        if (entry && typeof entry === 'object') {
          const field = Array.isArray(entry.loc)
            ? entry.loc.filter((p) => p !== 'body').join('.')
            : '';
          const msg = entry.msg || entry.message || entry.type || JSON.stringify(entry);
          return field ? `${field}: ${msg}` : String(msg);
        }
        return String(entry);
      })
      .join('; ');
  }

  if (typeof detail === 'object') {
    return detail.msg || detail.message || JSON.stringify(detail);
  }

  return String(detail);
}

/**
 * Extract a friendly error message from a variety of common shapes:
 *   - axios error: `err.response.data.detail`
 *   - fetch result: `{ detail, message }`
 *   - thrown `Error`: `err.message`
 *   - plain string
 */
export function getApiErrorMessage(err, fallback = '') {
  if (!err) return fallback;
  if (typeof err === 'string') return err;
  if (err?.response?.data?.detail !== undefined) {
    return formatErrorDetail(err.response.data.detail) || fallback;
  }
  if (err?.response?.data?.message) return String(err.response.data.message);
  if (err?.detail !== undefined) return formatErrorDetail(err.detail) || fallback;
  if (err?.message) return String(err.message);
  return fallback;
}
