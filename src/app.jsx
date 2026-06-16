import { useEffect, useState } from 'react'
import { supabase } from './supabase' // Imports the client from step 2

function App() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function fetchData() {
      try {
        // 💡 CHANGE 'todos' to your actual Supabase table name!
        const { data: tableData, error: fetchError } = await supabase
          .from('todos') 
          .select('*')
          .limit(10)

        if (fetchError) throw fetchError
        setData(tableData)
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  return (
    <div style={{ padding: '40px', fontFamily: 'system-ui, sans-serif', maxWidth: '600px', margin: '0 auto' }}>
      <h1>⚡ Vite + Supabase Setup</h1>
      <p>Testing your database integration below:</p>
      <hr style={{ margin: '20px 0', borderColor: '#eaeaea' }} />

      {/* 1. Loading State */}
      {loading && <p style={{ color: '#666' }}>Connecting to Supabase...</p>}

      {/* 2. Error State (Expected if your table name doesn't match or RLS rules block it) */}
      {error && (
        <div style={{ backgroundColor: '#fee2e2', color: '#991b1b', padding: '15px', borderRadius: '8px' }}>
          <p style={{ margin: 0, fontWeight: 'bold' }}>Database Notice:</p>
          <p style={{ margin: '5px 0 0 0', fontSize: '14px' }}>{error}</p>
          <p style={{ margin: '10px 0 0 0', fontSize: '12px', color: '#b91c1c' }}>
            *Make sure to change <code>.from('todos')</code> in App.jsx to match an actual table in your Supabase Dashboard.
          </p>
        </div>
      )}

      {/* 3. Success State */}
      {!loading && !error && (
        <div style={{ backgroundColor: '#f0fdf4', color: '#166534', padding: '15px', borderRadius: '8px' }}>
          <p style={{ margin: 0, fontWeight: 'bold' }}>✅ Connected Successfully!</p>
          <p style={{ fontSize: '14px' }}>Data received from your database:</p>
          <pre style={{ backgroundColor: '#fff', padding: '10px', borderRadius: '4px', border: '1px solid #dcfce7', overflowX: 'auto' }}>
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

export default App