// Frontend Platform - Group 4: Sync primitives for offline-first data
const SyncPrimitives = {
  _operations: new Map(),
  _conflicts: [],
  _lastSync: null,
  _syncInterval: null,

  async merge(localState, remoteState, conflictStrategy = 'remote-wins') {
    if (!localState || !remoteState) return remoteState || localState;

    const merged = { ...remoteState };
    const conflicts = [];

    for (const key of Object.keys(localState)) {
      if (key in remoteState) {
        if (localState[key] !== remoteState[key]) {
          conflicts.push({
            key,
            local: localState[key],
            remote: remoteState[key],
          });

          if (conflictStrategy === 'local-wins') {
            merged[key] = localState[key];
          }
        }
      } else {
        merged[key] = localState[key];
      }
    }

    if (conflicts.length > 0) {
      this._conflicts.push({
        timestamp: Date.now(),
        conflicts,
        strategy: conflictStrategy,
      });
    }

    return merged;
  },

  async applyOperation(operation) {
    const opId = operation.id || crypto.randomUUID();
    const op = {
      id: opId,
      type: operation.type,
      payload: operation.payload,
      timestamp: Date.now(),
      status: 'pending',
      retries: 0,
    };

    this._operations.set(opId, op);

    try {
      const response = await fetch('/api/sync/operations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(op),
      });

      if (response.ok) {
        op.status = 'applied';
        this._operations.set(opId, op);
        return op;
      }

      throw new Error(`Sync failed: ${response.status}`);
    } catch (err) {
      op.status = 'failed';
      op.error = err.message;
      this._operations.set(opId, op);
      throw err;
    }
  },

  async pull() {
    try {
      const response = await fetch('/api/sync/state');
      if (!response.ok) throw new Error('Pull failed');
      const remoteState = await response.json();
      this._lastSync = Date.now();
      return remoteState;
    } catch (err) {
      console.error('Sync pull failed:', err);
      throw err;
    }
  },

  async push(localState) {
    try {
      const response = await fetch('/api/sync/state', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(localState),
      });

      if (!response.ok) throw new Error('Push failed');
      this._lastSync = Date.now();
      return await response.json();
    } catch (err) {
      console.error('Sync push failed:', err);
      throw err;
    }
  },

  getConflicts() {
    return [...this._conflicts];
  },

  clearConflicts() {
    this._conflicts = [];
  },

  getLastSync() {
    return this._lastSync;
  },

  startAutoSync(intervalMs = 30000) {
    if (this._syncInterval) clearInterval(this._syncInterval);
    this._syncInterval = setInterval(() => {
      if (navigator.onLine) {
        this.pull().catch(() => {});
      }
    }, intervalMs);
  },

  stopAutoSync() {
    if (this._syncInterval) {
      clearInterval(this._syncInterval);
      this._syncInterval = null;
    }
  },
};

window.SyncPrimitives = SyncPrimitives;
