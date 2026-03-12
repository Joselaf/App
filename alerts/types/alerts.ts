export type AlertEventType =
  | 'low_battery'
  | 'dead_battery'
  | 'breaker_tripped'
  | 'fire_alarm'
  | 'panic_button';

export type AlertSeverity = 'info' | 'warning' | 'critical';
export type AlertStatus = 'active' | 'cleared';

export type AlertEvent = {
  id: string;
  eventType: AlertEventType;
  severity: AlertSeverity;
  status: AlertStatus;
  title: string;
  message: string;
  timestamp: string;
  deviceId: string;
  deviceName: string;
  metadata?: Record<string, boolean | number | string | null>;
};

export type MonitoredDevice = {
  id: string;
  name: string;
  category?: string | null;
  online: boolean;
  batteryLevel?: number | null;
  lastSeenAt?: string | null;
  activeEvents: AlertEventType[];
};

export type DashboardResponse = {
  monitorHealthy: boolean;
  tuyaConnected: boolean;
  connectionError: string | null;
  lastPollAt: string | null;
  devices: MonitoredDevice[];
  recentAlerts: AlertEvent[];
};

export type HealthResponse = {
  status: string;
  monitorHealthy: boolean;
  tuyaConfigured: boolean;
  tuyaConnected: boolean;
  connectionError: string | null;
  lastPollAt: string | null;
  subscriberCount: number;
};

export type SubscriptionRegistration = {
  ok: boolean;
  registeredAt: string;
};