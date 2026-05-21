const protocol = 'ws';
const host = window.location.hostname || 'localhost';

export const appConfig = {
  wsUrl: `${protocol}://${host}:8765`,
};
