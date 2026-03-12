import {
    createContext,
    PropsWithChildren,
    startTransition,
    useCallback,
    useContext,
    useEffect,
    useState,
} from 'react';

import { useAlertsApi } from '@/hooks/use-alerts-api';
import { usePushNotifications } from '@/hooks/use-push-notifications';
import type { DashboardResponse } from '@/types/alerts';

type PermissionStatus = 'granted' | 'denied' | 'undetermined';

type AlertsContextValue = {
  dashboard: DashboardResponse;
  loading: boolean;
  error: string | null;
  backendConfigured: boolean;
  refresh: () => void;
  sendTestNotification: () => Promise<void>;
  registration: {
    expoPushToken: string | null;
    permissionStatus: PermissionStatus | 'unavailable';
    error: string | null;
    isSupportedDevice: boolean;
  };
};

const defaultDashboard: DashboardResponse = {
  monitorHealthy: false,
  tuyaConnected: false,
  connectionError: null,
  lastPollAt: null,
  devices: [],
  recentAlerts: [],
};

const AlertsContext = createContext<AlertsContextValue>({
  dashboard: defaultDashboard,
  loading: false,
  error: null,
  backendConfigured: false,
  refresh: () => {},
  sendTestNotification: async () => {},
  registration: {
    expoPushToken: null,
    permissionStatus: 'unavailable',
    error: null,
    isSupportedDevice: false,
  },
});

export function AlertsProvider({ children }: PropsWithChildren) {
  const registration = usePushNotifications();
  const { backendConfigured, fetchDashboard, registerPushToken, sendTestNotification } = useAlertsApi();
  const [dashboard, setDashboard] = useState<DashboardResponse>(defaultDashboard);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runRefresh = useCallback(() => {
    if (!backendConfigured) {
      setError('Set expo.extra.apiBaseUrl in app.json to reach the monitoring backend.');
      return;
    }

    setLoading(true);
    fetchDashboard()
      .then((nextDashboard) => {
        startTransition(() => {
          setDashboard(nextDashboard);
          setError(null);
        });
      })
      .catch((nextError: Error) => {
        setError(nextError.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [backendConfigured, fetchDashboard]);

  const refresh = () => {
    runRefresh();
  };

  useEffect(() => {
    runRefresh();

    if (!backendConfigured) {
      return;
    }

    const intervalId = setInterval(() => {
      runRefresh();
    }, 30000);

    return () => {
      clearInterval(intervalId);
    };
  }, [backendConfigured, runRefresh]);

  useEffect(() => {
    if (!backendConfigured || !registration.expoPushToken) {
      return;
    }

    registerPushToken(registration.expoPushToken).catch((nextError: Error) => {
      setError(nextError.message);
    });
  }, [backendConfigured, registration.expoPushToken, registerPushToken]);

  return (
    <AlertsContext.Provider
      value={{
        dashboard,
        loading,
        error,
        backendConfigured,
        refresh,
        sendTestNotification: async () => {
          if (!registration.expoPushToken) {
            setError('Expo push token is not available yet. Open on a supported device and allow notifications.');
            return;
          }

          await sendTestNotification(registration.expoPushToken);
        },
        registration,
      }}>
      {children}
    </AlertsContext.Provider>
  );
}

export function useAlerts() {
  return useContext(AlertsContext);
}