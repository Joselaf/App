import { Pressable, ScrollView, StyleSheet, View } from 'react-native';

import { AlertEventCard } from '@/components/alert-event-card';
import { useAlerts } from '@/components/alerts-provider';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';

export default function AlertsScreen() {
  const { dashboard, registration, refresh, sendTestNotification, loading, error } = useAlerts();
  const canSendTestPush = Boolean(registration.expoPushToken);
  const needsPushAttention =
    registration.permissionStatus === 'denied' ||
    registration.permissionStatus === 'unavailable' ||
    !registration.expoPushToken;

  const pushAttentionMessage = registration.error
    ? registration.error
    : registration.permissionStatus === 'denied'
      ? 'Notification permission is denied. Enable notifications for this app in system settings.'
      : registration.permissionStatus === 'unavailable'
        ? 'Push notifications are unavailable in this runtime. Use a physical device/dev build.'
        : 'Push token is still loading. Wait a moment and tap Refresh.';

  return (
    <ScrollView contentContainerStyle={styles.content}>
      <ThemedView style={styles.hero}>
        <ThemedText type="title">Alerts</ThemedText>
        <ThemedText>
          Review recent Tuya events, verify Expo push registration, and test delivery through the
          backend.
        </ThemedText>
      </ThemedView>

      <ThemedView style={styles.section}>
        <ThemedText type="subtitle">Push registration</ThemedText>
        <ThemedText>Permission: {registration.permissionStatus || 'unknown'}</ThemedText>
        <ThemedText>
          Device support: {registration.isSupportedDevice ? 'physical device' : 'simulator/web'}
        </ThemedText>
        <ThemedText>
          Token: {registration.expoPushToken ? registration.expoPushToken : 'not available'}
        </ThemedText>
        {registration.error ? <ThemedText>{registration.error}</ThemedText> : null}
      </ThemedView>

      {needsPushAttention ? (
        <ThemedView style={styles.warningBanner}>
          <ThemedText type="defaultSemiBold" style={styles.warningTitle}>
            Push notifications need attention
          </ThemedText>
          <ThemedText>{pushAttentionMessage}</ThemedText>
        </ThemedView>
      ) : null}

      <View style={styles.actions}>
        <Pressable onPress={refresh} style={styles.button}>
          <ThemedText style={styles.buttonText}>{loading ? 'Refreshing...' : 'Refresh now'}</ThemedText>
        </Pressable>
        <Pressable
          onPress={() => void sendTestNotification()}
          disabled={!canSendTestPush}
          style={[styles.button, styles.secondaryButton, !canSendTestPush && styles.buttonDisabled]}>
          <ThemedText style={styles.buttonText}>
            {canSendTestPush ? 'Send test push' : 'Token not ready'}
          </ThemedText>
        </Pressable>
      </View>

      {error ? (
        <ThemedView style={styles.section}>
          <ThemedText type="subtitle">Backend status</ThemedText>
          <ThemedText>{error}</ThemedText>
        </ThemedView>
      ) : null}

      {dashboard.connectionError ? (
        <ThemedView style={styles.warningBanner}>
          <ThemedText type="defaultSemiBold" style={styles.warningTitle}>
            Tuya Cloud is not connected
          </ThemedText>
          <ThemedText>{dashboard.connectionError}</ThemedText>
        </ThemedView>
      ) : null}

      <ThemedView style={styles.section}>
        <ThemedText type="subtitle">Recent alerts</ThemedText>
        {dashboard.recentAlerts.length === 0 ? (
          <ThemedText>No alerts available yet.</ThemedText>
        ) : (
          dashboard.recentAlerts.map((event) => <AlertEventCard key={event.id} event={event} />)
        )}
      </ThemedView>

      <ThemedView style={styles.section}>
        <ThemedText type="subtitle">Monitored devices</ThemedText>
        {dashboard.devices.length === 0 ? (
          <ThemedText>No devices reported yet.</ThemedText>
        ) : (
          dashboard.devices.map((device) => (
            <ThemedView key={device.id} style={styles.deviceRow}>
              <ThemedText type="defaultSemiBold">{device.name}</ThemedText>
              <ThemedText>{device.category || 'unknown category'}</ThemedText>
              <ThemedText>
                {device.online ? 'online' : 'offline'}
                {typeof device.batteryLevel === 'number' ? ` • battery ${device.batteryLevel}%` : ''}
              </ThemedText>
            </ThemedView>
          ))
        )}
      </ThemedView>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: {
    padding: 20,
    gap: 16,
  },
  hero: {
    gap: 8,
    borderRadius: 24,
    padding: 20,
    backgroundColor: 'rgba(217,101,59,0.10)',
  },
  section: {
    gap: 10,
    borderRadius: 20,
    padding: 18,
    backgroundColor: 'rgba(100,116,139,0.08)',
  },
  warningBanner: {
    gap: 6,
    borderRadius: 16,
    padding: 14,
    borderWidth: 1,
    borderColor: 'rgba(199,125,0,0.45)',
    backgroundColor: 'rgba(199,125,0,0.12)',
  },
  warningTitle: {
    color: '#7A4B00',
  },
  actions: {
    flexDirection: 'row',
    gap: 12,
  },
  button: {
    flex: 1,
    borderRadius: 14,
    paddingVertical: 14,
    alignItems: 'center',
    backgroundColor: '#D9653B',
  },
  secondaryButton: {
    backgroundColor: '#3B6C52',
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonText: {
    color: '#FFFFFF',
    fontWeight: '700',
  },
  deviceRow: {
    gap: 4,
    borderRadius: 16,
    padding: 14,
    backgroundColor: 'rgba(15,23,42,0.06)',
  },
});