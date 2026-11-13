/**
 * A server error object must never reach a toast as a React child: FastAPI's validation errors are arrays of
 * {type, loc, msg, input, url}, and `toast.error(e.response.data.detail)` with such an array crashed the whole app
 * («Minified React error #31»). Every toast call (title and description) now goes through formatErrorDetail first.
 */
import { isValidElement } from 'react';
import { toast } from 'sonner';
import { formatErrorDetail } from '@/lib/apiErrors';

const safe = (m) => {
  if (m === null || m === undefined || typeof m === 'string' || typeof m === 'number' || typeof m === 'function' || isValidElement(m)) return m;
  try { return formatErrorDetail(m) || 'Error'; } catch (_) { return 'Error'; }
};
const safeOpts = (o) => (o && typeof o === 'object' && 'description' in o ? { ...o, description: safe(o.description) } : o);

export function installSafeToast() {
  if (toast.__safe) return;
  ['error', 'success', 'message', 'info', 'warning', 'loading'].forEach((k) => {
    const orig = toast[k];
    if (typeof orig === 'function') toast[k] = (m, o) => orig(safe(m), safeOpts(o));
  });
  toast.__safe = true;
}

/**
 * The same guard one step earlier, for EVERY place that shows a server error (toasts, `{error}` in JSX, alerts):
 * a FastAPI validation error («detail»: [{type, loc, msg, input, url}, …]) becomes a plain string before any
 * component sees it. The original list stays in `detail_list`. Object details with a `code` are left as they are
 * (components read their fields).
 */
export function installSafeApiErrors(axiosInstance) {
  if (!axiosInstance || axiosInstance.__safeErrors) return;
  axiosInstance.__safeErrors = true;
  axiosInstance.interceptors.response.use(undefined, (error) => {
    try {
      const data = error && error.response && error.response.data;
      if (data && Array.isArray(data.detail)) {
        data.detail_list = data.detail;
        data.detail = formatErrorDetail(data.detail) || 'Error';
      }
    } catch (_) { /* never break the error flow */ }
    return Promise.reject(error);
  });
}
