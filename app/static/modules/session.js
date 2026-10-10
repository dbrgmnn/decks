export function initSessionGuard() {
  const baseFetch = window.fetch.bind(window);
  window.fetch = async (...args) => {
    const response = await baseFetch(...args);
    if (response.status === 401) location.href = '/login';
    return response;
  };
}
