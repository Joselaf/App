import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';
import Constants from 'expo-constants';
import { Stack, useRouter } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { Platform } from 'react-native';
import 'react-native-reanimated';

import { AlertsProvider } from '@/components/alerts-provider';
import { useColorScheme } from '@/hooks/use-color-scheme';

export const unstable_settings = {
  anchor: '(tabs)',
};

export default function RootLayout() {
  const colorScheme = useColorScheme();
  const router = useRouter();

  useEffect(() => {
    if (Platform.OS === 'android' && Constants.appOwnership === 'expo') {
      return;
    }

    let responseSubscription: { remove: () => void } | null = null;

    void (async () => {
      try {
        const notifications = await import('expo-notifications');

        notifications.setNotificationHandler({
          handleNotification: async () => ({
            shouldPlaySound: true,
            shouldSetBadge: true,
            shouldShowBanner: true,
            shouldShowList: true,
          }),
        });

        responseSubscription = notifications.addNotificationResponseReceivedListener((response) => {
          const href = response.notification.request.content.data?.href;

          if (typeof href === 'string' && href.length > 0) {
            router.push(href as '/(tabs)/alerts');
            return;
          }

          router.push('/(tabs)/alerts');
        });
      } catch {
        // Expo Go on Android does not support remote notifications.
      }
    })();

    return () => {
      responseSubscription?.remove();
    };
  }, [router]);

  return (
    <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
      <AlertsProvider>
        <Stack>
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen name="modal" options={{ presentation: 'modal', title: 'Modal' }} />
        </Stack>
        <StatusBar style="auto" />
      </AlertsProvider>
    </ThemeProvider>
  );
}
