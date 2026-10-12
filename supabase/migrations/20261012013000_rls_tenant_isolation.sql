-- Row-level security policies for tenant isolation.
--
-- Why this exists: the application layer derives the tenant id from the
-- verified principal and 30 tests assert it does. That is one control, and
-- it only holds if every call site is correct. A single missed call site
-- is a cross-tenant read. These policies make the database assert the same
-- rule, so a mistake in application code is refused by Postgres instead of
-- silently returning another tenant's rows.
--
-- There were no policies here before. `git ls-files "*migrations/*rls*"`
-- returned nothing, and the only file mentioning rls was a read-only
-- verification query. The gap is now closed for every tenant-owned table.
--
-- The claim is `sub`, which Supabase sets from the verified JWT. A policy
-- comparing against `current_setting('request.jwt.claim.sub', true)` is
-- unauthenticated-safe: the second argument `true` means "return NULL
-- rather than error when the setting is absent", and NULL::uuid fails the
-- comparison, so anon gets nothing rather than everything.

-- ---------------------------------------------------------------------------
-- conversations
-- ---------------------------------------------------------------------------
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "conversations_select_own" ON public.conversations;
CREATE POLICY "conversations_select_own"
    ON public.conversations
    FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

DROP POLICY IF EXISTS "conversations_insert_own" ON public.conversations;
CREATE POLICY "conversations_insert_own"
    ON public.conversations
    FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "conversations_update_own" ON public.conversations;
CREATE POLICY "conversations_update_own"
    ON public.conversations
    FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "conversations_delete_own" ON public.conversations;
CREATE POLICY "conversations_delete_own"
    ON public.conversations
    FOR DELETE
    TO authenticated
    USING (user_id = auth.uid());

-- ---------------------------------------------------------------------------
-- messages
-- ---------------------------------------------------------------------------
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "messages_select_own" ON public.messages;
CREATE POLICY "messages_select_own"
    ON public.messages
    FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

DROP POLICY IF EXISTS "messages_insert_own" ON public.messages;
CREATE POLICY "messages_insert_own"
    ON public.messages
    FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "messages_update_own" ON public.messages;
CREATE POLICY "messages_update_own"
    ON public.messages
    FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "messages_delete_own" ON public.messages;
CREATE POLICY "messages_delete_own"
    ON public.messages
    FOR DELETE
    TO authenticated
    USING (user_id = auth.uid());

-- ---------------------------------------------------------------------------
-- ai_memory
-- ---------------------------------------------------------------------------
ALTER TABLE public.ai_memory ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "ai_memory_select_own" ON public.ai_memory;
CREATE POLICY "ai_memory_select_own"
    ON public.ai_memory
    FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

DROP POLICY IF EXISTS "ai_memory_insert_own" ON public.ai_memory;
CREATE POLICY "ai_memory_insert_own"
    ON public.ai_memory
    FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "ai_memory_update_own" ON public.ai_memory;
CREATE POLICY "ai_memory_update_own"
    ON public.ai_memory
    FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "ai_memory_delete_own" ON public.ai_memory;
CREATE POLICY "ai_memory_delete_own"
    ON public.ai_memory
    FOR DELETE
    TO authenticated
    USING (user_id = auth.uid());

-- ---------------------------------------------------------------------------
-- documents
-- ---------------------------------------------------------------------------
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "documents_select_own" ON public.documents;
CREATE POLICY "documents_select_own"
    ON public.documents
    FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

DROP POLICY IF EXISTS "documents_insert_own" ON public.documents;
CREATE POLICY "documents_insert_own"
    ON public.documents
    FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "documents_update_own" ON public.documents;
CREATE POLICY "documents_update_own"
    ON public.documents
    FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "documents_delete_own" ON public.documents;
CREATE POLICY "documents_delete_own"
    ON public.documents
    FOR DELETE
    TO authenticated
    USING (user_id = auth.uid());

-- ---------------------------------------------------------------------------
-- document_chunks
--
-- Ownership is inherited through the parent document, not carried on the
-- chunk itself. A chunk with no matching parent is unreadable, which is
-- correct: an orphaned chunk belongs to nobody.
-- ---------------------------------------------------------------------------
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "document_chunks_select_own" ON public.document_chunks;
CREATE POLICY "document_chunks_select_own"
    ON public.document_chunks
    FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.documents d
            WHERE d.id = document_chunks.document_id
              AND d.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "document_chunks_insert_own" ON public.document_chunks;
CREATE POLICY "document_chunks_insert_own"
    ON public.document_chunks
    FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.documents d
            WHERE d.id = document_chunks.document_id
              AND d.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "document_chunks_delete_own" ON public.document_chunks;
CREATE POLICY "document_chunks_delete_own"
    ON public.document_chunks
    FOR DELETE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.documents d
            WHERE d.id = document_chunks.document_id
              AND d.user_id = auth.uid()
        )
    );


-- ---------------------------------------------------------------------------
-- interactions
-- ---------------------------------------------------------------------------
ALTER TABLE public.interactions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "interactions_select_own" ON public.interactions;
CREATE POLICY "interactions_select_own" ON public.interactions FOR SELECT TO authenticated USING (user_id = auth.uid());

DROP POLICY IF EXISTS "interactions_insert_own" ON public.interactions;
CREATE POLICY "interactions_insert_own" ON public.interactions FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "interactions_update_own" ON public.interactions;
CREATE POLICY "interactions_update_own" ON public.interactions FOR UPDATE TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "interactions_delete_own" ON public.interactions;
CREATE POLICY "interactions_delete_own" ON public.interactions FOR DELETE TO authenticated USING (user_id = auth.uid());


-- ---------------------------------------------------------------------------
-- finetuning_jobs
-- ---------------------------------------------------------------------------
ALTER TABLE public.finetuning_jobs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "finetuning_jobs_select_own" ON public.finetuning_jobs;
CREATE POLICY "finetuning_jobs_select_own" ON public.finetuning_jobs FOR SELECT TO authenticated USING (user_id = auth.uid());

DROP POLICY IF EXISTS "finetuning_jobs_insert_own" ON public.finetuning_jobs;
CREATE POLICY "finetuning_jobs_insert_own" ON public.finetuning_jobs FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "finetuning_jobs_update_own" ON public.finetuning_jobs;
CREATE POLICY "finetuning_jobs_update_own" ON public.finetuning_jobs FOR UPDATE TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "finetuning_jobs_delete_own" ON public.finetuning_jobs;
CREATE POLICY "finetuning_jobs_delete_own" ON public.finetuning_jobs FOR DELETE TO authenticated USING (user_id = auth.uid());


-- ---------------------------------------------------------------------------
-- training_datasets
-- ---------------------------------------------------------------------------
ALTER TABLE public.training_datasets ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "training_datasets_select_own" ON public.training_datasets;
CREATE POLICY "training_datasets_select_own" ON public.training_datasets FOR SELECT TO authenticated USING (user_id = auth.uid());

DROP POLICY IF EXISTS "training_datasets_insert_own" ON public.training_datasets;
CREATE POLICY "training_datasets_insert_own" ON public.training_datasets FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "training_datasets_update_own" ON public.training_datasets;
CREATE POLICY "training_datasets_update_own" ON public.training_datasets FOR UPDATE TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "training_datasets_delete_own" ON public.training_datasets;
CREATE POLICY "training_datasets_delete_own" ON public.training_datasets FOR DELETE TO authenticated USING (user_id = auth.uid());


-- ---------------------------------------------------------------------------
-- usage_events
-- ---------------------------------------------------------------------------
ALTER TABLE public.usage_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "usage_events_select_own" ON public.usage_events;
CREATE POLICY "usage_events_select_own" ON public.usage_events FOR SELECT TO authenticated USING (user_id = auth.uid());

DROP POLICY IF EXISTS "usage_events_insert_own" ON public.usage_events;
CREATE POLICY "usage_events_insert_own" ON public.usage_events FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "usage_events_update_own" ON public.usage_events;
CREATE POLICY "usage_events_update_own" ON public.usage_events FOR UPDATE TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "usage_events_delete_own" ON public.usage_events;
CREATE POLICY "usage_events_delete_own" ON public.usage_events FOR DELETE TO authenticated USING (user_id = auth.uid());

-- ---------------------------------------------------------------------------
-- Explicit anon denial
-- ---------------------------------------------------------------------------
-- ENABLE ROW LEVEL SECURITY with no anon policy denies anon by default.
-- Stating it explicitly keeps that from reading as an oversight, and makes
-- the coverage testable.

DROP POLICY IF EXISTS "conversations_deny_anon" ON public.conversations;
CREATE POLICY "conversations_deny_anon" ON public.conversations FOR ALL TO anon USING (false) WITH CHECK (false);
DROP POLICY IF EXISTS "messages_deny_anon" ON public.messages;
CREATE POLICY "messages_deny_anon" ON public.messages FOR ALL TO anon USING (false) WITH CHECK (false);
DROP POLICY IF EXISTS "ai_memory_deny_anon" ON public.ai_memory;
CREATE POLICY "ai_memory_deny_anon" ON public.ai_memory FOR ALL TO anon USING (false) WITH CHECK (false);
DROP POLICY IF EXISTS "documents_deny_anon" ON public.documents;
CREATE POLICY "documents_deny_anon" ON public.documents FOR ALL TO anon USING (false) WITH CHECK (false);
DROP POLICY IF EXISTS "document_chunks_deny_anon" ON public.document_chunks;
CREATE POLICY "document_chunks_deny_anon" ON public.document_chunks FOR ALL TO anon USING (false) WITH CHECK (false);
DROP POLICY IF EXISTS "interactions_deny_anon" ON public.interactions;
CREATE POLICY "interactions_deny_anon" ON public.interactions FOR ALL TO anon USING (false) WITH CHECK (false);
DROP POLICY IF EXISTS "finetuning_jobs_deny_anon" ON public.finetuning_jobs;
CREATE POLICY "finetuning_jobs_deny_anon" ON public.finetuning_jobs FOR ALL TO anon USING (false) WITH CHECK (false);
DROP POLICY IF EXISTS "training_datasets_deny_anon" ON public.training_datasets;
CREATE POLICY "training_datasets_deny_anon" ON public.training_datasets FOR ALL TO anon USING (false) WITH CHECK (false);
DROP POLICY IF EXISTS "usage_events_deny_anon" ON public.usage_events;
CREATE POLICY "usage_events_deny_anon" ON public.usage_events FOR ALL TO anon USING (false) WITH CHECK (false);

-- ---------------------------------------------------------------------------
-- Explicit anon denial on every tenant-owned table.
--
-- ENABLE ROW LEVEL SECURITY with no anon policy denies anon by default;
-- stating it explicitly keeps that from reading as an oversight and makes
-- the coverage testable by tests/security/test_rls_migration.py.
-- ---------------------------------------------------------------------------

DROP POLICY IF EXISTS "conversations_deny_anon" ON public.conversations;
CREATE POLICY "conversations_deny_anon" ON public.conversations FOR ALL TO anon USING (false) WITH CHECK (false);

DROP POLICY IF EXISTS "messages_deny_anon" ON public.messages;
CREATE POLICY "messages_deny_anon" ON public.messages FOR ALL TO anon USING (false) WITH CHECK (false);

DROP POLICY IF EXISTS "ai_memory_deny_anon" ON public.ai_memory;
CREATE POLICY "ai_memory_deny_anon" ON public.ai_memory FOR ALL TO anon USING (false) WITH CHECK (false);

DROP POLICY IF EXISTS "documents_deny_anon" ON public.documents;
CREATE POLICY "documents_deny_anon" ON public.documents FOR ALL TO anon USING (false) WITH CHECK (false);

DROP POLICY IF EXISTS "document_chunks_deny_anon" ON public.document_chunks;
CREATE POLICY "document_chunks_deny_anon" ON public.document_chunks FOR ALL TO anon USING (false) WITH CHECK (false);

DROP POLICY IF EXISTS "interactions_deny_anon" ON public.interactions;
CREATE POLICY "interactions_deny_anon" ON public.interactions FOR ALL TO anon USING (false) WITH CHECK (false);

DROP POLICY IF EXISTS "finetuning_jobs_deny_anon" ON public.finetuning_jobs;
CREATE POLICY "finetuning_jobs_deny_anon" ON public.finetuning_jobs FOR ALL TO anon USING (false) WITH CHECK (false);

DROP POLICY IF EXISTS "training_datasets_deny_anon" ON public.training_datasets;
CREATE POLICY "training_datasets_deny_anon" ON public.training_datasets FOR ALL TO anon USING (false) WITH CHECK (false);

DROP POLICY IF EXISTS "usage_events_deny_anon" ON public.usage_events;
CREATE POLICY "usage_events_deny_anon" ON public.usage_events FOR ALL TO anon USING (false) WITH CHECK (false);

