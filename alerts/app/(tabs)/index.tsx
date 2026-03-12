import { StyleSheet, View } from 'react-native';

import { AlertEventCard } from '@/components/alert-event-card';
import { useAlerts } from '@/components/alerts-provider';
import ParallaxScrollView from '@/components/parallax-scroll-view';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Fonts } from '@/constants/theme';

export default function HomeScreen() {
  const { dashboard, refresh } = useAlerts();
  const activeCount = dashboard.recentAlerts.filter((alert) => alert.status === 'active').length;
  const criticalCount = dashboard.recentAlerts.filter((alert) => alert.severity === 'critical').length;
  const statusLabel = dashboard.tuyaConnected ? 'Monitor connected' : 'Tuya unavailable';

  return (
    <ParallaxScrollView
      headerBackgroundColor={{ light: '#F1E6D8', dark: '#2B2117' }}
      headerImage={<View style={styles.headerGlow} />}>
      <ThemedView style={styles.titleContainer}>
        <ThemedText type="title" style={styles.title}>
          Alert command
        </ThemedText>
      </ThemedView>
      <ThemedView style={styles.metricsRow}>
        <ThemedView style={styles.metricCard}>
          <ThemedText type="subtitle">{dashboard.devices.length}</ThemedText>
          <ThemedText>devices monitored</ThemedText>
        </ThemedView>
        <ThemedView style={styles.metricCard}>
          <ThemedText type="subtitle">{activeCount}</ThemedText>
          <ThemedText>active alerts</ThemedText>
        </ThemedView>
        <ThemedView style={styles.metricCard}>
          <ThemedText type="subtitle">{criticalCount}</ThemedText>
          <ThemedText>critical events</ThemedText>
        </ThemedView>
      </ThemedView>
      <ThemedView style={styles.statusBar}>
        <ThemedText style={styles.statusDot}>{dashboard.monitorHealthy ? '🟢' : '🔴'}</ThemedText>
        <ThemedText>
          {statusLabel}
          {dashboard.lastPollAt
            ? `  ·  ${new Date(dashboard.lastPollAt).toLocaleTimeString()}`
            : ''}
        </ThemedText>
        <ThemedText type="link" onPress={refresh} style={styles.refreshLink}>
          Refresh
        </ThemedText>
      </ThemedView>
      {dashboard.connectionError ? (
        <ThemedView style={styles.statusErrorCard}>
          <ThemedText type="defaultSemiBold">Tuya connection error</ThemedText>
          <ThemedText>{dashboard.connectionError}</ThemedText>
        </ThemedView>
      ) : null}
      <ThemedView style={styles.section}>
        <ThemedText type="subtitle">Recent events</ThemedText>
        {dashboard.recentAlerts.length === 0 ? (
          <ThemedText>No alerts received yet.</ThemedText>
        ) : (
          dashboard.recentAlerts.slice(0, 3).map((event) => (
            <AlertEventCard key={event.id} event={event} />
          ))
        )}
      </ThemedView>
      <ThemedView style={styles.section}>
        <ThemedText type="subtitle">Device snapshot</ThemedText>
        {dashboard.devices.length === 0 ? (
          <ThemedText>No devices reported yet.</ThemedText>
        ) : (
          dashboard.devices.slice(0, 5).map((device) => (
            <ThemedView key={device.id} style={styles.deviceRow}>
              <ThemedText type="defaultSemiBold">{device.name}</ThemedText>
              <ThemedText>
                {device.online ? 'online' : 'offline'}
                {typeof device.batteryLevel === 'number' ? ` • battery ${device.batteryLevel}%` : ''}
              </ThemedText>
            </ThemedView>
          ))
        )}
      </ThemedView>
    </ParallaxScrollView>
  );
}

const styles = StyleSheet.create({
  titleContainer: {
    paddingTop: 8,
  },
  title: {
    fontFamily: Fonts.rounded,
  },
  headerGlow: {
    width: 260,
    height: 260,
    borderRadius: 130,
    backgroundColor: '#D9653B',
    opacity: 0.22,
    position: 'absolute',
    right: 12,
    top: 18,
  },
  metricsRow: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 16,
  },
  metricCard: {
    flex: 1,
    padding: 14,
    borderRadius: 18,
    backgroundColor: 'rgba(217,101,59,0.08)',
    gap: 4,
  },
  statusBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 14,
    backgroundColor: 'rgba(31,41,55,0.06)',
    marginBottom: 4,
  },
  statusDot: {
    fontSize: 14,
  },
  refreshLink: {
    marginLeft: 'auto',
  },
  section: {
    gap: 12,
    marginBottom: 16,
  },
  statusErrorCard: {
    gap: 6,
    marginBottom: 16,
    padding: 14,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(185,28,28,0.22)',
    backgroundColor: 'rgba(185,28,28,0.08)',
  },
  deviceRow: {
    gap: 4,
    padding: 14,
    borderRadius: 18,
    backgroundColor: 'rgba(148,163,184,0.10)',
  },
});
