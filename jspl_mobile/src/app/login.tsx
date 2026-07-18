import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, TextInput, Pressable, ActivityIndicator, Alert, Modal, View } from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { WebView } from 'react-native-webview';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { apiService, getApiBaseUrl, setApiBaseUrl, API_BASE_URL } from '@/services/api';

export default function LoginScreen() {
  const [webUrl, setWebUrl] = useState<string | null>(null);
  const [settingsVisible, setSettingsVisible] = useState(false);
  const [tempBaseUrl, setTempBaseUrl] = useState('');
  const [webviewKey, setWebviewKey] = useState(0);
  const webViewRef = useRef<WebView>(null);
  const router = useRouter();

  // Load URL and check auth on mount
  useEffect(() => {
    async function init() {
      const authenticated = await apiService.isAuthenticated();
      if (authenticated) {
        router.replace('/');
        return;
      }

      const activeUrl = await getApiBaseUrl();
      const cleanBase = activeUrl.replace(/\/api$/, '');
      setWebUrl(`${cleanBase}/login/`);
    }
    init();
  }, []);

  const handleMessage = async (event: any) => {
    try {
      const data = JSON.parse(event.nativeEvent.data);
      if (data.type === 'MOBILE_LOGIN_SUCCESS') {
        if (data.access && data.refresh) {
          await AsyncStorage.setItem('access_token', data.access);
          await AsyncStorage.setItem('refresh_token', data.refresh);
          router.replace('/');
        }
      }
    } catch (e) {
      console.log('[Login WebView Message Error]', e);
    }
  };

  const saveSettings = async () => {
    if (!tempBaseUrl.trim()) {
      Alert.alert('Error', 'API URL cannot be empty.');
      return;
    }
    await setApiBaseUrl(tempBaseUrl.trim());
    const cleanBase = tempBaseUrl.trim().replace(/\/api$/, '');
    setWebUrl(`${cleanBase}/login/`);
    setWebviewKey(prev => prev + 1);
    setSettingsVisible(false);
    Alert.alert('Success', 'API Server URL updated.');
  };

  const resetSettings = async () => {
    await setApiBaseUrl('');
    setTempBaseUrl(API_BASE_URL);
    const cleanBase = API_BASE_URL.replace(/\/api$/, '');
    setWebUrl(`${cleanBase}/login/`);
    setWebviewKey(prev => prev + 1);
    setSettingsVisible(false);
    Alert.alert('Reset', 'API URL has been reset to default.');
  };

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea} edges={['top', 'left', 'right']}>
        {/* Settings Header Bar */}
        <ThemedView style={styles.headerBar}>
          <ThemedText style={styles.headerTitle}>JSPL Portal Login</ThemedText>
          <Pressable
            style={styles.settingsIcon}
            onPress={async () => {
              const currentUrl = await getApiBaseUrl();
              setTempBaseUrl(currentUrl);
              setSettingsVisible(true);
            }}
          >
            <ThemedText style={styles.settingsIconText}>⚙️ Server Settings</ThemedText>
          </Pressable>
        </ThemedView>

        {/* WebView */}
        {webUrl ? (
          <WebView
            key={webviewKey}
            ref={webViewRef}
            source={{
              uri: webUrl,
              headers: {
                'Bypass-Tunnel-Reminder': 'true',
              },
            }}
            onMessage={handleMessage}
            userAgent="JSPLMobileApp/1.0 (iPhone; Mobile)"
            incognito={false}
            domStorageEnabled={true}
            style={styles.webview}
            startInLoadingState={true}
            renderLoading={() => (
              <View style={styles.loaderContainer}>
                <ActivityIndicator size="large" color="#002855" />
              </View>
            )}
          />
        ) : (
          <View style={styles.loaderContainer}>
            <ActivityIndicator size="large" color="#002855" />
          </View>
        )}

        {/* Server Settings Modal */}
        <Modal
          visible={settingsVisible}
          transparent={true}
          animationType="fade"
          onRequestClose={() => setSettingsVisible(false)}
        >
          <ThemedView style={styles.modalOverlay}>
            <ThemedView style={styles.modalContent}>
              <ThemedText style={styles.modalTitle} type="subtitle">Server Settings</ThemedText>
              
              <ThemedText style={styles.modalLabel} type="defaultSemiBold">API Base URL</ThemedText>
              <TextInput
                style={styles.modalInput}
                value={tempBaseUrl}
                onChangeText={setTempBaseUrl}
                placeholder="https://your-server-ip/api"
                placeholderTextColor="#888"
                autoCapitalize="none"
                autoCorrect={false}
              />
              
              <ThemedText style={styles.modalHelpText} type="small">
                Enter your backend server's URL. You can use your dynamic tunnel URL (e.g. localtunnel/ngrok) or a public domain.
              </ThemedText>

              <ThemedView style={styles.modalActions}>
                <Pressable
                  style={[styles.modalButton, styles.modalCancelButton]}
                  onPress={() => setSettingsVisible(false)}
                >
                  <ThemedText style={styles.modalButtonTextCancel}>Cancel</ThemedText>
                </Pressable>
                
                <Pressable
                  style={[styles.modalButton, styles.modalSaveButton]}
                  onPress={saveSettings}
                >
                  <ThemedText style={styles.modalButtonText}>Save</ThemedText>
                </Pressable>
              </ThemedView>
              
              <Pressable
                style={styles.modalResetButton}
                onPress={resetSettings}
              >
                <ThemedText style={styles.modalResetButtonText}>Reset to Default</ThemedText>
              </Pressable>
            </ThemedView>
          </ThemedView>
        </Modal>
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  safeArea: {
    flex: 1,
  },
  headerBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.four,
    paddingVertical: Spacing.three,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#dee2e6',
  },
  headerTitle: {
    fontSize: 16,
    color: '#002855',
    fontWeight: 'bold',
  },
  settingsIcon: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 20,
    backgroundColor: '#e9ecef',
    borderWidth: 1,
    borderColor: '#dee2e6',
  },
  settingsIconText: {
    fontSize: 12,
    color: '#495057',
    fontWeight: '600',
  },
  webview: {
    flex: 1,
  },
  loaderContainer: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
    zIndex: 99,
  },
  modalOverlay: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.5)',
  },
  modalContent: {
    width: '85%',
    maxWidth: 360,
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: Spacing.four,
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 12,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#002855',
    marginBottom: Spacing.three,
    textAlign: 'center',
  },
  modalLabel: {
    fontSize: 14,
    color: '#495057',
    marginBottom: Spacing.one,
  },
  modalInput: {
    height: 48,
    borderWidth: 1,
    borderColor: '#ced4da',
    borderRadius: 6,
    paddingHorizontal: Spacing.three,
    fontSize: 14,
    color: '#212529',
    backgroundColor: '#f8f9fa',
    marginBottom: Spacing.two,
  },
  modalHelpText: {
    color: '#666',
    fontSize: 12,
    marginBottom: Spacing.three,
    lineHeight: 16,
  },
  modalActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: Spacing.two,
    marginBottom: Spacing.two,
    backgroundColor: 'transparent',
  },
  modalButton: {
    flex: 1,
    height: 44,
    borderRadius: 6,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalCancelButton: {
    backgroundColor: '#e9ecef',
    borderWidth: 1,
    borderColor: '#ced4da',
  },
  modalSaveButton: {
    backgroundColor: '#002855',
  },
  modalButtonText: {
    color: '#fff',
    fontWeight: 'bold',
    fontSize: 14,
  },
  modalButtonTextCancel: {
    color: '#495057',
    fontSize: 14,
  },
  modalResetButton: {
    alignItems: 'center',
    paddingVertical: Spacing.two,
    marginTop: Spacing.one,
  },
  modalResetButtonText: {
    color: '#dc3545',
    fontSize: 13,
    textDecorationLine: 'underline',
    fontWeight: '600',
  },
});
