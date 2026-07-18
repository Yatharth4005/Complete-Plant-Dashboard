import React, { useState, useEffect } from 'react';
import { StyleSheet, Pressable, ActivityIndicator, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { WebView } from 'react-native-webview';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { apiService, getApiBaseUrl } from '@/services/api';

export default function WebViewScreen() {
  const params = useLocalSearchParams();
  const router = useRouter();
  const title = params.title as string || 'Department Module';
  const targetPath = params.url as string || '/';

  const [webUrl, setWebUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function prepareUrl() {
      try {
        // Refresh token first to get a freshly minted access token
        let token = await apiService.refreshToken();
        if (!token) {
          token = await AsyncStorage.getItem('access_token');
        }
        const baseUrl = await getApiBaseUrl();
        const cleanBase = baseUrl.replace(/\/api$/, '');
        // Build auto-login redirection URL
        const autoLoginUrl = `${cleanBase}/api/auth/auto-login/?token=${token}&next=${encodeURIComponent(targetPath)}`;
        setWebUrl(autoLoginUrl);
      } catch (err) {
        console.error('Error loading token for WebView:', err);
      }
    }
    prepareUrl();
  }, [targetPath]);

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        {/* Header Bar */}
        <ThemedView style={styles.header}>
          <Pressable style={styles.backButton} onPress={() => router.back()}>
            <ThemedText style={styles.backButtonText} type="defaultSemiBold">← Back</ThemedText>
          </Pressable>
          <ThemedView style={styles.headerTitleContainer}>
            <ThemedText style={styles.headerTitle} type="title">{title}</ThemedText>
          </ThemedView>
        </ThemedView>

        {webUrl ? (
          <View style={styles.webviewContainer}>
            <WebView
              source={{
                uri: webUrl,
                headers: {
                  'Bypass-Tunnel-Reminder': 'true',
                },
              }}
              injectedJavaScriptBeforeContentLoaded={`
                (function() {
                  window.onerror = function(message, source, lineno, colno, error) {
                    window.ReactNativeWebView.postMessage(JSON.stringify({
                      type: 'ERROR',
                      message: message,
                      source: source,
                      line: lineno,
                      col: colno
                    }));
                    return false;
                  };
                  var log = console.log;
                  console.log = function() {
                    var args = Array.prototype.slice.call(arguments);
                    window.ReactNativeWebView.postMessage(JSON.stringify({
                      type: 'LOG',
                      message: args.join(' ')
                    }));
                    log.apply(console, arguments);
                  };
                  var err = console.error;
                  console.error = function() {
                    var args = Array.prototype.slice.call(arguments);
                    window.ReactNativeWebView.postMessage(JSON.stringify({
                      type: 'CONSOLE_ERROR',
                      message: args.join(' ')
                    }));
                    err.apply(console, arguments);
                  };
                })();
                true;
              `}
              onMessage={async (event) => {
                try {
                  const data = JSON.parse(event.nativeEvent.data);
                  console.log(`[WebView ${data.type}]`, data.message || data);
                  if (data.type === 'TOKEN_ERROR') {
                    await apiService.logout();
                    router.replace('/login');
                  }
                } catch (e) {
                  console.log('[WebView Message]', event.nativeEvent.data);
                }
              }}
              injectedJavaScript={`
                if (document.body.innerText.includes('Token is expired') || document.body.innerText.includes('Invalid or expired token')) {
                  window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'TOKEN_ERROR' }));
                }
                true;
              `}
              incognito={false}
              cacheEnabled={true}
              cacheMode="LOAD_DEFAULT"
              domStorageEnabled={true}
              userAgent="JSPLMobileApp/1.0 (iPhone; Mobile)"
              style={styles.webview}
              onLoadEnd={() => setLoading(false)}
              startInLoadingState={true}
              renderLoading={() => (
                <View style={styles.loaderContainer}>
                  <ActivityIndicator size="large" color="#002855" />
                </View>
              )}
            />
          </View>
        ) : (
          <View style={styles.loaderContainer}>
            <ActivityIndicator size="large" color="#002855" />
          </View>
        )}
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
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.four,
    paddingVertical: Spacing.three,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#dee2e6',
  },
  backButton: {
    paddingRight: Spacing.four,
  },
  backButtonText: {
    color: '#0d6efd',
    fontSize: 15,
  },
  headerTitleContainer: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  headerTitle: {
    fontSize: 16,
    color: '#002855',
    fontWeight: 'bold',
    textAlign: 'center',
  },
  webviewContainer: {
    flex: 1,
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
});
