import { GATEWAY_API_BASE } from './constants/gateway';

export const GATEWAY_ACCESS_TOKEN_KEY = 'workspace.gateway.lab.accessToken';
export const GATEWAY_REFRESH_TOKEN_KEY = 'workspace.gateway.lab.refreshToken';
export const GATEWAY_AUTH_CHANGE_EVENT = 'dbgpt-gateway-auth-change';

export type GatewayTokenResponse = {
  accessToken: string;
  refreshToken: string;
  expiresInSeconds?: number;
  tokenType?: string;
};

export type GatewayUserInfo = {
  userId: string;
  loginName: string;
  name: string;
  roles: string[];
  permissions: string[];
};

type JwtPayload = {
  sub?: string;
  userId?: string | number;
  nickname?: string;
  roles?: string[];
  permissions?: string[];
  exp?: number;
};

type AuthHeaderOptions = {
  json?: boolean;
  eventStream?: boolean;
};

const GATEWAY_ORIGIN = new URL(GATEWAY_API_BASE).origin;
export const GATEWAY_AUTH_API_BASE = `${GATEWAY_ORIGIN}/api/auth/v1`;

const isBrowser = () => typeof window !== 'undefined';

const decodeBase64Url = (value: string): string => {
  const normalized = value.replace(/-/g, '+').replace(/_/g, '/');
  return window.atob(normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), '='));
};

export const decodeJwt = <T = JwtPayload>(token: string): T | null => {
  if (!isBrowser() || !token) return null;
  const parts = token.split('.');
  if (parts.length !== 3) return null;
  try {
    return JSON.parse(decodeBase64Url(parts[1])) as T;
  } catch {
    return null;
  }
};

export const getGatewayAccessToken = (): string => {
  if (!isBrowser()) return '';
  return window.sessionStorage.getItem(GATEWAY_ACCESS_TOKEN_KEY) || '';
};

export const getGatewayRefreshToken = (): string => {
  if (!isBrowser()) return '';
  return window.sessionStorage.getItem(GATEWAY_REFRESH_TOKEN_KEY) || '';
};

const emitAuthChange = () => {
  if (!isBrowser()) return;
  window.dispatchEvent(new Event(GATEWAY_AUTH_CHANGE_EVENT));
};

export const setGatewayTokens = (accessToken: string, refreshToken: string) => {
  if (!isBrowser()) return;
  window.sessionStorage.setItem(GATEWAY_ACCESS_TOKEN_KEY, accessToken || '');
  window.sessionStorage.setItem(GATEWAY_REFRESH_TOKEN_KEY, refreshToken || '');
  emitAuthChange();
};

export const clearGatewayTokens = () => {
  if (!isBrowser()) return;
  window.sessionStorage.removeItem(GATEWAY_ACCESS_TOKEN_KEY);
  window.sessionStorage.removeItem(GATEWAY_REFRESH_TOKEN_KEY);
  emitAuthChange();
};

const isJwtExpired = (payload: JwtPayload | null): boolean => {
  if (!payload?.exp) return false;
  return payload.exp * 1000 <= Date.now();
};

const getValidGatewayAccessToken = (): string => {
  const token = getGatewayAccessToken();
  if (!token) return '';

  const payload = decodeJwt<JwtPayload>(token);
  if (!payload || isJwtExpired(payload)) {
    clearGatewayTokens();
    return '';
  }

  return token;
};

export const getGatewayUserInfo = (): GatewayUserInfo | null => {
  const payload = decodeJwt<JwtPayload>(getValidGatewayAccessToken());
  if (!payload?.userId) return null;
  return {
    userId: String(payload.userId),
    loginName: payload.sub || '',
    name: payload.nickname || payload.sub || '',
    roles: Array.isArray(payload.roles) ? payload.roles : [],
    permissions: Array.isArray(payload.permissions) ? payload.permissions : [],
  };
};

export const isGatewayAuthenticated = (): boolean => Boolean(getValidGatewayAccessToken() && getGatewayUserInfo());

export const buildGatewayUserInfoHeader = (userInfo: GatewayUserInfo): string =>
  JSON.stringify({
    userId: userInfo.userId,
    loginName: userInfo.loginName,
    name: userInfo.name,
    email: '',
    phone: '',
    positionShortName: '',
    structShortName: '',
    type: '',
    gatewayType: '',
    lang: '',
    buId: '',
    positionId: '',
    structId: '',
  });

export const getGatewayAuthHeaders = (options: AuthHeaderOptions = {}): Record<string, string> => {
  const headers: Record<string, string> = {};
  if (options.json) {
    headers['Content-Type'] = 'application/json';
  }
  if (options.eventStream) {
    headers.Accept = 'text/event-stream';
  }

  const token = getValidGatewayAccessToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const userInfo = getGatewayUserInfo();
  if (userInfo) {
    headers['X-User-Id'] = userInfo.userId;
    headers['X-Username'] = userInfo.loginName;
    headers['X-Roles'] = userInfo.roles.join(',');
    headers['X-Permissions'] = userInfo.permissions.join(',');
    headers['X-User-Info'] = buildGatewayUserInfoHeader(userInfo);
  }

  return headers;
};

export const createGatewayFetchHeaders = (headers?: HeadersInit, options: AuthHeaderOptions = {}): Headers => {
  const merged = new Headers(headers || {});
  Object.entries(getGatewayAuthHeaders(options)).forEach(([key, value]) => {
    if (value) {
      merged.set(key, value);
    }
  });
  return merged;
};

export const loginWithGateway = async (username: string, password: string): Promise<GatewayTokenResponse> => {
  const response = await fetch(`${GATEWAY_AUTH_API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload?.message || payload?.error || 'Login failed');
  }
  if (!payload?.accessToken) {
    throw new Error('Login response missing accessToken');
  }
  setGatewayTokens(payload.accessToken, payload.refreshToken || '');
  return payload;
};
