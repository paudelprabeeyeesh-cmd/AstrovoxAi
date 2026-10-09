BEGIN;

CREATE TABLE IF NOT EXISTS public.ai_memory (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users ON DELETE CASCADE NOT NULL,
    content TEXT NOT NULL,
    importance INTEGER DEFAULT 1,
    embedding_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.ai_memory ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own memory"
    ON public.ai_memory
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own memory"
    ON public.ai_memory
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own memory"
    ON public.ai_memory
    FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own memory"
    ON public.ai_memory
    FOR DELETE
    USING (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_ai_memory_user_id ON public.ai_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_memory_importance ON public.ai_memory(importance DESC);
CREATE INDEX IF NOT EXISTS idx_ai_memory_created_at ON public.ai_memory(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_memory_user_importance ON public.ai_memory(user_id, importance DESC);

COMMIT;
