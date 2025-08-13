// TypeScript types generated from JSON schemas

// Tool Types
export interface Tool {
  id: string;
  name: string;
  description: string;
  version: string;
  parameters: {
    type: 'object';
    properties: Record<string, any>;
    required?: string[];
  };
  returns: {
    type: string;
    [key: string]: any;
  };
  category?: 'search' | 'analysis' | 'generation' | 'transformation' | 'utility';
  tags?: string[];
}

// Chat Types
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string; // ISO 8601 date-time
  metadata?: {
    model?: string;
    usage?: {
      prompt_tokens?: number;
      completion_tokens?: number;
      total_tokens?: number;
    };
  };
}

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  created_at: string; // ISO 8601 date-time
  updated_at: string; // ISO 8601 date-time
  settings?: {
    model?: string;
    temperature?: number; // 0-2
    max_tokens?: number; // min 1
  };
}

// API Types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
  metadata?: {
    timestamp: string;
    request_id: string;
    version: string;
  };
}

export interface ApiRequest {
  headers?: Record<string, string>;
  params?: Record<string, any>;
  body?: any;
}

// Client SDK Types
export interface ClientConfig {
  baseUrl?: string;
  apiKey?: string;
  timeout?: number;
  headers?: Record<string, string>;
}

export interface PaginationParams {
  page?: number;
  limit?: number;
  offset?: number;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination?: {
    page: number;
    limit: number;
    total: number;
    hasNext: boolean;
    hasPrevious: boolean;
  };
}

// Error Types
export class ApiError extends Error {
  constructor(
    message: string,
    public code: string,
    public status?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export class ValidationError extends ApiError {
  constructor(message: string, details?: any) {
    super(message, 'VALIDATION_ERROR', 400, details);
    this.name = 'ValidationError';
  }
}

export class NotFoundError extends ApiError {
  constructor(resource: string) {
    super(`${resource} not found`, 'NOT_FOUND', 404);
    this.name = 'NotFoundError';
  }
}

// Type Guards
export function isChatMessage(obj: any): obj is ChatMessage {
  return obj && 
    typeof obj.id === 'string' &&
    ['user', 'assistant', 'system'].includes(obj.role) &&
    typeof obj.content === 'string' &&
    typeof obj.timestamp === 'string';
}

export function isConversation(obj: any): obj is Conversation {
  return obj &&
    typeof obj.id === 'string' &&
    typeof obj.title === 'string' &&
    Array.isArray(obj.messages) &&
    typeof obj.created_at === 'string' &&
    typeof obj.updated_at === 'string';
}

export function isTool(obj: any): obj is Tool {
  return obj &&
    typeof obj.id === 'string' &&
    typeof obj.name === 'string' &&
    typeof obj.description === 'string' &&
    typeof obj.version === 'string' &&
    obj.parameters &&
    obj.returns;
}
