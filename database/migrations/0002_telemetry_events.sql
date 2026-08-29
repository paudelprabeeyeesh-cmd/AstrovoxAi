-- Create telemetry_events table for tracking user events
CREATE TABLE IF NOT EXISTS public.telemetry_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users ON DELETE CASCADE NOT NULL,
    event_name TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable Row Level Security
ALTER TABLE public.telemetry_events ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Users can only see their own telemetry events
CREATE POLICY "Users can view their own telemetry events"
    ON public.telemetry_events
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own telemetry events"
    ON public.telemetry_events
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_telemetry_events_user_id ON public.telemetry_events(user_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_events_timestamp ON public.telemetry_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_events_category ON public.telemetry_events(category);
CREATE INDEX IF NOT EXISTS idx_telemetry_events_event_name ON public.telemetry_events(event_name);
CREATE INDEX IF NOT EXISTS idx_telemetry_events_user_timestamp ON public.telemetry_events(user_id, timestamp DESC);
