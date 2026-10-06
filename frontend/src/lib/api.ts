const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

function parseErrorMessage(error: any, fallbackStatus: number): string {
  let errorMessage = `HTTP ${fallbackStatus}`;
  if (error && error.detail) {
    if (typeof error.detail === 'string') {
      errorMessage = error.detail;
    } else if (Array.isArray(error.detail)) {
      errorMessage = error.detail
        .map((item: any) => {
          const loc = Array.isArray(item.loc) ? item.loc.join('.') : item.loc;
          return loc ? `${loc}: ${item.msg || JSON.stringify(item)}` : (item.msg || JSON.stringify(item));
        })
        .join('; ');
    } else {
      errorMessage = JSON.stringify(error.detail);
    }
  }
  return errorMessage;
}

class ApiClient {
  private getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('access_token');
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      if (response.status === 401) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
      }
      throw new Error(parseErrorMessage(error, response.status));
    }

    return response.json();
  }

  async get<T>(path: string): Promise<T> {
    return this.request<T>(path);
  }

  async post<T>(path: string, body?: any): Promise<T> {
    return this.request<T>(path, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async put<T>(path: string, body?: any): Promise<T> {
    return this.request<T>(path, {
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async delete<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: 'DELETE' });
  }

  async uploadFile<T>(path: string, file: File, additionalFields?: Record<string, string>): Promise<T> {
    const token = this.getToken();
    const formData = new FormData();
    formData.append('file', file);
    if (additionalFields) {
      Object.entries(additionalFields).forEach(([key, value]) => {
        formData.append(key, value);
      });
    }

    const response = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(parseErrorMessage(error, response.status));
    }

    return response.json();
  }
}

export const api = new ApiClient();
export default api;
