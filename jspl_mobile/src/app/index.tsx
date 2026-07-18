import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, ActivityIndicator, View, BackHandler, Pressable } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { WebView } from 'react-native-webview';
import { ThemedText } from '@/components/themed-text';
import { Spacing } from '@/constants/theme';

export default function HomeScreen() {
  const [loading, setLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [webviewKey, setWebviewKey] = useState(0);
  const webViewRef = useRef<WebView>(null);
  const [canGoBack, setCanGoBack] = useState(false);

  const PORTAL_URL = 'https://subjugular-shrilly-zada.ngrok-free.dev/';

  // Handle hardware/gesture back press to navigate backward in the WebView instead of exiting the app
  useEffect(() => {
    const onBackPress = () => {
      if (webViewRef.current && canGoBack) {
        webViewRef.current.goBack();
        return true;
      }
      return false;
    };

    const subscription = BackHandler.addEventListener('hardwareBackPress', onBackPress);
    return () => {
      subscription.remove();
    };
  }, [canGoBack]);

  const handleNavigationStateChange = (navState: any) => {
    setCanGoBack(navState.canGoBack);
  };

  if (hasError) {
    return (
      <SafeAreaView style={styles.errorContainer}>
        <ThemedText style={styles.errorTitle} type="title">Jindal Steel</ThemedText>
        <ThemedText style={styles.errorSubtitle}>
          Unable to reach the Operations Portal. Please check your network connection and try again.
        </ThemedText>
        
        <Pressable 
          style={styles.retryButton} 
          onPress={() => {
            setHasError(false);
            setWebviewKey(prev => prev + 1);
          }}
        >
          <ThemedText style={styles.retryButtonText} type="defaultSemiBold">🔄 Retry Connection</ThemedText>
        </Pressable>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['top', 'left', 'right']}>
      <WebView
        key={webviewKey}
        ref={webViewRef}
        source={{
          uri: PORTAL_URL,
          headers: {
            'Bypass-Tunnel-Reminder': 'true',
          },
        }}
        onNavigationStateChange={handleNavigationStateChange}
        onError={() => setHasError(true)}
        onHttpError={() => setHasError(true)}
        incognito={false}
        cacheEnabled={true}
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
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: Spacing.five,
    backgroundColor: '#f8f9fa',
  },
  errorTitle: {
    fontSize: 24,
    color: '#dc3545',
    fontWeight: 'bold',
    marginBottom: Spacing.two,
  },
  errorSubtitle: {
    fontSize: 14,
    color: '#6c757d',
    textAlign: 'center',
    marginBottom: Spacing.five,
    lineHeight: 20,
  },
  retryButton: {
    height: 48,
    width: '100%',
    maxWidth: 300,
    backgroundColor: '#002855',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: Spacing.three,
  },
  retryButtonText: {
    color: '#fff',
    fontSize: 16,
  },
  webview: {
    flex: 1,
  },
  loaderContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
  },
});
