import Constants from 'expo-constants';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Alert, Platform, StyleSheet, View } from 'react-native';

import ParallaxScrollView from '@/components/parallax-scroll-view';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';

type AlertKind = 'battery' | 'breaker' | 'panic' | 'fire';

type TuyaAlert = {
  id: string;
  kind: AlertKind;
  severity: 'warning' | 'critical';
  device_id: string;
  device_name: string;
  message: string;
  code: string;
  value: unknown;
  timestamp: string;
};

type AlertsResponse = {
  connected: boolean;
  last_poll: string | null;
  last_error: string | null;
  count: number;
  alerts: TuyaAlert[];
};

type DeviceInfo = {
  id: string;
  name: string;
};

type DevicesResponse = {
  connected: boolean;
  last_poll: string | null;
  device_count: number;
  devices: DeviceInfo[];
};

const resolveApiBase = () => {
  if (process.env.EXPO_PUBLIC_TUYA_MONITOR_URL) {
    return process.env.EXPO_PUBLIC_TUYA_MONITOR_URL;
  }

  // In Expo Go/dev, derive host from Metro and target backend on port 8001.
  const hostUri = Constants.expoConfig?.hostUri;
  if (hostUri) {
    const host = hostUri.split(':')[0];
    if (host) {
      return `http://${host}:8001`;
    }
  }

  return 'http://127.0.0.1:8001';
};

const API_BASE = resolveApiBase();

const KIND_LABELS: Record<AlertKind, string> = {
  battery: 'Bateria',
  breaker: 'Disjuntor',
  panic: 'Pânico',
  fire: 'Incêndio',
};

const formatRelativeTimePt = (isoDate: string | null, nowMs = Date.now()) => {
  if (!isoDate) {
    return 'N/D';
  }

  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) {
    return 'N/D';
  }

  const diffSeconds = Math.max(0, Math.floor((nowMs - date.getTime()) / 1000));

  if (diffSeconds < 5) {
    return 'agora mesmo';
  }
  if (diffSeconds < 60) {
    return `há ${diffSeconds}s`;
  }

  const diffMinutes = Math.floor(diffSeconds / 60);
  if (diffMinutes < 60) {
    return `há ${diffMinutes} min`;
  }

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) {
    return `há ${diffHours} h`;
  }

  const diffDays = Math.floor(diffHours / 24);
  return `há ${diffDays} d`;
};

const pluralizePt = (count: number, singular: string, plural: string) =>
  `${count} ${count === 1 ? singular : plural}`;

const IS_EXPO_GO =
  Constants.executionEnvironment === 'storeClient' || Constants.appOwnership === 'expo';

const setupNotifications = async () => {
  if (IS_EXPO_GO) {
    return false;
  }

  let Notifications: typeof import('expo-notifications');
  try {
    Notifications = await import('expo-notifications');
  } catch {
    return false;
  }

  try {
    Notifications.setNotificationHandler({
      handleNotification: async () => ({
        shouldShowBanner: true,
        shouldShowList: true,
        shouldPlaySound: true,
        shouldSetBadge: false,
      }),
    });
  } catch {
    return false;
  }

  if (Platform.OS === 'android') {
    try {
      await Notifications.setNotificationChannelAsync('alerts', {
        name: 'Alertas Tuya',
        importance: Notifications.AndroidImportance.HIGH,
        sound: 'default',
        vibrationPattern: [0, 250, 250, 250],
        lockscreenVisibility: Notifications.AndroidNotificationVisibility.PUBLIC,
      });
    } catch {
      return false;
    }
  }

  let finalStatus: string;

  try {
    const currentPermissions = await Notifications.getPermissionsAsync();
    finalStatus = currentPermissions.status;
  } catch {
    return false;
  }

  if (finalStatus !== 'granted') {
    try {
      const requested = await Notifications.requestPermissionsAsync();
      finalStatus = requested.status;
    } catch {
      return false;
    }
  }

  return finalStatus === 'granted';
};

const sendCriticalNotification = async (title: string, body: string) => {
  if (IS_EXPO_GO) {
    return false;
  }

  try {
    const Notifications = await import('expo-notifications');
    await Notifications.scheduleNotificationAsync({
      content: {
        title,
        body,
        sound: 'default',
        priority: Notifications.AndroidNotificationPriority.HIGH,
      },
      trigger: null,
    });
    return true;
  } catch {
    return false;
  }
};

export default function HomeScreen() {
  const [connected, setConnected] = useState(false);
  const [lastPoll, setLastPoll] = useState<string | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const [alerts, setAlerts] = useState<TuyaAlert[]>([]);
  const [devices, setDevices] = useState<DeviceInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [now, setNow] = useState(() => Date.now());
  const [notificationsReady, setNotificationsReady] = useState(false);
  const seenCriticalRef = useRef<Set<string>>(new Set());

  const groupedCounts = useMemo(() => {
    const counts: Record<AlertKind, number> = {
      battery: 0,
      breaker: 0,
      panic: 0,
      fire: 0,
    };

    for (const event of alerts) {
      counts[event.kind] += 1;
    }

    return counts;
  }, [alerts]);

  const fetchAlerts = useCallback(
    async () => {
      try {
        const [alertsRes, devicesRes] = await Promise.all([
          fetch(`${API_BASE}/alerts?limit=100`),
          fetch(`${API_BASE}/devices`),
        ]);

        if (!alertsRes.ok) {
          throw new Error(`Erro da API de alertas (${alertsRes.status})`);
        }
        if (!devicesRes.ok) {
          throw new Error(`Erro da API de dispositivos (${devicesRes.status})`);
        }

        const alertsData = (await alertsRes.json()) as AlertsResponse;
        const devicesData = (await devicesRes.json()) as DevicesResponse;

        setConnected(alertsData.connected);
        setLastPoll(alertsData.last_poll);
        setLastError(alertsData.last_error);
        setAlerts(alertsData.alerts);
        setDevices(devicesData.devices);

        const freshCritical = alertsData.alerts.filter(
          (item) => item.severity === 'critical' && !seenCriticalRef.current.has(item.id)
        );

        for (const item of freshCritical) {
          seenCriticalRef.current.add(item.id);
          const title = `Alerta de ${KIND_LABELS[item.kind]}`;
          if (notificationsReady) {
            const sent = await sendCriticalNotification(title, item.message);
            if (!sent) {
              Alert.alert(title, item.message);
            }
          } else {
            Alert.alert(title, item.message);
          }
        }
      } catch (error) {
        setConnected(false);
        const message = error instanceof Error ? error.message : 'Erro de rede desconhecido';
        setLastError(`${message}. Verifique se o backend está em execução em ${API_BASE}.`);
      } finally {
        setLoading(false);
      }
    },
    [notificationsReady]
  );

  useEffect(() => {
    if (IS_EXPO_GO) {
      setNotificationsReady(false);
      return;
    }

    setupNotifications()
      .then((enabled) => setNotificationsReady(enabled))
      .catch(() => setNotificationsReady(false));
  }, []);

  useEffect(() => {
    fetchAlerts();

    const interval = setInterval(() => {
      fetchAlerts();
    }, 3000);

    return () => clearInterval(interval);
  }, [fetchAlerts]);

  useEffect(() => {
    const ticker = setInterval(() => {
      setNow(Date.now());
    }, 1000);

    return () => clearInterval(ticker);
  }, []);

  const totalCritical = alerts.filter((a) => a.severity === 'critical').length;
  const noActiveAlerts = !loading && alerts.length === 0;

  return (
    <ParallaxScrollView
      headerBackgroundColor={{ light: '#D8E9E0', dark: '#1F2A26' }}
      headerImage={<View style={styles.headerBlob} />}>
      <ThemedView style={styles.titleContainer}>
        <ThemedText type="title">Alertas de Segurança</ThemedText>
      </ThemedView>

      <ThemedView style={styles.statusCard}>
        <ThemedText type="subtitle">Tuya Cloud</ThemedText>
        <ThemedText style={connected ? styles.statusUp : styles.statusDown}>
          {connected ? 'Conectado' : 'Desconectado'}
        </ThemedText>
        <ThemedText>API: {API_BASE}</ThemedText>
        <ThemedText>
          Última verificação: {formatRelativeTimePt(lastPoll, now)}
          {lastPoll
            ? ` (${new Date(lastPoll).toLocaleTimeString('pt-PT', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              })})`
            : ''}
        </ThemedText>
        {lastError ? <ThemedText style={styles.errorText}>Erro: {lastError}</ThemedText> : null}
      </ThemedView>

      <ThemedView style={styles.metricsRow}>
        <ThemedView style={styles.metricCard}>
          <ThemedText type="subtitle">Críticos</ThemedText>
          <ThemedText style={styles.metricCritical}>{totalCritical}</ThemedText>
        </ThemedView>
        <ThemedView style={styles.metricCard}>
          <ThemedText type="subtitle">Total</ThemedText>
          <ThemedText style={styles.metricNeutral}>{alerts.length}</ThemedText>
        </ThemedView>
      </ThemedView>

      <ThemedText style={styles.summaryText}>
        {pluralizePt(totalCritical, 'alerta crítico', 'alertas críticos')} •{' '}
        {pluralizePt(alerts.length, 'alerta ativo', 'alertas ativos')}
      </ThemedText>

      {noActiveAlerts ? (
        <ThemedView style={styles.safeBanner}>
          <ThemedText type="defaultSemiBold">Sem alertas ativos</ThemedText>
          <ThemedText>Todos os dispositivos monitorados estão em estado normal.</ThemedText>
        </ThemedView>
      ) : null}

      <ThemedView style={styles.kindCard}>
        <ThemedText type="subtitle">Por Tipo</ThemedText>
        <ThemedText>Bateria: {groupedCounts.battery}</ThemedText>
        <ThemedText>Disjuntor: {groupedCounts.breaker}</ThemedText>
        <ThemedText>Pânico: {groupedCounts.panic}</ThemedText>
        <ThemedText>Incêndio: {groupedCounts.fire}</ThemedText>
      </ThemedView>

      <ThemedView style={styles.deviceCard}>
        <ThemedText type="subtitle">
          Dispositivos Monitorados ({pluralizePt(devices.length, 'dispositivo', 'dispositivos')})
        </ThemedText>
        {devices.length === 0 ? (
          <ThemedText>Nenhum dispositivo encontrado. Verifique a conexão.</ThemedText>
        ) : (
          devices.map((device) => (
            <ThemedText key={device.id} style={styles.deviceItem}>
              • {device.name}
            </ThemedText>
          ))
        )}
      </ThemedView>

      <ThemedView style={styles.stepContainer}>
        <ThemedText type="subtitle">Eventos Recentes</ThemedText>
      </ThemedView>

      <ThemedView>
        {loading ? <ThemedText>A carregar alertas...</ThemedText> : null}
        {!loading && alerts.length === 0 ? (
          <ThemedText>Nenhuma condição de alerta detetada.</ThemedText>
        ) : null}

        {alerts.map((item) => (
          <ThemedView
            key={item.id}
            style={[styles.eventCard, item.severity === 'critical' ? styles.criticalCard : null]}>
            <ThemedText type="defaultSemiBold">{item.message}</ThemedText>
            <ThemedText style={styles.eventTime}>
              {new Date(item.timestamp).toLocaleTimeString('pt-PT', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              })}{' '}
              • {formatRelativeTimePt(item.timestamp, now)}
            </ThemedText>
          </ThemedView>
        ))}
      </ThemedView>
    </ParallaxScrollView>
  );
}

const styles = StyleSheet.create({
  titleContainer: {
    gap: 6,
  },
  stepContainer: {
    gap: 8,
    marginBottom: 8,
  },
  headerBlob: {
    height: 190,
    width: 300,
    borderRadius: 30,
    transform: [{ rotate: '-7deg' }],
    backgroundColor: '#6BB58A',
    opacity: 0.18,
    position: 'absolute',
    bottom: -20,
    left: -20,
  },
  statusCard: {
    borderRadius: 14,
    padding: 14,
    gap: 4,
    marginBottom: 12,
    backgroundColor: 'rgba(107,181,138,0.10)',
  },
  statusUp: {
    color: '#2C8A52',
  },
  statusDown: {
    color: '#B0413E',
  },
  errorText: {
    color: '#B0413E',
  },
  metricsRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 8,
  },
  summaryText: {
    marginBottom: 12,
    opacity: 0.75,
  },
  metricCard: {
    flex: 1,
    borderRadius: 12,
    padding: 12,
    backgroundColor: 'rgba(0,0,0,0.04)',
  },
  metricCritical: {
    fontSize: 26,
    color: '#B0413E',
  },
  metricNeutral: {
    fontSize: 26,
    color: '#23607A',
  },
  kindCard: {
    borderRadius: 12,
    padding: 12,
    gap: 4,
    marginBottom: 12,
    backgroundColor: 'rgba(35,96,122,0.08)',
  },
  safeBanner: {
    borderRadius: 12,
    padding: 12,
    gap: 4,
    marginBottom: 12,
    backgroundColor: 'rgba(44,138,82,0.14)',
  },
  deviceCard: {
    borderRadius: 12,
    padding: 12,
    gap: 4,
    marginBottom: 12,
    backgroundColor: 'rgba(0,0,0,0.04)',
  },
  deviceItem: {
    fontSize: 14,
    marginBottom: 2,
  },
  eventCard: {
    borderRadius: 12,
    padding: 12,
    gap: 4,
    marginBottom: 10,
    backgroundColor: 'rgba(0,0,0,0.04)',
  },
  eventTime: {
    fontSize: 12,
    opacity: 0.55,
  },
  criticalCard: {
    backgroundColor: 'rgba(176,65,62,0.13)',
  },
});
