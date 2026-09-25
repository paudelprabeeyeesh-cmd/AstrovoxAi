-- Analytics persistent tables for high-value analytics features
-- Run this migration to create all analytics tables

-- 1. Enhanced analytics events with rich metadata
CREATE TABLE IF NOT EXISTS public.analytics_events_v2 (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    event_name TEXT,
    category TEXT DEFAULT 'general',
    properties JSONB DEFAULT '{}',
    session_id TEXT,
    device_type TEXT,
    browser TEXT,
    os TEXT,
    country TEXT,
    city TEXT,
    ip_address TEXT,
    referrer TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    page_url TEXT,
    duration_ms INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. User behavior events
CREATE TABLE IF NOT EXISTS public.user_behavior_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    element_id TEXT,
    element_class TEXT,
    page_url TEXT NOT NULL,
    properties JSONB DEFAULT '{}',
    time_on_page_seconds INTEGER DEFAULT 0,
    scroll_depth_percent INTEGER DEFAULT 0,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Feature adoption tracking
CREATE TABLE IF NOT EXISTS public.feature_adoption (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users ON DELETE CASCADE,
    feature_name TEXT NOT NULL,
    feature_category TEXT NOT NULL,
    first_used_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    usage_count INTEGER DEFAULT 1,
    is_adopted BOOLEAN DEFAULT false,
    adoption_date TIMESTAMP WITH TIME ZONE,
    time_to_adoption_seconds INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(user_id, feature_name)
);

-- 4. A/B tests
CREATE TABLE IF NOT EXISTS public.ab_tests (
    id BIGSERIAL PRIMARY KEY,
    test_name TEXT NOT NULL UNIQUE,
    description TEXT,
    variant_a JSONB DEFAULT '{}',
    variant_b JSONB DEFAULT '{}',
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'running', 'paused', 'completed', 'archived')),
    metric_name TEXT NOT NULL,
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    min_sample_size INTEGER DEFAULT 100,
    confidence_level REAL DEFAULT 0.95,
    created_by UUID REFERENCES auth.users ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 5. A/B test assignments
CREATE TABLE IF NOT EXISTS public.ab_test_assignments (
    id BIGSERIAL PRIMARY KEY,
    test_id BIGINT REFERENCES public.ab_tests ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users ON DELETE CASCADE NOT NULL,
    variant TEXT NOT NULL CHECK (variant IN ('A', 'B')),
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(test_id, user_id)
);

-- 6. A/B test events
CREATE TABLE IF NOT EXISTS public.ab_test_events (
    id BIGSERIAL PRIMARY KEY,
    test_id BIGINT REFERENCES public.ab_tests ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users ON DELETE CASCADE NOT NULL,
    variant TEXT NOT NULL,
    event_name TEXT NOT NULL,
    event_value NUMERIC,
    properties JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 7. Funnels
CREATE TABLE IF NOT EXISTS public.funnels (
    id BIGSERIAL PRIMARY KEY,
    funnel_name TEXT NOT NULL UNIQUE,
    description TEXT,
    steps JSONB NOT NULL,
    created_by UUID REFERENCES auth.users ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 8. Funnel events
CREATE TABLE IF NOT EXISTS public.funnel_events (
    id BIGSERIAL PRIMARY KEY,
    funnel_id BIGINT REFERENCES public.funnels ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users ON DELETE CASCADE,
    session_id TEXT,
    step_index INTEGER NOT NULL,
    step_name TEXT NOT NULL,
    entered_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    exited_at TIMESTAMP WITH TIME ZONE,
    completed BOOLEAN DEFAULT false,
    drop_off_reason TEXT,
    properties JSONB DEFAULT '{}'
);

-- 9. Cohorts
CREATE TABLE IF NOT EXISTS public.cohorts (
    id BIGSERIAL PRIMARY KEY,
    cohort_name TEXT NOT NULL UNIQUE,
    description TEXT,
    definition JSONB NOT NULL,
    member_count INTEGER DEFAULT 0,
    created_by UUID REFERENCES auth.users ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 10. Cohort members
CREATE TABLE IF NOT EXISTS public.cohort_members (
    id BIGSERIAL PRIMARY KEY,
    cohort_id BIGINT REFERENCES public.cohorts ON DELETE CASCADE NOT NULL,
    user_id UUID REFERENCES auth.users ON DELETE CASCADE NOT NULL,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    left_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    UNIQUE(cohort_id, user_id)
);

-- 11. Cohort metrics (daily snapshots)
CREATE TABLE IF NOT EXISTS public.cohort_metrics (
    id BIGSERIAL PRIMARY KEY,
    cohort_id BIGINT REFERENCES public.cohorts ON DELETE CASCADE NOT NULL,
    date DATE NOT NULL,
    active_users INTEGER DEFAULT 0,
    new_retained INTEGER DEFAULT 0,
    returning_users INTEGER DEFAULT 0,
    churned_users INTEGER DEFAULT 0,
    retention_rate REAL DEFAULT 0,
    revenue REAL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(cohort_id, date)
);

-- 12. Retention snapshots
CREATE TABLE IF NOT EXISTS public.retention_snapshots (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users ON DELETE CASCADE NOT NULL,
    cohort_date DATE NOT NULL,
    day_0 BOOLEAN DEFAULT true,
    day_1 BOOLEAN DEFAULT false,
    day_3 BOOLEAN DEFAULT false,
    day_7 BOOLEAN DEFAULT false,
    day_14 BOOLEAN DEFAULT false,
    day_30 BOOLEAN DEFAULT false,
    day_60 BOOLEAN DEFAULT false,
    day_90 BOOLEAN DEFAULT false,
    last_active_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(user_id, cohort_date)
);

-- 13. Revenue events
CREATE TABLE IF NOT EXISTS public.revenue_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users ON DELETE CASCADE NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('subscription_start', 'subscription_renewal', 'subscription_upgrade', 'subscription_downgrade', 'subscription_cancel', 'one_time_purchase', 'refund')),
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    plan_name TEXT,
    plan_interval TEXT,
    payment_method TEXT,
    stripe_invoice_id TEXT,
    stripe_customer_id TEXT,
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 14. Custom reports
CREATE TABLE IF NOT EXISTS public.custom_reports (
    id BIGSERIAL PRIMARY KEY,
    report_name TEXT NOT NULL,
    description TEXT,
    created_by UUID REFERENCES auth.users ON DELETE SET NULL,
    config JSONB NOT NULL,
    schedule TEXT,
    recipients TEXT[],
    last_run_at TIMESTAMP WITH TIME ZONE,
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 15. Report runs
CREATE TABLE IF NOT EXISTS public.report_runs (
    id BIGSERIAL PRIMARY KEY,
    report_id BIGINT REFERENCES public.custom_reports ON DELETE CASCADE NOT NULL,
    triggered_by UUID REFERENCES auth.users ON DELETE SET NULL,
    status TEXT DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
    result JSONB,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for analytics performance
CREATE INDEX IF NOT EXISTS idx_analytics_events_v2_user_timestamp ON public.analytics_events_v2(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_events_v2_type_timestamp ON public.analytics_events_v2(event_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_events_v2_category ON public.analytics_events_v2(category);
CREATE INDEX IF NOT EXISTS idx_analytics_events_v2_session ON public.analytics_events_v2(session_id);

CREATE INDEX IF NOT EXISTS idx_user_behavior_user_timestamp ON public.user_behavior_events(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_user_behavior_session ON public.user_behavior_events(session_id);
CREATE INDEX IF NOT EXISTS idx_user_behavior_event_type ON public.user_behavior_events(event_type);

CREATE INDEX IF NOT EXISTS idx_feature_adoption_user ON public.feature_adoption(user_id);
CREATE INDEX IF NOT EXISTS idx_feature_adoption_feature ON public.feature_adoption(feature_name);
CREATE INDEX IF NOT EXISTS idx_feature_adoption_adopted ON public.feature_adoption(is_adopted) WHERE is_adopted = true;

CREATE INDEX IF NOT EXISTS idx_ab_test_assignments_test_user ON public.ab_test_assignments(test_id, user_id);
CREATE INDEX IF NOT EXISTS idx_ab_test_events_test_user ON public.ab_test_events(test_id, user_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_funnel_events_funnel_user ON public.funnel_events(funnel_id, user_id, step_index);
CREATE INDEX IF NOT EXISTS idx_funnel_events_session ON public.funnel_events(session_id);

CREATE INDEX IF NOT EXISTS idx_cohort_members_cohort ON public.cohort_members(cohort_id, is_active);
CREATE INDEX IF NOT EXISTS idx_cohort_metrics_cohort_date ON public.cohort_metrics(cohort_id, date DESC);

CREATE INDEX IF NOT EXISTS idx_retention_user_cohort ON public.retention_snapshots(user_id, cohort_date);

CREATE INDEX IF NOT EXISTS idx_revenue_user_timestamp ON public.revenue_events(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_revenue_type ON public.revenue_events(event_type);

CREATE INDEX IF NOT EXISTS idx_report_runs_report ON public.report_runs(report_id, started_at DESC);

-- RLS Policies
ALTER TABLE public.analytics_events_v2 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_behavior_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feature_adoption ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ab_tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ab_test_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ab_test_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.funnels ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.funnel_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cohorts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cohort_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cohort_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.retention_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.revenue_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.custom_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.report_runs ENABLE ROW LEVEL SECURITY;

-- Analytics events: users can insert, admins can view all
CREATE POLICY "Users can insert own analytics events"
    ON public.analytics_events_v2 FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Admins can view all analytics events"
    ON public.analytics_events_v2 FOR SELECT USING (
        EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'moderator'))
    );

-- User behavior events
CREATE POLICY "Users can insert own behavior events"
    ON public.user_behavior_events FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Admins can view all behavior events"
    ON public.user_behavior_events FOR SELECT USING (
        EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'moderator'))
    );

-- Feature adoption
CREATE POLICY "Users can insert own feature adoption"
    ON public.feature_adoption FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can view own feature adoption"
    ON public.feature_adoption FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Admins can manage all feature adoption"
    ON public.feature_adoption FOR ALL USING (
        EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'moderator'))
    );

-- A/B tests (admin only)
CREATE POLICY "Admins can manage ab tests"
    ON public.ab_tests FOR ALL USING (
        EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'moderator'))
    );
CREATE POLICY "Users can view active ab tests"
    ON public.ab_tests FOR SELECT USING (status = 'running' OR status = 'paused');

-- A/B test assignments
CREATE POLICY "Users can insert own assignments"
    ON public.ab_test_assignments FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can view own assignments"
    ON public.ab_test_assignments FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Admins can view all assignments"
    ON public.ab_test_assignments FOR SELECT USING (
        EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'moderator'))
    );

-- A/B test events
CREATE POLICY "Users can insert own ab events"
    ON public.ab_test_events FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Admins can view all ab events"
    ON public.ab_test_events FOR SELECT USING (
        EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'moderator'))
    );

-- Funnels
CREATE POLICY "Admins can manage funnels"
    ON public.funnels FOR ALL USING (
        EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'moderator'))
    );
CREATE POLICY "Authenticated users can view active funnels"
    ON public.funnels FOR SELECT USING (is_active = true AND auth.uid() IS NOT NULL);

-- Funnel events
CREATE POLICY "Users can insert own funnel events"
    ON public.funnel_events FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Admins can view all funnel events"
    ON public.funnel_events FOR SELECT USING (
        EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'moderator'))
    );

-- Cohorts
CREATE POLICY "Admins can manage cohorts"
    ON public.cohorts FOR ALL USING (
        EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'moderator'))
    );
CREATE POLICY "Authenticated users can view cohorts"
    ON public.cohorts FOR SELECT USING (auth.uid() IS NOT NULL);

-- Cohort members
CREATE POLICY "Admins can manage cohort members"
    ON public.cohort_members FOR ALL USING (
        EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'moderator'))
    );

-- Cohort metrics
CREATE POLICY "Admins can view cohort metrics"
    ON public.cohort_metrics FOR SELECT USING (
        EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'moderator'))
    );

-- Retention snapshots
CREATE POLICY "Users can view own retention"
    ON public.retention_snapshots FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Admins can view all retention"
    ON public.retention_snapshots FOR SELECT USING (
        EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'moderator'))
    );

-- Revenue events (admin only)
CREATE POLICY "Admins can manage revenue events"
    ON public.revenue_events FOR ALL USING (
        EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'moderator'))
    );

-- Custom reports
CREATE POLICY "Users can create own reports"
    ON public.custom_reports FOR INSERT WITH CHECK (auth.uid() = created_by);
CREATE POLICY "Users can view own reports or public reports"
    ON public.custom_reports FOR SELECT USING (
        auth.uid() = created_by OR is_public = true OR
        EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'moderator'))
    );
CREATE POLICY "Users can update own reports"
    ON public.custom_reports FOR UPDATE USING (auth.uid() = created_by);
CREATE POLICY "Users can delete own reports"
    ON public.custom_reports FOR DELETE USING (auth.uid() = created_by);
CREATE POLICY "Admins can manage all reports"
    ON public.custom_reports FOR ALL USING (
        EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'moderator'))
    );

-- Report runs
CREATE POLICY "Users can view own report runs"
    ON public.report_runs FOR SELECT USING (
        auth.uid() = (SELECT created_by FROM public.custom_reports WHERE id = report_id) OR
        EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'moderator'))
    );
CREATE POLICY "Admins can manage report runs"
    ON public.report_runs FOR ALL USING (
        EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role IN ('admin', 'moderator'))
    );
