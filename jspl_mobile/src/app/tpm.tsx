import React from 'react';
import { StyleSheet, Pressable } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';

export default function TPMScreen() {
  const params = useLocalSearchParams();
  const router = useRouter();
  const departmentId = Number(params.department_id);
  const departmentName = params.department_name;

  const navigateToFuguai = () => {
    router.push({
      pathname: '/fuguai',
      params: { department_id: departmentId, department_name: departmentName },
    });
  };

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.safeArea}>
        {/* Header */}
        <ThemedView style={styles.header}>
          <Pressable style={styles.backButton} onPress={() => router.back()}>
            <ThemedText style={styles.backButtonText} type="defaultSemiBold">← Back</ThemedText>
          </Pressable>
          <ThemedView style={styles.headerTitleContainer}>
            <ThemedText style={styles.headerTitle} type="title">TPM Portal</ThemedText>
            <ThemedText style={styles.headerSub} type="small">{departmentName}</ThemedText>
          </ThemedView>
        </ThemedView>

        <ThemedView style={styles.content}>
          <ThemedText style={styles.sectionTitle} type="defaultSemiBold">Select Module</ThemedText>

          {/* Fuguai Register Tab */}
          <Pressable style={({ pressed }) => [styles.menuCard, pressed && styles.pressed]} onPress={navigateToFuguai}>
            <ThemedView style={styles.menuIconContainer}>
              <ThemedText style={styles.menuIcon}>📸</ThemedText>
            </ThemedView>
            <ThemedView style={styles.menuTextContainer}>
              <ThemedText style={styles.menuTitle} type="defaultSemiBold">Fuguai Register</ThemedText>
              <ThemedText style={styles.menuDesc} type="small">Log abnormalities, take before/after photos directly using camera.</ThemedText>
            </ThemedView>
          </Pressable>

          {/* OPL Sheets */}
          <Pressable style={[styles.menuCard, styles.disabledCard]}>
            <ThemedView style={styles.menuIconContainer}>
              <ThemedText style={styles.menuIcon}>📄</ThemedText>
            </ThemedView>
            <ThemedView style={styles.menuTextContainer}>
              <ThemedText style={styles.menuTitle} type="defaultSemiBold">OPL Sheets</ThemedText>
              <ThemedText style={styles.badgeText} type="small">Coming Soon</ThemedText>
              <ThemedText style={styles.menuDesc} type="small">One Point Lessons tracking and sheets generation.</ThemedText>
            </ThemedView>
          </Pressable>

          {/* Kaizen Sheets */}
          <Pressable style={[styles.menuCard, styles.disabledCard]}>
            <ThemedView style={styles.menuIconContainer}>
              <ThemedText style={styles.menuIcon}>💡</ThemedText>
            </ThemedView>
            <ThemedView style={styles.menuTextContainer}>
              <ThemedText style={styles.menuTitle} type="defaultSemiBold">Kaizen Sheets</ThemedText>
              <ThemedText style={styles.badgeText} type="small">Coming Soon</ThemedText>
              <ThemedText style={styles.menuDesc} type="small">Log continuous improvement projects, loss categories, and benefits.</ThemedText>
            </ThemedView>
          </Pressable>

          {/* Workstation KPIs */}
          <Pressable style={[styles.menuCard, styles.disabledCard]}>
            <ThemedView style={styles.menuIconContainer}>
              <ThemedText style={styles.menuIcon}>📈</ThemedText>
            </ThemedView>
            <ThemedView style={styles.menuTextContainer}>
              <AlignLeftText style={styles.menuTitle} type="defaultSemiBold">Workstation KPIs</AlignLeftText>
              <ThemedText style={styles.badgeText} type="small">Coming Soon</ThemedText>
              <ThemedText style={styles.menuDesc} type="small">Inspect specific workstation KPI targets vs monthly actuals.</ThemedText>
            </ThemedView>
          </Pressable>

        </ThemedView>
      </SafeAreaView>
    </ThemedView>
  );
}

// Simple helper to align text
const AlignLeftText = ({ style, type, children }: any) => (
  <ThemedText style={style} type={type}>{children}</ThemedText>
);

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
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
    backgroundColor: 'transparent',
  },
  headerTitle: {
    fontSize: 18,
    color: '#002855',
    fontWeight: 'bold',
  },
  headerSub: {
    color: '#666',
  },
  content: {
    padding: Spacing.four,
    flex: 1,
  },
  sectionTitle: {
    fontSize: 15,
    color: '#495057',
    marginBottom: Spacing.four,
  },
  menuCard: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#dee2e6',
    borderRadius: 8,
    padding: Spacing.four,
    marginBottom: Spacing.three,
    alignItems: 'center',
  },
  pressed: {
    opacity: 0.9,
    backgroundColor: '#f8f9fa',
  },
  disabledCard: {
    opacity: 0.6,
    backgroundColor: '#e9ecef',
  },
  menuIconContainer: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#f1f3f5',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: Spacing.three,
  },
  menuIcon: {
    fontSize: 22,
  },
  menuTextContainer: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  menuTitle: {
    fontSize: 15,
    color: '#212529',
  },
  menuDesc: {
    fontSize: 12,
    color: '#6c757d',
    marginTop: 2,
  },
  badgeText: {
    color: '#6c757d',
    fontWeight: 'bold',
    fontSize: 9,
    textTransform: 'uppercase',
    marginTop: 2,
  },
});
