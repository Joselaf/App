import { StyleSheet } from 'react-native';

import type { AlertEvent } from '@/types/alerts';

import { ThemedText } from './themed-text';
import { ThemedView } from './themed-view';

const severityColors = {
  info: '#2D6A4F',
  warning: '#C77D00',
  critical: '#B02A37',
};

export function AlertEventCard({ event }: { event: AlertEvent }) {
  return (
    <ThemedView style={styles.card}>
      <ThemedView style={[styles.badge, { backgroundColor: severityColors[event.severity] }]}>
        <ThemedText style={styles.badgeText}>{event.severity.toUpperCase()}</ThemedText>
      </ThemedView>
      <ThemedText type="defaultSemiBold">{event.title}</ThemedText>
      <ThemedText>{event.message}</ThemedText>
      <ThemedText>
        {event.deviceName} • {new Date(event.timestamp).toLocaleString()}
      </ThemedText>
      <ThemedText>
        {event.status === 'active' ? 'Active event' : 'Recovery event'} • {event.eventType}
      </ThemedText>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  card: {
    gap: 6,
    borderRadius: 18,
    padding: 16,
    backgroundColor: 'rgba(148,163,184,0.12)',
  },
  badge: {
    alignSelf: 'flex-start',
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  badgeText: {
    color: '#FFFFFF',
    fontSize: 12,
    lineHeight: 16,
    fontWeight: '700',
  },
});