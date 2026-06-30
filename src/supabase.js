import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.https//dowinoownpxfmowxltuw.supabase.co;
const supabaseAnonKey = import.meta.env.sb_publishable_w3hs3ZGJjH_QKleb7cmQCw_OnI5vbWS;

export const supabase = createClient(
  supabaseUrl,
  supabaseAnonKey
);