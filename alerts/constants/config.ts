import Constants from 'expo-constants';

type AppExtra = {
  apiBaseUrl?: string;
  eas?: {
    projectId?: string;
  };
};

const extra = (Constants.expoConfig?.extra ?? {}) as AppExtra;

const apiBaseUrlFromEnv =
  typeof process.env.EXPO_PUBLIC_API_BASE_URL === 'string'
    ? process.env.EXPO_PUBLIC_API_BASE_URL.trim()
    : '';

const apiBaseUrlFromAppConfig = typeof extra.apiBaseUrl === 'string' ? extra.apiBaseUrl.trim() : '';

export const apiBaseUrl = (apiBaseUrlFromEnv || apiBaseUrlFromAppConfig).replace(/\/+$/, '');
export const easProjectId =
  extra.eas?.projectId ?? Constants.easConfig?.projectId ?? Constants.expoConfig?.extra?.eas?.projectId;