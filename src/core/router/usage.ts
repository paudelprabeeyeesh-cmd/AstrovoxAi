type UsageRecord = {
  provider: string;
  model: string;
  promptTokens?: number;
  completionTokens?: number;
  totalTokens?: number;
  costUSD?: number;
  timestamp: string;
  meta?: Record<string, any>;
};

const records: UsageRecord[] = [];

export const usage = {
  record(r: Omit<UsageRecord, 'timestamp'>) {
    const rec: UsageRecord = { ...r, timestamp: new Date().toISOString() };
    records.push(rec);
    return rec;
  },
  list(since?: string) {
    if (!since) return records.slice();
    return records.filter(r => r.timestamp > since);
  },
  clear() {
    records.length = 0;
  }
};
