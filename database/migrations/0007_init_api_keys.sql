BEGIN;

CREATE TABLE IF NOT EXISTS public.api_keys (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users ON DELETE CASCADE NOT NULL,
    name TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    key_prefix TEXT NOT NULL,
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.api_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own API keys"
    ON public.api_keys
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own API keys"
    ON public.api_keys
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own API keys"
    ON public.api_keys
    FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own API keys"
    ON public.api_keys
    FOR DELETE
    USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON public.api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_prefix ON public.api_keys(key_prefix);
CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON public.api_keys(is_active);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_active ON public.api_keys(user_id, is_active);

COMMIT;
