import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Replace with your local machine's IP address on the network if running on physical device
// The default Django ALLOWED_HOSTS includes '172.17.18.13'
export const API_BASE_URL = 'https://subjugular-shrilly-zada.ngrok-free.dev/api';

export async function getApiBaseUrl(): Promise<string> {
  const savedBaseUrl = await AsyncStorage.getItem('api_base_url');
  return savedBaseUrl || API_BASE_URL;
}

export async function setApiBaseUrl(url: string): Promise<void> {
  if (url) {
    const cleanUrl = url.endsWith('/') ? url.slice(0, -1) : url;
    await AsyncStorage.setItem('api_base_url', cleanUrl);
  } else {
    await AsyncStorage.removeItem('api_base_url');
  }
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'Bypass-Tunnel-Reminder': 'true',
  },
  timeout: 10000,
});

// Interceptor to inject the JWT access token in the headers automatically
api.interceptors.request.use(
  async (config) => {
    try {
      const activeBaseUrl = await getApiBaseUrl();
      config.baseURL = activeBaseUrl;

      const token = await AsyncStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (e) {
      console.error('Failed to retrieve token/baseURL from storage:', e);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Endpoints wrapper
export const apiService = {
  // Auth endpoints
  async login(username, password) {
    const response = await api.post('/auth/login/', { username, password });
    if (response.data.access && response.data.refresh) {
      await AsyncStorage.setItem('access_token', response.data.access);
      await AsyncStorage.setItem('refresh_token', response.data.refresh);
    }
    return response.data;
  },

  async logout() {
    await AsyncStorage.removeItem('access_token');
    await AsyncStorage.removeItem('refresh_token');
  },

  async refreshToken() {
    try {
      const refresh = await AsyncStorage.getItem('refresh_token');
      if (!refresh) return null;
      // Use clean axios instance to prevent recursive interceptor calls
      const activeBaseUrl = await getApiBaseUrl();
      const response = await axios.post(`${activeBaseUrl}/auth/refresh/`, { refresh });
      if (response.data.access) {
        await AsyncStorage.setItem('access_token', response.data.access);
        return response.data.access;
      }
    } catch (err) {
      console.error('Failed to refresh token:', err);
    }
    return null;
  },

  async isAuthenticated() {
    const token = await AsyncStorage.getItem('access_token');
    return !!token;
  },

  async getMe() {
    const response = await api.get('/auth/me/');
    return response.data;
  },

  // Dashboard configs
  async getDashboard() {
    const response = await api.get('/dashboard/');
    return response.data;
  },

  // Checklists endpoints
  async getChecklistSchedules(departmentId) {
    const response = await api.get(`/checklist/schedules/?department_id=${departmentId}`);
    return response.data;
  },

  async getChecklistsList(departmentId, date = '') {
    let url = `/checklist/list/?department_id=${departmentId}`;
    if (date) {
      url += `&date=${date}`;
    }
    const response = await api.get(url);
    return response.data;
  },

  async getChecklistDetail(checklistId) {
    const response = await api.get(`/checklist/detail/${checklistId}/`);
    return response.data;
  },

  async initializeChecklist(departmentId, equipment, date) {
    const response = await api.post('/checklist/initialize/', {
      department_id: departmentId,
      equipment,
      date,
    });
    return response.data;
  },

  async saveChecklist(checklistId, payload) {
    const response = await api.post(`/checklist/save/${checklistId}/`, payload);
    return response.data;
  },

  // Fuguai Abnormality Register endpoints
  async getFuguaiTags(departmentId: number) {
    const response = await api.get(`/tpm/fuguai/list/?department_id=${departmentId}`);
    return response.data;
  },

  async createFuguaiTag(departmentId: number, theme: string, beforeImageUri: string | null, tagColor: 'WHITE' | 'RED' = 'WHITE') {
    const formData = new FormData();
    formData.append('department_id', departmentId.toString());
    formData.append('theme', theme);
    formData.append('tag_color', tagColor);

    if (beforeImageUri) {
      const uriParts = beforeImageUri.split('/');
      const filename = uriParts[uriParts.length - 1];
      const type = filename.toLowerCase().endsWith('.png') ? 'image/png' : 'image/jpeg';

      formData.append('before_image', {
        uri: beforeImageUri,
        name: filename,
        type: type,
      } as any);
    }

    const response = await api.post('/tpm/fuguai/create/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async updateFuguaiTag(tagId: number, afterImageUri: string | null, theme?: string) {
    const formData = new FormData();
    if (theme) {
      formData.append('theme', theme);
    }

    if (afterImageUri) {
      const uriParts = afterImageUri.split('/');
      const filename = uriParts[uriParts.length - 1];
      const type = filename.toLowerCase().endsWith('.png') ? 'image/png' : 'image/jpeg';

      formData.append('after_image', {
        uri: afterImageUri,
        name: filename,
        type: type,
      } as any);
    }

    const response = await api.post(`/tpm/fuguai/update/${tagId}/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};

export default api;

