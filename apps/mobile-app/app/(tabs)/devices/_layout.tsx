import { Stack } from 'expo-router';

import { useColorScheme } from '@/hooks/use-color-scheme';
import { getMobilePalette } from '@/lib/mobile-theme';

export default function DevicesLayout() {
  const colorScheme = useColorScheme();
  const palette = getMobilePalette(colorScheme);

  return (
    <Stack
      screenOptions={{
        contentStyle: { backgroundColor: palette.background },
        headerShadowVisible: false,
        headerStyle: { backgroundColor: palette.background },
        headerTintColor: palette.text,
        headerTitleStyle: {
          color: palette.text,
          fontWeight: '700',
        },
      }}>
      <Stack.Screen name="index" options={{ headerShown: false }} />
      <Stack.Screen
        name="[deviceId]"
        options={{
          title: 'Device detail',
          headerBackTitle: 'Devices',
        }}
      />
    </Stack>
  );
}
