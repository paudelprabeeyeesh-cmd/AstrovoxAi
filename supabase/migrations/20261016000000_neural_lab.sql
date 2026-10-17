-- Persistent, tenant-isolated metadata for the experimental Neural Lab.
-- Checkpoint and dataset content stays in the configured backend storage root.
CREATE TABLE IF NOT EXISTS public.neural_lab_datasets (
    id text PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name text NOT NULL,
    digest text NOT NULL,
    metadata jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, digest)
);
CREATE INDEX IF NOT EXISTS neural_lab_datasets_user_created
    ON public.neural_lab_datasets (user_id, created_at DESC);
ALTER TABLE public.neural_lab_datasets ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.neural_lab_datasets TO authenticated;
REVOKE ALL ON public.neural_lab_datasets FROM anon;
CREATE POLICY neural_lab_datasets_select_own ON public.neural_lab_datasets
    FOR SELECT TO authenticated USING (user_id = auth.uid());
CREATE POLICY neural_lab_datasets_insert_own ON public.neural_lab_datasets
    FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());
CREATE POLICY neural_lab_datasets_update_own ON public.neural_lab_datasets
    FOR UPDATE TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY neural_lab_datasets_delete_own ON public.neural_lab_datasets
    FOR DELETE TO authenticated USING (user_id = auth.uid());

CREATE TABLE IF NOT EXISTS public.neural_lab_jobs (
    id text PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    dataset_id text NOT NULL,
    config jsonb NOT NULL,
    status text NOT NULL,
    error text,
    progress jsonb NOT NULL DEFAULT '{}'::jsonb,
    run_path text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.neural_lab_jobs ADD COLUMN IF NOT EXISTS error text;
ALTER TABLE public.neural_lab_jobs ADD COLUMN IF NOT EXISTS progress jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS neural_lab_jobs_user_created
    ON public.neural_lab_jobs (user_id, created_at DESC);

ALTER TABLE public.neural_lab_jobs ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.neural_lab_jobs TO authenticated;
REVOKE ALL ON public.neural_lab_jobs FROM anon;
CREATE POLICY neural_lab_jobs_select_own ON public.neural_lab_jobs
    FOR SELECT TO authenticated USING (user_id = auth.uid());
CREATE POLICY neural_lab_jobs_insert_own ON public.neural_lab_jobs
    FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());
CREATE POLICY neural_lab_jobs_update_own ON public.neural_lab_jobs
    FOR UPDATE TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY neural_lab_jobs_delete_own ON public.neural_lab_jobs
    FOR DELETE TO authenticated USING (user_id = auth.uid());

CREATE TABLE IF NOT EXISTS public.neural_lab_models (
    id text PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    training_job_id text NOT NULL,
    name text NOT NULL,
    architecture text NOT NULL,
    origin text NOT NULL,
    configuration jsonb NOT NULL,
    training_status text NOT NULL,
    artifact_path text NOT NULL,
    dataset_provenance text NOT NULL,
    evaluation_results jsonb NOT NULL DEFAULT '{}'::jsonb,
    compatibility_status text NOT NULL DEFAULT 'experimental-only; not connected to Astrovox chat',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS neural_lab_models_user_created
    ON public.neural_lab_models (user_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS neural_lab_models_user_job
    ON public.neural_lab_models (user_id, training_job_id);
ALTER TABLE public.neural_lab_models ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.neural_lab_models TO authenticated;
REVOKE ALL ON public.neural_lab_models FROM anon;
CREATE POLICY neural_lab_models_select_own ON public.neural_lab_models
    FOR SELECT TO authenticated USING (user_id = auth.uid());
CREATE POLICY neural_lab_models_insert_own ON public.neural_lab_models
    FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());
CREATE POLICY neural_lab_models_update_own ON public.neural_lab_models
    FOR UPDATE TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY neural_lab_models_delete_own ON public.neural_lab_models
    FOR DELETE TO authenticated USING (user_id = auth.uid());

CREATE TABLE IF NOT EXISTS public.neural_lab_model_selection (
    user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    active_model_id text REFERENCES public.neural_lab_models(id) ON DELETE SET NULL,
    previous_model_id text REFERENCES public.neural_lab_models(id) ON DELETE SET NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.neural_lab_model_selection ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.neural_lab_model_selection TO authenticated;
REVOKE ALL ON public.neural_lab_model_selection FROM anon;
CREATE POLICY neural_lab_model_selection_select_own ON public.neural_lab_model_selection
    FOR SELECT TO authenticated USING (
        user_id = auth.uid()
        AND (active_model_id IS NULL OR EXISTS (
            SELECT 1 FROM public.neural_lab_models m WHERE m.id = active_model_id AND m.user_id = auth.uid()
        ))
    );
CREATE POLICY neural_lab_model_selection_insert_own ON public.neural_lab_model_selection
    FOR INSERT TO authenticated WITH CHECK (
        user_id = auth.uid()
        AND (active_model_id IS NULL OR EXISTS (
            SELECT 1 FROM public.neural_lab_models m WHERE m.id = active_model_id AND m.user_id = auth.uid()
        ))
        AND (previous_model_id IS NULL OR EXISTS (
            SELECT 1 FROM public.neural_lab_models m WHERE m.id = previous_model_id AND m.user_id = auth.uid()
        ))
    );
CREATE POLICY neural_lab_model_selection_update_own ON public.neural_lab_model_selection
    FOR UPDATE TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (
        user_id = auth.uid()
        AND (active_model_id IS NULL OR EXISTS (
            SELECT 1 FROM public.neural_lab_models m WHERE m.id = active_model_id AND m.user_id = auth.uid()
        ))
        AND (previous_model_id IS NULL OR EXISTS (
            SELECT 1 FROM public.neural_lab_models m WHERE m.id = previous_model_id AND m.user_id = auth.uid()
        ))
    );
CREATE POLICY neural_lab_model_selection_delete_own ON public.neural_lab_model_selection
    FOR DELETE TO authenticated USING (user_id = auth.uid());
