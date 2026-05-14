const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
const host = window.location.hostname || 'localhost';

export const appConfig = {
  wsUrl: `${protocol}://${host}:8765`,
};
