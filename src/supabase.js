import { createClient } from "@supabase/supabase-js";

const supabaseUrl = "https://dowinoownpxfmowxltuw.supabase.co";
const supabaseAnonKey = "sb_publishable_w3hs3ZGJjH_QKleb7cmQCw_OnI5vbWS";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);