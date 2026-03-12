import { ScrollView, StyleSheet, View } from 'react-native';

import { useAlerts } from '@/components/alerts-provider';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';

const categoryLabels: Record<string, string> = {
  ms: 'Smart Lock',
  dlq: 'Circuit Breaker',
  tdq: 'Smart Switch',
  jtmspro: 'Smart Lock Pro',
};

const eventLabels: Record<string, string> = {
  low_battery: 'Low battery',
  dead_battery: 'Dead battery',
  breaker_tripped: 'Breaker tripped',
  fire_alarm: 'Fire alarm',
  panic_button: 'Panic button',
};

export default function DevicesScreen() {
  const { dashboard } = useAlerts();
  const online = dashboard.devices.filter((d) => d.online).length;
  const withAlerts = dashboard.devices.filter((d) => d.activeEvents.length > 0).length;

  return (
    <ScrollView contentContainerStyle={styles.content}>
      <ThemedView style={styles.header}>
        <ThemedText type="title">Devices</ThemedText>
        <View style={styles.statsRow}>
          <ThemedView style={styles.stat}>
            <ThemedText type="subtitle">{dashboard.devices.length}</ThemedText>
            <ThemedText>total</ThemedText>
          </ThemedView>
          <ThemedView style={styles.stat}>
            <ThemedText type="subtitle">{online}</ThemedText>
            <ThemedText>online</ThemedText>
          </ThemedView>
          <ThemedView style={styles.stat}>
            <ThemedText type="subtitle" style={withAlerts > 0 ? styles.alertNumber : undefined}>
              {withAlerts}
            </ThemedText>
            <ThemedText>with alerts</ThemedText>
          </ThemedView>
        </View>
      </ThemedView>

      {dashboard.devices.length === 0 ? (
        <ThemedView style={styles.empty}>
          <ThemedText>No devices yet — waiting for first poll.</ThemedText>
        </ThemedView>
      ) : (
        dashboard.devices.map((device) => (
          <ThemedView
            key={device.id}
            style={[styles.card, device.activeEvents.length > 0 && styles.cardAlert]}>
            <View style={styles.cardTop}>
              <ThemedText type="defaultSemiBold" style={styles.deviceName}>
                {device.name}
              </ThemedText>
              <View style={[styles.dot, device.online ? styles.dotOnline : styles.dotOffline]} />
            </View>
            <ThemedText style={styles.category}>
              {categoryLabels[device.category] ?? device.category}
            </ThemedText>
            {typeof device.batteryLevel === 'number' && (
              <ThemedText>Battery: {device.batteryLevel}%</ThemedText>
            )}
            {device.activeEvents.length > 0 && (
              <View style={styles.eventTags}>
                {device.activeEvents.map((ev) => (
                  <View key={ev} style={styles.tag}>
                    <ThemedText style={styles.tagText}>
                      {eventLabels[ev] ?? ev}
                    </ThemedText>
                  </View>
                ))}
              </View>
            )}
          </ThemedView>
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: {
    padding: 20,
    gap: 12,
  },
  header: {
    borderRadius: 24,
    padding: 20,
    gap: 16,
    backgroundColor: 'rgba(88,129,87,0.10)',
    marginBottom: 4,
  },
  statsRow: {
    flexDirection: 'row',
    gap: 12,
  },
  stat: {
    flex: 1,
    alignItems: 'center',
    gap: 2,
  },
  alertNumber: {
    color: '#B02A37',
  },
  empty: {
    padding: 20,
    borderRadius: 18,
    backgroundColor: 'rgba(148,163,184,0.10)',
  },
  card: {
    borderRadius: 18,
    padding: 16,
    gap: 6,
    backgroundColor: 'rgba(148,163,184,0.10)',
  },
  cardAlert: {
    backgroundColor: 'rgba(176,42,55,0.08)',
    borderWidth: 1,
    borderColor: 'rgba(176,42,55,0.25)',
  },
  cardTop: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  deviceName: {
    flex: 1,
  },
  dot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  dotOnline: {
    backgroundColor: '#2D6A4F',
  },
  dotOffline: {
    backgroundColor: '#94A3B8',
  },
  category: {
    opacity: 0.6,
    fontSize: 13,
  },
  eventTags: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginTop: 4,
  },
  tag: {
    backgroundColor: '#B02A37',
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 3,
  },
  tagText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '700',
  },
});
