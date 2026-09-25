export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  conversationId: string;
  model?: string;
  timestamp?: string;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}

export interface ModelId {
  id: string;
  name: string;
  provider: string;
}

export interface DocumentItem {
  id: string;
  filename: string;
  status: string;
  chunks: number;
  createdAt: string;
}
