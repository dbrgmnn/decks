export function initSessionGuard() {
  if (window.fetch.__sessionGuard) return;

  const baseFetch = window.fetch.bind(window);
  const guardedFetch = async (...args) => {
    const response = await baseFetch(...args);
    if (response.status === 401) location.href = '/login';
    return response;
  };

  guardedFetch.__sessionGuard = true;
  window.fetch = guardedFetch;
}
