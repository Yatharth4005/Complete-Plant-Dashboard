import React, { useState, useEffect } from 'react';
import { StyleSheet, ScrollView, Pressable, TextInput, ActivityIndicator, Alert } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { apiService } from '@/services/api';

export default function ChecklistScreen() {
  const params = useLocalSearchParams();
  const router = useRouter();
  const departmentId = Number(params.department_id);
  const departmentName = params.department_name;

  const [schedules, setSchedules] = useState<any[]>([]);
  const [selectedSchedule, setSelectedSchedule] = useState<any>(null);
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]); // YYYY-MM-DD
  const [loadingSchedules, setLoadingSchedules] = useState(true);
  const [loadingChecklist, setLoadingChecklist] = useState(false);
  const [saving, setSaving] = useState(false);

  // Active checklist details
  const [checklist, setChecklist] = useState<any>(null);
  const [items, setItems] = useState<any[]>([]);
  const [shiftIncharge, setShiftIncharge] = useState('');
  const [engineer, setEngineer] = useState('');
  const [operator, setOperator] = useState('');
  const [generalRemark, setGeneralRemark] = useState('');

  // Load schedules
  useEffect(() => {
    async function loadSchedules() {
      try {
        const data = await apiService.getChecklistSchedules(departmentId);
        setSchedules(data);
        setLoadingSchedules(false);
      } catch (error) {
        setLoadingSchedules(false);
        Alert.alert('Error', 'Unable to fetch checklist schedules.');
      }
    }
    loadSchedules();
  }, [departmentId]);

  // Load or Initialize checklist when schedule changes
  const handleSelectSchedule = async (schedule: any) => {
    setSelectedSchedule(schedule);
    setLoadingChecklist(true);
    try {
      const data = await apiService.initializeChecklist(departmentId, schedule.checklist_name, date);
      const chk = data.checklist;
      setChecklist(chk);
      setItems(chk.items || []);
      setShiftIncharge(chk.shift_incharge || schedule.shift_incharge || '');
      setEngineer(chk.engineer || '');
      setOperator(chk.operator || '');
      setGeneralRemark(chk.remark || '');
      setLoadingChecklist(false);
    } catch (error) {
      setLoadingChecklist(false);
      Alert.alert('Error', 'Failed to load or initialize checklist.');
    }
  };

  const handleToggleStatus = (itemId: number, status: 'OK' | 'NOT OK') => {
    setItems((prevItems) =>
      prevItems.map((item) =>
        item.id === itemId
          ? { ...item, status: item.status === status ? null : status } // toggle off if clicked again
          : item
      )
    );
  };

  const handleRemarkChange = (itemId: number, text: string) => {
    setItems((prevItems) =>
      prevItems.map((item) => (item.id === itemId ? { ...item, remarks: text } : item))
    );
  };

  const handleSave = async () => {
    if (!checklist) return;
    
    setSaving(true);
    try {
      const payload = {
        shift_incharge: shiftIncharge,
        engineer: engineer,
        operator: operator,
        remark: generalRemark,
        items: items.map((item) => ({
          id: item.id,
          status: item.status,
          remarks: item.remarks,
        })),
      };

      await apiService.saveChecklist(checklist.id, payload);
      setSaving(false);
      Alert.alert('Success', 'Checklist saved successfully!', [
        { text: 'OK', onPress: () => router.back() }
      ]);
    } catch (error) {
      setSaving(false);
      Alert.alert('Error', 'Failed to save checklist entries.');
    }
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
            <ThemedText style={styles.headerTitle} type="title">Checklist entry</ThemedText>
            <ThemedText style={styles.headerSub} type="small">{departmentName}</ThemedText>
          </ThemedView>
        </ThemedView>

        {loadingSchedules ? (
          <ThemedView style={styles.centerContainer}>
            <ActivityIndicator size="large" color="#002855" />
          </ThemedView>
        ) : (
          <ScrollView contentContainerStyle={styles.scrollContent}>
            {/* Step 1: Select Equipment Checksheet */}
            <ThemedView style={styles.sectionCard}>
              <ThemedText style={styles.sectionLabel} type="defaultSemiBold">Select Equipment Checklist</ThemedText>
              {schedules.length === 0 ? (
                <ThemedText style={styles.infoText} type="small">No active checklist schedules configured.</ThemedText>
              ) : (
                <ThemedView style={styles.scheduleGrid}>
                  {schedules.map((sched) => (
                    <Pressable
                      key={sched.id}
                      style={[
                        styles.scheduleTab,
                        selectedSchedule?.id === sched.id && styles.scheduleTabSelected,
                      ]}
                      onPress={() => handleSelectSchedule(sched)}
                    >
                      <ThemedText
                        style={[
                          styles.scheduleTabText,
                          selectedSchedule?.id === sched.id && styles.scheduleTabTextSelected,
                        ]}
                        type="defaultSemiBold"
                      >
                        {sched.checklist_name}
                      </ThemedText>
                      <ThemedText style={styles.scheduleTabSub} type="small">{sched.frequency}</ThemedText>
                    </Pressable>
                  ))}
                </ThemedView>
              )}
            </ThemedView>

            {/* Checklist details & Items form */}
            {selectedSchedule && (
              <>
                {loadingChecklist ? (
                  <ThemedView style={styles.cardLoading}>
                    <ActivityIndicator size="small" color="#002855" />
                    <ThemedText style={styles.cardLoadingText} type="small">Initializing form...</ThemedText>
                  </ThemedView>
                ) : (
                  checklist && (
                    <ThemedView style={styles.formCard}>
                      {/* Meta information */}
                      <ThemedView style={styles.metaForm}>
                        <ThemedText style={styles.fieldLabel} type="defaultSemiBold">Date</ThemedText>
                        <TextInput style={styles.readOnlyInput} value={date} editable={false} />

                        <ThemedText style={styles.fieldLabel} type="defaultSemiBold">Shift Incharge</ThemedText>
                        <TextInput
                          style={styles.input}
                          placeholder="Enter Shift Incharge"
                          value={shiftIncharge}
                          onChangeText={setShiftIncharge}
                        />

                        <ThemedText style={styles.fieldLabel} type="defaultSemiBold">Engineer</ThemedText>
                        <TextInput
                          style={styles.input}
                          placeholder="Enter Engineer Name"
                          value={engineer}
                          onChangeText={setEngineer}
                        />

                        <ThemedText style={styles.fieldLabel} type="defaultSemiBold">Operator</ThemedText>
                        <TextInput
                          style={styles.input}
                          placeholder="Enter Operator Name"
                          value={operator}
                          onChangeText={setOperator}
                        />
                      </ThemedView>

                      {/* Checklist Items list */}
                      <ThemedText style={styles.itemsHeader} type="defaultSemiBold">Inspection Items</ThemedText>
                      {items.map((item) => {
                        if (item.is_header) {
                          return (
                            <ThemedView key={item.id} style={styles.headerItemContainer}>
                              <ThemedText style={styles.headerItemText} type="defaultSemiBold">
                                {item.action_item}
                              </ThemedText>
                            </ThemedView>
                          );
                        }

                        return (
                          <ThemedView key={item.id} style={styles.actionItemRow}>
                            <ThemedText style={styles.actionText}>{item.action_item}</ThemedText>
                            
                            {/* Toggle Switches (OK / NOT OK) */}
                            <ThemedView style={styles.toggleContainer}>
                              <Pressable
                                style={[
                                  styles.toggleButton,
                                  item.status === 'OK' && styles.toggleOk,
                                ]}
                                onPress={() => handleToggleStatus(item.id, 'OK')}
                              >
                                <ThemedText style={[styles.toggleText, item.status === 'OK' && styles.toggleTextActive]}>OK</ThemedText>
                              </Pressable>

                              <Pressable
                                style={[
                                  styles.toggleButton,
                                  item.status === 'NOT OK' && styles.toggleNotOk,
                                ]}
                                onPress={() => handleToggleStatus(item.id, 'NOT OK')}
                              >
                                <ThemedText style={[styles.toggleText, item.status === 'NOT OK' && styles.toggleTextActive]}>NOT OK</ThemedText>
                              </Pressable>
                            </ThemedView>

                            {/* Item Remark field */}
                            <TextInput
                              style={styles.itemRemarkInput}
                              placeholder="Add specific defect remark if NOT OK..."
                              placeholderTextColor="#aaa"
                              value={item.remarks || ''}
                              onChangeText={(text) => handleRemarkChange(item.id, text)}
                            />
                          </ThemedView>
                        );
                      })}

                      {/* General Remark */}
                      <ThemedText style={styles.fieldLabel} type="defaultSemiBold">General Remark / Remarks</ThemedText>
                      <TextInput
                        style={[styles.input, styles.textArea]}
                        multiline
                        numberOfLines={3}
                        placeholder="Enter general checklist observation remarks..."
                        value={generalRemark}
                        onChangeText={setGeneralRemark}
                      />

                      {/* Submit button */}
                      <Pressable
                        style={({ pressed }) => [
                          styles.submitBtn,
                          pressed && styles.submitBtnPressed,
                          saving && styles.submitBtnDisabled,
                        ]}
                        onPress={handleSave}
                        disabled={saving}
                      >
                        {saving ? (
                          <ActivityIndicator color="#fff" />
                        ) : (
                          <ThemedText style={styles.submitBtnText} type="defaultSemiBold">Submit Checklist</ThemedText>
                        )}
                      </Pressable>
                    </ThemedView>
                  )
                )}
              </>
            )}
          </ScrollView>
        )}
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  safeArea: {
    flex: 1,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
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
  scrollContent: {
    padding: Spacing.four,
  },
  sectionCard: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: Spacing.four,
    borderWidth: 1,
    borderColor: '#dee2e6',
    marginBottom: Spacing.four,
  },
  sectionLabel: {
    fontSize: 15,
    color: '#495057',
    marginBottom: Spacing.three,
  },
  infoText: {
    color: '#6c757d',
  },
  scheduleGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
    backgroundColor: 'transparent',
  },
  scheduleTab: {
    width: '48%',
    padding: Spacing.three,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#dee2e6',
    backgroundColor: '#f8f9fa',
  },
  scheduleTabSelected: {
    borderColor: '#0d6efd',
    backgroundColor: '#f0f7ff',
  },
  scheduleTabText: {
    fontSize: 13,
    color: '#495057',
  },
  scheduleTabTextSelected: {
    color: '#0d6efd',
  },
  scheduleTabSub: {
    fontSize: 10,
    color: '#6c757d',
    marginTop: 2,
  },
  cardLoading: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: Spacing.five,
    borderWidth: 1,
    borderColor: '#dee2e6',
    alignItems: 'center',
    gap: Spacing.two,
  },
  cardLoadingText: {
    color: '#6c757d',
  },
  formCard: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: Spacing.four,
    borderWidth: 1,
    borderColor: '#dee2e6',
    marginBottom: Spacing.four,
  },
  metaForm: {
    backgroundColor: 'transparent',
    marginBottom: Spacing.four,
  },
  fieldLabel: {
    fontSize: 13,
    color: '#495057',
    marginBottom: Spacing.one,
    marginTop: Spacing.two,
  },
  input: {
    height: 40,
    borderWidth: 1,
    borderColor: '#ced4da',
    borderRadius: 5,
    paddingHorizontal: Spacing.three,
    fontSize: 14,
    color: '#212529',
    backgroundColor: '#f8f9fa',
  },
  readOnlyInput: {
    height: 40,
    borderWidth: 1,
    borderColor: '#dee2e6',
    borderRadius: 5,
    paddingHorizontal: Spacing.three,
    fontSize: 14,
    color: '#6c757d',
    backgroundColor: '#e9ecef',
  },
  textArea: {
    height: 80,
    textAlignVertical: 'top',
    paddingVertical: Spacing.two,
    marginBottom: Spacing.four,
  },
  itemsHeader: {
    fontSize: 15,
    color: '#495057',
    borderTopWidth: 1,
    borderTopColor: '#e9ecef',
    paddingTop: Spacing.three,
    marginBottom: Spacing.three,
  },
  headerItemContainer: {
    backgroundColor: '#e9ecef',
    paddingVertical: 6,
    paddingHorizontal: Spacing.three,
    borderRadius: 4,
    marginTop: Spacing.three,
    marginBottom: Spacing.two,
  },
  headerItemText: {
    fontSize: 12,
    color: '#495057',
    fontWeight: 'bold',
  },
  actionItemRow: {
    borderBottomWidth: 1,
    borderBottomColor: '#f1f3f5',
    paddingVertical: Spacing.three,
    backgroundColor: 'transparent',
  },
  actionText: {
    fontSize: 14,
    color: '#212529',
    marginBottom: Spacing.two,
  },
  toggleContainer: {
    flexDirection: 'row',
    gap: Spacing.two,
    backgroundColor: 'transparent',
    marginBottom: Spacing.two,
  },
  toggleButton: {
    paddingHorizontal: Spacing.three,
    paddingVertical: 6,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: '#ced4da',
    backgroundColor: '#fff',
  },
  toggleOk: {
    borderColor: '#198754',
    backgroundColor: '#d1e7dd',
  },
  toggleNotOk: {
    borderColor: '#dc3545',
    backgroundColor: '#f8d7da',
  },
  toggleText: {
    fontSize: 11,
    color: '#495057',
  },
  toggleTextActive: {
    fontWeight: 'bold',
    color: '#212529',
  },
  itemRemarkInput: {
    height: 32,
    borderWidth: 1,
    borderColor: '#ced4da',
    borderRadius: 4,
    paddingHorizontal: Spacing.two,
    fontSize: 12,
    color: '#212529',
    backgroundColor: '#fff',
  },
  submitBtn: {
    height: 46,
    backgroundColor: '#002855',
    borderRadius: 6,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: Spacing.two,
  },
  submitBtnPressed: {
    opacity: 0.9,
  },
  submitBtnDisabled: {
    backgroundColor: '#6c757d',
  },
  submitBtnText: {
    color: '#fff',
    fontSize: 15,
  },
});
