BEGIN;

CREATE TABLE IF NOT EXISTS public.audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users ON DELETE CASCADE,
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    ip_address TEXT,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own audit logs"
    ON public.audit_logs
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service role can insert audit logs"
    ON public.audit_logs
    FOR INSERT
    WITH CHECK (true);

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON public.audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON public.audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON public.audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_action ON public.audit_logs(user_id, action, created_at DESC);

COMMIT;
