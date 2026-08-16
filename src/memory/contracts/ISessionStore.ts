export interface SessionRecord {
  id: string;
  sessionId: string;
  text: string;
  metadata?: Record<string, any>;
  createdAt: string;
}

export interface ISessionStore {
  init(): Promise<void>;
  add(record: SessionRecord): Promise<void>;
  list(sessionId: string, opts?: { limit?: number; since?: string }): Promise<SessionRecord[]>;
  clear(sessionId: string): Promise<void>;
  close(): Promise<void>;
}
