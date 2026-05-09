import axios from 'axios';
import { getGatewayAuthHeaders } from './auth';
import { GATEWAY_API_BASE } from './constants/gateway';

const api = axios.create({
  baseURL: process.env.API_BASE_URL || GATEWAY_API_BASE,
});

api.defaults.timeout = 30000;

api.interceptors.request.use(config => {
  Object.entries(getGatewayAuthHeaders()).forEach(([key, value]) => {
    config.headers.set(key, value);
  });
  return config;
});

api.interceptors.response.use(
  response => response.data,
  err => Promise.reject(err),
);

export default api;
