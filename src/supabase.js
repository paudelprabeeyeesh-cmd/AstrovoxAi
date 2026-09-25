import { createClient } from "@supabase/supabase-js";

<<<<<<< HEAD
const supabaseUrl = "https://dowinoownpxfmowxltuw.supabase.co";
const supabaseAnonKey = "sb_publishable_w3hs3ZGJjH_QKleb7cmQCw_OnI5vbWS";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
=======
const projectId = import.meta.env.VITE_SUPABASE_PROJECT_ID
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || (projectId ? `https://${projectId}.supabase.co` : '')
// Supabase projects created after 2025 can use publishable keys. Existing
// anon-key projects continue to work without any configuration change.
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    'Supabase is not configured. Set VITE_SUPABASE_URL (or VITE_SUPABASE_PROJECT_ID) and VITE_SUPABASE_ANON_KEY (or VITE_SUPABASE_PUBLISHABLE_KEY).'
  )
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true
  }
})
>>>>>>> d06d6f13ebb90117a65b970c3333bcc1c6546838
