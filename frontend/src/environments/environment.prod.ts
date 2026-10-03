declare const API_URL: string | undefined;

export const environment = {
  // Set at build time (ng build --define API_URL="'...'"); empty means same origin.
  apiUrl: typeof API_URL === 'string' ? API_URL : '',
};
