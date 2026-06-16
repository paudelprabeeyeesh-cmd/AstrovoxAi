import { createClient } from '@supabase/supabase-js'

// Pull secrets securely from Vite's environment handler
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

// A helpful developer alert to catch missing keys early
if (!supabaseUrl || !supabaseAnonKey) {
  console.error(
    '⚠️ Supabase Connection Error: Environment variables are missing.\n' +
    'Verify that your .env file is in the root directory and keys start with VITE_'
  )
}

// Export the client instance
export const supabase = createClient(supabaseUrl, supabaseAnonKey)