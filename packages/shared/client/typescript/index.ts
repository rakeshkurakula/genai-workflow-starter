import {
  ApiResponse,
  ApiError,
  ClientConfig,
  ChatMessage,
  Conversation,
  Tool,
  PaginationParams,
  PaginatedResponse
} from '../../types';

/**
 * TypeScript Client SDK for GenAI Workflow API
 */
export class GenAIClient {
  private baseUrl: string;
  private apiKey?: string;
  private timeout: number;
  private headers: Record<string, string>;

  constructor(config: ClientConfig = {}) {
    this.baseUrl = config.baseUrl || 'http://localhost:8000/api';
    this.apiKey = config.apiKey;
    this.timeout = config.timeout || 30000;
    this.headers = {
      'Content-Type': 'application/json',
      ...config.headers
    };

    if (this.apiKey) {
      this.headers['Authorization'] = `Bearer ${this.apiKey}`;
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`;
    const config: RequestInit = {
      ...options,
      headers: {
        ...this.headers,
        ...(options.headers || {})
      }
    };

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);
      
      const response = await fetch(url, {
        ...config,
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new ApiError(
          data.error?.message || 'API request failed',
          data.error?.code || 'API_ERROR',
          response.status,
          data.error?.details
        );
      }
      
      return data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      
      throw new ApiError(
        error instanceof Error ? error.message : 'Unknown error',
        'NETWORK_ERROR'
      );
    }
  }

  // Chat API methods
  async getConversations(params?: PaginationParams): Promise<PaginatedResponse<Conversation>> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    if (params?.offset) searchParams.set('offset', params.offset.toString());
    
    const query = searchParams.toString();
    return this.request<Conversation[]>(`/conversations${query ? `?${query}` : ''}`);
  }

  async getConversation(id: string): Promise<ApiResponse<Conversation>> {
    return this.request<Conversation>(`/conversations/${id}`);
  }

  async createConversation(data: Partial<Conversation>): Promise<ApiResponse<Conversation>> {
    return this.request<Conversation>('/conversations', {
      method: 'POST',
      body: JSON.stringify(data)
    });
  }

  async updateConversation(id: string, data: Partial<Conversation>): Promise<ApiResponse<Conversation>> {
    return this.request<Conversation>(`/conversations/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }

  async deleteConversation(id: string): Promise<ApiResponse<void>> {
    return this.request<void>(`/conversations/${id}`, {
      method: 'DELETE'
    });
  }

  async sendMessage(
    conversationId: string,
    message: Partial<ChatMessage>
  ): Promise<ApiResponse<ChatMessage>> {
    return this.request<ChatMessage>(`/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify(message)
    });
  }

  // Tools API methods
  async getTools(params?: PaginationParams): Promise<PaginatedResponse<Tool>> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    if (params?.offset) searchParams.set('offset', params.offset.toString());
    
    const query = searchParams.toString();
    return this.request<Tool[]>(`/tools${query ? `?${query}` : ''}`);
  }

  async getTool(id: string): Promise<ApiResponse<Tool>> {
    return this.request<Tool>(`/tools/${id}`);
  }

  async executeTool(
    id: string,
    parameters: Record<string, any>
  ): Promise<ApiResponse<any>> {
    return this.request<any>(`/tools/${id}/execute`, {
      method: 'POST',
      body: JSON.stringify({ parameters })
    });
  }

  // Health check
  async health(): Promise<ApiResponse<{ status: string; timestamp: string }>> {
    return this.request<{ status: string; timestamp: string }>('/health');
  }
}

// Export default instance
export default GenAIClient;

// Export types for convenience
export * from '../../types';
