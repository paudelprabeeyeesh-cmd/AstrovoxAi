export default function TerminalConsole({ userEmail, totalItems, history = [], setHistory }) {
  const handleClear = () => {
    setHistory?.([]);
  };

  return (
    <div style={{ padding: 16, backgroundColor: 'rgba(4,8,20,0.75)', borderRadius: 12, border: '1px solid #1e293b' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h3 style={{ margin: 0, color: '#67e8f9', fontSize: 14 }}>Terminal Console</h3>
        <button onClick={handleClear} style={{ background: 'transparent', color: '#94a3b8', border: '1px solid #1e293b', borderRadius: 999, cursor: 'pointer', padding: '4px 10px' }}>
          Clear
        </button>
      </div>
      <div style={{ fontSize: 12, color: '#cbd5e1', lineHeight: 1.5, maxHeight: 220, overflowY: 'auto' }}>
        {history.length === 0 ? (
          <div style={{ color: '#64748b' }}>No terminal activity recorded.</div>
        ) : (
          history.map((entry, index) => <div key={`${entry}-${index}`} style={{ marginBottom: 6 }}>{entry}</div>)
        )}
      </div>
      <div style={{ marginTop: 12, fontSize: 11, color: '#64748b' }}>
        User: {userEmail || 'unknown'} · Items: {totalItems}
      </div>
    </div>
  );
}