import React, { useState, useEffect } from 'react';
import { StyleSheet, ScrollView, Pressable, TextInput, Image, ActivityIndicator, Alert, View } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as ImagePicker from 'expo-image-picker';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { apiService, API_BASE_URL, getApiBaseUrl } from '@/services/api';

export default function FuguaiScreen() {
  const params = useLocalSearchParams();
  const router = useRouter();
  const departmentId = Number(params.department_id);
  const departmentName = params.department_name;

  const [tags, setTags] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  // New tag form state
  const [isAdding, setIsAdding] = useState(false);
  const [theme, setTheme] = useState('');
  const [tagColor, setTagColor] = useState<'WHITE' | 'RED'>('WHITE');
  const [beforeImage, setBeforeImage] = useState<string | null>(null);
  const [afterImage, setAfterImage] = useState<string | null>(null);

  // Edit / Rectify existing tag state
  const [selectedTag, setSelectedTag] = useState<any>(null);
  const [isRectifying, setIsRectifying] = useState(false);
  const [activeBaseUrl, setActiveBaseUrl] = useState<string>(API_BASE_URL);

  // Fetch logged Fuguai tags
  const fetchTags = async () => {
    try {
      const data = await apiService.getFuguaiTags(departmentId);
      setTags(data);
      setLoading(false);
    } catch (error) {
      setLoading(false);
      Alert.alert('Error', 'Failed to fetch Fuguai tags.');
    }
  };

  useEffect(() => {
    async function loadBase() {
      try {
        const url = await getApiBaseUrl();
        setActiveBaseUrl(url);
      } catch (e) {
        // ignore
      }
    }
    loadBase();
    fetchTags();
  }, [departmentId]);

  // Request permissions and select image source
  const handleImagePick = (type: 'before' | 'after') => {
    Alert.alert(
      'Select Photo Source',
      'Choose how you want to upload the photo:',
      [
        { text: 'Take Photo (Camera)', onPress: () => capturePhoto(type) },
        { text: 'Choose from Gallery', onPress: () => selectFromGallery(type) },
        { text: 'Cancel', style: 'cancel' }
      ]
    );
  };

  const capturePhoto = async (type: 'before' | 'after') => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission Denied', 'Camera access is required to take photos.');
      return;
    }

    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.7,
    });

    if (!result.canceled && result.assets && result.assets[0].uri) {
      if (type === 'before') {
        setBeforeImage(result.assets[0].uri);
      } else {
        setAfterImage(result.assets[0].uri);
      }
    }
  };

  const selectFromGallery = async (type: 'before' | 'after') => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission Denied', 'Gallery access is required to choose photos.');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.7,
    });

    if (!result.canceled && result.assets && result.assets[0].uri) {
      if (type === 'before') {
        setBeforeImage(result.assets[0].uri);
      } else {
        setAfterImage(result.assets[0].uri);
      }
    }
  };

  // Submit new Fuguai tag (Create Abnormality - Before state)
  const handleCreateTag = async () => {
    if (!theme.trim()) {
      Alert.alert('Validation Error', 'Please enter a description/theme.');
      return;
    }
    if (!beforeImage) {
      Alert.alert('Validation Error', 'You must capture/upload the Rectified (Before) image first.');
      return;
    }

    setSubmitting(true);
    try {
      await apiService.createFuguaiTag(departmentId, theme, beforeImage, tagColor);
      // Clean form state
      setTheme('');
      setTagColor('WHITE');
      setBeforeImage(null);
      setAfterImage(null);
      setIsAdding(false);
      // Refresh list
      fetchTags();
      Alert.alert('Success', 'Abnormality logged successfully!');
    } catch (error) {
      Alert.alert('Error', 'Failed to log abnormality.');
    } finally {
      setSubmitting(false);
    }
  };

  // Submit rectification (Update Abnormality - After state)
  const handleRectifyTag = async () => {
    if (!afterImage) {
      Alert.alert('Validation Error', 'Please capture/upload the Identified (After) image.');
      return;
    }

    setSubmitting(true);
    try {
      await apiService.updateFuguaiTag(selectedTag.id, afterImage);
      setIsRectifying(false);
      setSelectedTag(null);
      setAfterImage(null);
      fetchTags();
      Alert.alert('Success', 'Abnormality marked as Identified (Rectified) successfully!');
    } catch (error) {
      Alert.alert('Error', 'Failed to update abnormality tag.');
    } finally {
      setSubmitting(false);
    }
  };

  const cleanMediaUrl = (url: string) => {
    if (!url) return '';
    // Django REST Framework returns absolute URLs. If it's a relative path, prefix it with the base url.
    if (url.startsWith('http://') || url.startsWith('https://')) {
      // In localtunnel scenarios, we want to replace the host with our dynamic localtunnel URL if necessary
      const relativePath = url.replace(/^(https?:\/\/[^\/]+)/, '');
      const cleanBase = activeBaseUrl.replace(/\/api$/, '');
      return `${cleanBase}${relativePath}`;
    }
    const cleanBase = activeBaseUrl.replace(/\/api$/, '');
    return `${cleanBase}${url}`;
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
            <ThemedText style={styles.headerTitle} type="title">Fuguai Register</ThemedText>
            <ThemedText style={styles.headerSub} type="small">{departmentName}</ThemedText>
          </ThemedView>
        </ThemedView>

        {loading ? (
          <ThemedView style={styles.centerContainer}>
            <ActivityIndicator size="large" color="#002855" />
          </ThemedView>
        ) : (
          <ScrollView contentContainerStyle={styles.scrollContent}>
            {/* Form Section to log new Abnormality */}
            {isAdding ? (
              <ThemedView style={styles.card}>
                <ThemedText style={styles.cardTitle} type="defaultSemiBold">Log New Abnormality</ThemedText>
                
                 <ThemedText style={styles.label} type="defaultSemiBold">Description / Theme</ThemedText>
                <TextInput
                  style={styles.input}
                  placeholder="e.g. Oil leakage in Motor-2"
                  value={theme}
                  onChangeText={setTheme}
                />

                <ThemedText style={styles.label} type="defaultSemiBold">Tag Type / Color</ThemedText>
                <ThemedView style={styles.tagColorContainer}>
                  <Pressable
                    style={[
                      styles.colorTab,
                      tagColor === 'WHITE' && styles.colorTabWhiteSelected,
                    ]}
                    onPress={() => setTagColor('WHITE')}
                  >
                    <ThemedText style={[styles.colorTabText, tagColor === 'WHITE' && styles.colorTabTextWhiteActive]}>⚪ White Tag (Self-Rectify)</ThemedText>
                  </Pressable>

                  <Pressable
                    style={[
                      styles.colorTab,
                      tagColor === 'RED' && styles.colorTabRedSelected,
                    ]}
                    onPress={() => setTagColor('RED')}
                  >
                    <ThemedText style={[styles.colorTabText, tagColor === 'RED' && styles.colorTabTextRedActive]}>🔴 Red Tag (Maintenance)</ThemedText>
                  </Pressable>
                </ThemedView>

                <ThemedText style={styles.label} type="defaultSemiBold">Rectified (Before Part)</ThemedText>
                <Pressable style={styles.photoUploadBtn} onPress={() => handleImagePick('before')}>
                  {beforeImage ? (
                    <Image source={{ uri: beforeImage }} style={styles.photoPreview} />
                  ) : (
                    <ThemedText style={styles.photoUploadText} type="small">📸 Click / Upload Before Image</ThemedText>
                  )}
                </Pressable>

                <ThemedText style={styles.label} type="defaultSemiBold">Identified (After Part)</ThemedText>
                <Pressable
                  style={[styles.photoUploadBtn, !beforeImage && styles.photoUploadBtnDisabled]}
                  onPress={() => handleImagePick('after')}
                  disabled={!beforeImage}
                >
                  {afterImage ? (
                    <Image source={{ uri: afterImage }} style={styles.photoPreview} />
                  ) : (
                    <ThemedView style={styles.lockInfoContainer}>
                      {!beforeImage && <ThemedText style={styles.lockText}>🔒 </ThemedText>}
                      <ThemedText 
                        style={[styles.photoUploadText, !beforeImage && styles.photoUploadTextDisabled]} 
                        type="small"
                      >
                        {beforeImage ? '📸 Click / Upload After Image' : 'Upload Before Image First'}
                      </ThemedText>
                    </ThemedView>
                  )}
                </Pressable>

                <ThemedView style={styles.formActions}>
                  <Pressable style={[styles.actionBtn, styles.cancelBtn]} onPress={() => { setIsAdding(false); setTagColor('WHITE'); }}>
                    <ThemedText style={styles.cancelBtnText} type="defaultSemiBold">Cancel</ThemedText>
                  </Pressable>
                  <Pressable 
                    style={[styles.actionBtn, styles.saveBtn, submitting && styles.saveBtnDisabled]} 
                    onPress={handleCreateTag}
                    disabled={submitting}
                  >
                    {submitting ? (
                      <ActivityIndicator color="#fff" size="small" />
                    ) : (
                      <ThemedText style={styles.saveBtnText} type="defaultSemiBold">Submit Tag</ThemedText>
                    )}
                  </Pressable>
                </ThemedView>
              </ThemedView>
            ) : isRectifying && selectedTag ? (
              <ThemedView style={styles.card}>
                <ThemedText style={styles.cardTitle} type="defaultSemiBold">Rectify Abnormality #{selectedTag.id}</ThemedText>
                <ThemedText style={styles.rectifyTheme} type="default">{selectedTag.theme}</ThemedText>

                <ThemedView style={styles.beforeAfterDisplay}>
                  <View style={styles.halfWidth}>
                    <ThemedText style={styles.subLabel} type="small">Before (Rectified)</ThemedText>
                    {selectedTag.before_image && (
                      <Image source={{ uri: cleanMediaUrl(selectedTag.before_image) }} style={styles.miniPreview} />
                    )}
                  </View>
                  
                  <View style={styles.halfWidth}>
                    <ThemedText style={styles.subLabel} type="small">After (Identified)</ThemedText>
                    <Pressable style={styles.photoUploadBtnMini} onPress={() => handleImagePick('after')}>
                      {afterImage ? (
                        <Image source={{ uri: afterImage }} style={styles.photoPreview} />
                      ) : (
                        <ThemedText style={styles.photoUploadText} type="small">📸 Capture After Image</ThemedText>
                      )}
                    </Pressable>
                  </View>
                </ThemedView>

                <ThemedView style={styles.formActions}>
                  <Pressable 
                    style={[styles.actionBtn, styles.cancelBtn]} 
                    onPress={() => { setIsRectifying(false); setSelectedTag(null); }}
                  >
                    <ThemedText style={styles.cancelBtnText} type="defaultSemiBold">Cancel</ThemedText>
                  </Pressable>
                  <Pressable 
                    style={[styles.actionBtn, styles.saveBtn, submitting && styles.saveBtnDisabled]} 
                    onPress={handleRectifyTag}
                    disabled={submitting}
                  >
                    {submitting ? (
                      <ActivityIndicator color="#fff" size="small" />
                    ) : (
                      <ThemedText style={styles.saveBtnText} type="defaultSemiBold">Save Resolution</ThemedText>
                    )}
                  </Pressable>
                </ThemedView>
              </ThemedView>
            ) : (
              <Pressable style={styles.addBtn} onPress={() => setIsAdding(true)}>
                <ThemedText style={styles.addBtnText} type="defaultSemiBold">+ Log Abnormality (Fuguai)</ThemedText>
              </Pressable>
            )}

            {/* List of abnormalities */}
            <ThemedText style={styles.listHeader} type="defaultSemiBold">Abnormalities Logged</ThemedText>
            {tags.length === 0 ? (
              <ThemedView style={styles.emptyCard}>
                <ThemedText style={styles.emptyText} type="default">No abnormalities registered yet.</ThemedText>
              </ThemedView>
            ) : (
              tags.map((tag) => (
                <ThemedView key={tag.id} style={styles.tagCard}>
                  <ThemedView style={styles.tagCardHeader}>
                    <ThemedView style={{ flexDirection: 'row', gap: 6, alignItems: 'center', backgroundColor: 'transparent' }}>
                      <ThemedText style={styles.tagId} type="defaultSemiBold">TAG #{tag.id}</ThemedText>
                      <ThemedView style={[styles.tagColorPill, tag.tag_color === 'RED' ? styles.tagRedPill : styles.tagWhitePill]}>
                        <ThemedText style={tag.tag_color === 'RED' ? styles.tagRedText : styles.tagWhiteText}>
                          {tag.tag_color === 'RED' ? '🔴 RED' : '⚪ WHITE'}
                        </ThemedText>
                      </ThemedView>
                    </ThemedView>
                    {tag.after_image ? (
                      <ThemedView style={[styles.statusBadge, styles.statusSolved]}>
                        <ThemedText style={styles.statusSolvedText}>Closed (Identified)</ThemedText>
                      </ThemedView>
                    ) : (
                      <ThemedView style={[styles.statusBadge, styles.statusOpen]}>
                        <ThemedText style={styles.statusOpenText}>Open (Rectified)</ThemedText>
                      </ThemedView>
                    )}
                  </ThemedView>

                  <ThemedText style={styles.tagTheme}>{tag.theme}</ThemedText>
                  
                  <ThemedView style={styles.tagImages}>
                    <View style={styles.imageCol}>
                      <ThemedText style={styles.imageLabel} type="small">Before Part (Rectified)</ThemedText>
                      {tag.before_image ? (
                        <Image source={{ uri: cleanMediaUrl(tag.before_image) }} style={styles.gridPreview} />
                      ) : (
                        <ThemedText style={styles.noPhoto} type="small">No Photo</ThemedText>
                      )}
                    </View>

                    <View style={styles.imageCol}>
                      <ThemedText style={styles.imageLabel} type="small">After Part (Identified)</ThemedText>
                      {tag.after_image ? (
                        <Image source={{ uri: cleanMediaUrl(tag.after_image) }} style={styles.gridPreview} />
                      ) : (
                        <ThemedText style={styles.noPhoto} type="small">No Photo</ThemedText>
                      )}
                    </View>
                  </ThemedView>

                  {/* If tag is open, show Action to close it */}
                  {!tag.after_image && (
                    <Pressable 
                      style={styles.rectifyActionBtn} 
                      onPress={() => {
                        setSelectedTag(tag);
                        setIsRectifying(true);
                        setIsAdding(false);
                      }}
                    >
                      <ThemedText style={styles.rectifyActionText} type="defaultSemiBold">🛠️ Upload After Image (Identify)</ThemedText>
                    </Pressable>
                  )}
                  
                  <ThemedText style={styles.tagFooter} type="small">
                    Logged: {new Date(tag.created_at).toLocaleDateString()} by {tag.created_by_details?.first_name || tag.created_by_details?.username || 'Staff'}
                  </ThemedText>
                </ThemedView>
              ))
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
  card: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: Spacing.four,
    borderWidth: 1,
    borderColor: '#dee2e6',
    marginBottom: Spacing.four,
  },
  cardTitle: {
    fontSize: 16,
    color: '#002855',
    marginBottom: Spacing.three,
  },
  label: {
    fontSize: 13,
    color: '#495057',
    marginBottom: Spacing.one,
    marginTop: Spacing.two,
  },
  subLabel: {
    fontSize: 12,
    color: '#6c757d',
    marginBottom: Spacing.one,
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
    marginBottom: Spacing.two,
  },
  photoUploadBtn: {
    height: 120,
    borderWidth: 1,
    borderColor: '#ced4da',
    borderStyle: 'dashed',
    borderRadius: 6,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f8f9fa',
    overflow: 'hidden',
  },
  photoUploadBtnDisabled: {
    backgroundColor: '#e9ecef',
    borderColor: '#dee2e6',
  },
  photoUploadText: {
    color: '#0d6efd',
  },
  photoUploadTextDisabled: {
    color: '#adb5bd',
  },
  lockInfoContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'transparent',
  },
  lockText: {
    fontSize: 12,
  },
  photoPreview: {
    width: '100%',
    height: '100%',
    resizeMode: 'cover',
  },
  formActions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: Spacing.two,
    marginTop: Spacing.four,
    backgroundColor: 'transparent',
  },
  actionBtn: {
    height: 38,
    paddingHorizontal: Spacing.four,
    borderRadius: 5,
    justifyContent: 'center',
    alignItems: 'center',
  },
  cancelBtn: {
    backgroundColor: '#e2e3e5',
    borderWidth: 1,
    borderColor: '#ced4da',
  },
  cancelBtnText: {
    color: '#495057',
  },
  saveBtn: {
    backgroundColor: '#002855',
    minWidth: 100,
  },
  saveBtnDisabled: {
    backgroundColor: '#6c757d',
  },
  saveBtnText: {
    color: '#fff',
  },
  addBtn: {
    height: 46,
    backgroundColor: '#002855',
    borderRadius: 6,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: Spacing.four,
  },
  addBtnText: {
    color: '#fff',
    fontSize: 15,
  },
  listHeader: {
    fontSize: 15,
    color: '#495057',
    marginBottom: Spacing.three,
  },
  emptyCard: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: Spacing.five,
    borderWidth: 1,
    borderColor: '#dee2e6',
    alignItems: 'center',
  },
  emptyText: {
    color: '#6c757d',
    textAlign: 'center',
  },
  tagCard: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: Spacing.four,
    borderWidth: 1,
    borderColor: '#dee2e6',
    marginBottom: Spacing.three,
  },
  tagCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: 'transparent',
    marginBottom: Spacing.two,
  },
  tagId: {
    fontSize: 14,
    color: '#002855',
  },
  statusBadge: {
    paddingHorizontal: Spacing.two,
    paddingVertical: 3,
    borderRadius: 4,
  },
  statusSolved: {
    backgroundColor: '#d1e7dd',
  },
  statusSolvedText: {
    fontSize: 10,
    color: '#0f5132',
    fontWeight: 'bold',
  },
  statusOpen: {
    backgroundColor: '#f8d7da',
  },
  statusOpenText: {
    fontSize: 10,
    color: '#842029',
    fontWeight: 'bold',
  },
  tagTheme: {
    fontSize: 14,
    color: '#212529',
    marginBottom: Spacing.three,
  },
  tagImages: {
    flexDirection: 'row',
    gap: Spacing.two,
    backgroundColor: 'transparent',
    marginBottom: Spacing.three,
  },
  imageCol: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  imageLabel: {
    fontSize: 11,
    color: '#6c757d',
    marginBottom: 4,
  },
  gridPreview: {
    width: '100%',
    height: 100,
    borderRadius: 4,
    resizeMode: 'cover',
  },
  noPhoto: {
    height: 100,
    borderWidth: 1,
    borderColor: '#dee2e6',
    borderRadius: 4,
    backgroundColor: '#f8f9fa',
    color: '#adb5bd',
    textAlign: 'center',
    textAlignVertical: 'center',
    lineHeight: 100,
  },
  rectifyActionBtn: {
    height: 36,
    backgroundColor: '#f0f7ff',
    borderWidth: 1,
    borderColor: '#b6d4fe',
    borderRadius: 5,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: Spacing.two,
  },
  rectifyActionText: {
    color: '#0d6efd',
    fontSize: 12,
  },
  tagFooter: {
    color: '#adb5bd',
    fontSize: 10,
    marginTop: Spacing.one,
  },
  rectifyTheme: {
    color: '#495057',
    fontSize: 14,
    marginBottom: Spacing.three,
  },
  beforeAfterDisplay: {
    flexDirection: 'row',
    gap: Spacing.three,
    backgroundColor: 'transparent',
    marginBottom: Spacing.four,
  },
  halfWidth: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  miniPreview: {
    width: '100%',
    height: 100,
    borderRadius: 6,
    resizeMode: 'cover',
  },
  photoUploadBtnMini: {
    height: 100,
    borderWidth: 1,
    borderColor: '#ced4da',
    borderStyle: 'dashed',
    borderRadius: 6,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f8f9fa',
    overflow: 'hidden',
  },
  tagColorContainer: {
    flexDirection: 'row',
    gap: Spacing.two,
    backgroundColor: 'transparent',
    marginBottom: Spacing.three,
  },
  colorTab: {
    flex: 1,
    height: 40,
    borderWidth: 1,
    borderColor: '#ced4da',
    borderRadius: 5,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#fff',
  },
  colorTabText: {
    fontSize: 12,
    color: '#495057',
  },
  colorTabWhiteSelected: {
    borderColor: '#adb5bd',
    backgroundColor: '#f8f9fa',
    borderWidth: 2,
  },
  colorTabTextWhiteActive: {
    fontWeight: 'bold',
    color: '#212529',
  },
  colorTabRedSelected: {
    borderColor: '#dc3545',
    backgroundColor: '#f8d7da',
    borderWidth: 2,
  },
  colorTabTextRedActive: {
    fontWeight: 'bold',
    color: '#842029',
  },
  tagColorPill: {
    paddingHorizontal: 6,
    paddingVertical: 1,
    borderRadius: 3,
  },
  tagWhitePill: {
    backgroundColor: '#f8f9fa',
    borderWidth: 1,
    borderColor: '#ced4da',
  },
  tagRedPill: {
    backgroundColor: '#f8d7da',
    borderWidth: 1,
    borderColor: '#f5c2c7',
  },
  tagWhiteText: {
    fontSize: 9,
    fontWeight: 'bold',
    color: '#212529',
  },
  tagRedText: {
    fontSize: 9,
    fontWeight: 'bold',
    color: '#842029',
  },
});
