import { createClient } from '@supabase/supabase-js'

// Pull the credentials safely from Vite's environment handler
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

// A quick safety check during development to prevent silent failures
if (!supabaseUrl || !supabaseAnonKey) {
  console.error(
    '⚠️ Supabase integration failed: Environment variables are missing.\n' +
    'Make sure your .env file is in the root directory and keys start with VITE_'
  );
}

// Initialize and export the single client instance
export const supabase = createClient(supabaseUrl, supabaseAnonKey)