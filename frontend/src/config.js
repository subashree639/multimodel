// Central API configuration. Override with a .env file:
//   VITE_API_URL=http://127.0.0.1:8000/api/v1
const config = {
  API_BASE_URL:
    (typeof import.meta !== 'undefined' &&
      import.meta.env &&
      import.meta.env.VITE_API_URL) ||
    'http://127.0.0.1:8000/api/v1',
  API_TIMEOUT: 10000,
};

export default config;
