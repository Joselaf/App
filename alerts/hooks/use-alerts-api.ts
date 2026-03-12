import { useState } from 'react';

import { apiBaseUrl } from '@/constants/config';
import type { DashboardResponse, SubscriptionRegistration } from '@/types/alerts';

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${apiBaseUrl}${path}`;
  let response: Response;

  try {
    response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...(init?.headers ?? {}),
      },
      ...init,
    });
  } catch (error) {
    if (error instanceof Error && /network request failed/i.test(error.message)) {
      throw new Error(
        `Network request failed while calling ${url}. Make sure the backend is running and EXPO_PUBLIC_API_BASE_URL (or expo.extra.apiBaseUrl) points to a reachable LAN URL for this device.`
      );
    }
    throw error;
  }

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}

export function useAlertsApi() {
  const [registeredToken, setRegisteredToken] = useState<string | null>(null);
  const backendConfigured = apiBaseUrl.length > 0;

  return {
    backendConfigured,
    fetchDashboard: async (): Promise<DashboardResponse> => {
      if (!backendConfigured) {
        throw new Error('Backend URL is not configured.');
      }

      return requestJson<DashboardResponse>('/api/dashboard');
    },
    registerPushToken: async (expoPushToken: string) => {
      if (!backendConfigured || expoPushToken === registeredToken) {
        return;
      }

      await requestJson<SubscriptionRegistration>('/api/subscriptions/register', {
        method: 'POST',
        body: JSON.stringify({
          expoPushToken,
          platform: 'expo',
          appVersion: '1.0.0',
        }),
      });

      setRegisteredToken(expoPushToken);
    },
    sendTestNotification: async (expoPushToken: string) => {
      if (!backendConfigured) {
        throw new Error('Backend URL is not configured.');
      }

      await requestJson<{ ok: boolean }>('/api/notifications/test', {
        method: 'POST',
        body: JSON.stringify({ expoPushToken }),
      });
    },
  };
}