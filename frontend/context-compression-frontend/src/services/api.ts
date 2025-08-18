// Backend API type definitions
export interface CompressionRequest {
  role: 'system' | 'assistant' | 'user' | 'tool';
  section: 'BACKGROUND' | 'PLAN' | 'SUB_APP' | 'HISTORY';
  content: string;
  target_modules: string[];
  use_tf_idf: boolean;
  use_history_compression: boolean;
  max_token: number;
  
  // TF-IDF compression parameters
  tf_idf_compression_ratio: number; // TF-IDF compression retention ratio (0.1-1.0), default 0.6 means retain 60% of sentences
  
  // History compression parameters
  history_preserve_tokens: number; // Number of latest tokens to preserve in history compression, default 500
  history_compression_ratio: number; // Compression ratio for old content in history compression (0.1-1.0), default 0.3 means compress to 30%
  
  // User identifier (optional, auto-generated if not provided)
  user_id?: string;
  
  openai_api_key?: string;
  openai_base_url?: string;
}

export interface CompressionResponse {
  success: boolean;
  original_content: string;
  compressed_content: string;
  compression_ratio: number;
  token_count_original: number;
  token_count_compressed: number;
  file_path: string;
  message: string;
}

export interface FileInfo {
  name: string;
  size: number;
  modified: string;
  user_id?: string;
}

export interface UserInfo {
  user_id: string;
  user_dir: string;
  files_count: number;
  user_agent_hash: string;
}

// API service class
class ApiService {
  private baseUrl: string;

  constructor() {
    // 在生产环境中，API请求通过nginx代理，无需指定完整URL
    // 在开发环境中，使用环境变量或默认的localhost:8000
    if (import.meta.env.PROD) {
      this.baseUrl = '/api'; // 生产环境通过nginx代理
    } else {
      this.baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    }
  }

  async compressContext(data: CompressionRequest): Promise<CompressionResponse> {
    const response = await fetch(`${this.baseUrl}/compress`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMessage = errorData.detail || `HTTP error! status: ${response.status}`;
      throw new Error(errorMessage);
    }

    return response.json();
  }

  async getFiles(): Promise<{files: FileInfo[], user_id: string}> {
    const response = await fetch(`${this.baseUrl}/files`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  }

  async getFile(filename: string): Promise<{filename: string; content: string; user_id: string}> {
    const response = await fetch(`${this.baseUrl}/file/${filename}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  }

  async getUserInfo(): Promise<UserInfo> {
    const response = await fetch(`${this.baseUrl}/user-info`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  }

  async healthCheck(): Promise<{status: string; timestamp: string}> {
    const response = await fetch(`${this.baseUrl}/health`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.json();
  }
}

export const apiService = new ApiService();
