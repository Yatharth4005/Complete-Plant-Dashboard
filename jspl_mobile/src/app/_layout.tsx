import React from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

export default function RootLayout() {
  return (
    <>
      <StatusBar style="auto" />
      <Stack screenOptions={{ headerShown: false }}>
        <Stack.Screen name="login" options={{ gestureEnabled: false }} />
        <Stack.Screen name="index" options={{ gestureEnabled: false }} />
        <Stack.Screen name="checklist" />
        <Stack.Screen name="tpm" />
        <Stack.Screen name="fuguai" />
        <Stack.Screen name="webview" />
      </Stack>
    </>
  );
}
