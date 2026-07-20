import axios from 'axios';
 
const api = axios.create({
  // Use same-origin so Nginx can proxy /api to backend in Docker
  baseURL: '',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});
 
export const statusAPI = {
  getStatus: () => api.get('/api/status/'),
};
 
export const devicesAPI = {
  getDevices: ()   => api.get('/api/devices/'),
  getDevice:  (id) => api.get(`/api/devices/${id}`),
};
 
export const commandAPI = {
  testCommand: (commandPacket) =>
    api.post('/api/commands/test/', commandPacket),
};
 
export const configAPI = {
  getConfig:  ()     => api.get('/api/config/'),
  saveConfig: (data) => api.post('/api/config/', data),
};
 
export const logsAPI = {
  getLogs: (lines = 100, level = 'ALL') =>
    api.get('/api/logs/', { params: { lines, level } }),
};
 
export default api;
