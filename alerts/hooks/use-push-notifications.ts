import Constants from 'expo-constants';
import * as Device from 'expo-device';
import { useEffect, useState } from 'react';
import { Platform } from 'react-native';

import { easProjectId } from '@/constants/config';

type PermissionStatus = 'granted' | 'denied' | 'undetermined' | 'unavailable';

type NotificationsModule = typeof import('expo-notifications');

async function loadNotificationsModule(): Promise<NotificationsModule | null> {
  try {
    return await import('expo-notifications');
  } catch {
    return null;
  }
}

async function registerForPushNotificationsAsync() {
  const isExpoGoAndroid = Platform.OS === 'android' && Constants.appOwnership === 'expo';
  if (isExpoGoAndroid) {
    return {
      expoPushToken: null,
      permissionStatus: 'unavailable' as const,
      error: 'Push notifications are unavailable in Expo Go on Android. Use a development build.',
      isSupportedDevice: Device.isDevice,
    };
  }

  const notifications = await loadNotificationsModule();
  if (!notifications) {
    return {
      expoPushToken: null,
      permissionStatus: 'unavailable' as const,
      error: 'Push notifications are unavailable in Expo Go on Android. Use a development build.',
      isSupportedDevice: Device.isDevice,
    };
  }

  if (Platform.OS === 'android') {
    await notifications.setNotificationChannelAsync('alerts', {
      name: 'alerts',
      importance: notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#D9653B',
    });
  }

  if (!Device.isDevice) {
    return {
      expoPushToken: null,
      permissionStatus: 'unavailable' as const,
      error: 'Use a physical device to receive Expo push notifications.',
      isSupportedDevice: false,
    };
  }

  const existingStatus = await notifications.getPermissionsAsync();
  let finalStatus = existingStatus.status;

  if (finalStatus !== 'granted') {
    const requestStatus = await notifications.requestPermissionsAsync();
    finalStatus = requestStatus.status;
  }

  if (finalStatus !== 'granted') {
    return {
      expoPushToken: null,
      permissionStatus: finalStatus,
      error: 'Notification permission was not granted.',
      isSupportedDevice: true,
    };
  }

  if (!easProjectId) {
    return {
      expoPushToken: null,
      permissionStatus: finalStatus,
      error: 'Missing EAS project ID in Expo config.',
      isSupportedDevice: true,
    };
  }

  const pushToken = await notifications.getExpoPushTokenAsync({ projectId: easProjectId });

  return {
    expoPushToken: pushToken.data,
    permissionStatus: finalStatus,
    error: null,
    isSupportedDevice: true,
  };
}

export function usePushNotifications() {
  const [state, setState] = useState({
    expoPushToken: null as string | null,
    permissionStatus: 'unavailable' as PermissionStatus,
    error: null as string | null,
    isSupportedDevice: false,
  });

  useEffect(() => {
    registerForPushNotificationsAsync()
      .then(setState)
      .catch((error: Error) => {
        setState({
          expoPushToken: null,
          permissionStatus: 'unavailable',
          error: error.message,
          isSupportedDevice: Device.isDevice,
        });
      });
  }, []);

  return state;
}