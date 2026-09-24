import sqlite3
from datetime import datetime, timezone
from typing import List, Tuple


def get_enterprise_migrations() -> List[Tuple[int, str, str]]:
    return [
        (
            10,
            "create_organizations",
            """
            CREATE TABLE IF NOT EXISTS organizations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                owner_id TEXT NOT NULL,
                plan TEXT NOT NULL DEFAULT 'free',
                tenant_id TEXT UNIQUE,
                custom_domain TEXT,
                white_label_enabled INTEGER DEFAULT 0,
                white_label_config TEXT,
                sso_enabled INTEGER DEFAULT 0,
                sso_provider TEXT,
                sso_config TEXT,
                scim_enabled INTEGER DEFAULT 0,
                scim_secret TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_organizations_owner ON organizations(owner_id);
            CREATE INDEX IF NOT EXISTS idx_organizations_tenant ON organizations(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_organizations_slug ON organizations(slug);
            """,
        ),
        (
            11,
            "create_organization_members",
            """
            CREATE TABLE IF NOT EXISTS organization_members (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                permissions TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                invited_by TEXT,
                joined_at TEXT NOT NULL,
                left_at TEXT,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE,
                UNIQUE(org_id, user_id)
            );
            CREATE INDEX IF NOT EXISTS idx_org_members_org ON organization_members(org_id);
            CREATE INDEX IF NOT EXISTS idx_org_members_user ON organization_members(user_id);
            """,
        ),
        (
            12,
            "create_workspaces",
            """
            CREATE TABLE IF NOT EXISTS workspaces (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_workspaces_org ON workspaces(org_id);
            CREATE INDEX IF NOT EXISTS idx_workspaces_owner ON workspaces(owner_id);
            """,
        ),
        (
            13,
            "create_workspace_members",
            """
            CREATE TABLE IF NOT EXISTS workspace_members (
                id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                permissions TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                joined_at TEXT NOT NULL,
                left_at TEXT,
                FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
                UNIQUE(workspace_id, user_id)
            );
            CREATE INDEX IF NOT EXISTS idx_workspace_members_workspace ON workspace_members(workspace_id);
            CREATE INDEX IF NOT EXISTS idx_workspace_members_user ON workspace_members(user_id);
            """,
        ),
        (
            14,
            "create_teams",
            """
            CREATE TABLE IF NOT EXISTS teams (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                workspace_id TEXT,
                owner_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE,
                FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE SET NULL
            );
            CREATE INDEX IF NOT EXISTS idx_teams_org ON teams(org_id);
            CREATE INDEX IF NOT EXISTS idx_teams_workspace ON teams(workspace_id);
            """,
        ),
        (
            15,
            "create_team_members",
            """
            CREATE TABLE IF NOT EXISTS team_members (
                id TEXT PRIMARY KEY,
                team_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                permissions TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                joined_at TEXT NOT NULL,
                left_at TEXT,
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
                UNIQUE(team_id, user_id)
            );
            CREATE INDEX IF NOT EXISTS idx_team_members_team ON team_members(team_id);
            CREATE INDEX IF NOT EXISTS idx_team_members_user ON team_members(user_id);
            """,
        ),
        (
            16,
            "create_invitations",
            """
            CREATE TABLE IF NOT EXISTS invitations (
                id TEXT PRIMARY KEY,
                workspace_id TEXT,
                team_id TEXT,
                org_id TEXT NOT NULL,
                email TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                token TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'pending',
                invited_by TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                accepted_at TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_invitations_token ON invitations(token);
            CREATE INDEX IF NOT EXISTS idx_invitations_email ON invitations(email);
            """,
        ),
        (
            17,
            "create_enterprise_accounts",
            """
            CREATE TABLE IF NOT EXISTS enterprise_accounts (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                account_name TEXT NOT NULL,
                account_type TEXT NOT NULL DEFAULT 'business',
                billing_email TEXT NOT NULL,
                billing_address TEXT,
                tax_id TEXT,
                payment_method_id TEXT,
                stripe_customer_id TEXT,
                plan TEXT NOT NULL DEFAULT 'enterprise',
                status TEXT NOT NULL DEFAULT 'active',
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_enterprise_accounts_org ON enterprise_accounts(org_id);
            """,
        ),
        (
            18,
            "create_subscriptions",
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                user_id TEXT,
                plan TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                stripe_subscription_id TEXT,
                stripe_price_id TEXT,
                current_period_start TEXT,
                current_period_end TEXT,
                cancel_at_period_end INTEGER DEFAULT 0,
                canceled_at TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_subscriptions_org ON subscriptions(org_id);
            """,
        ),
        (
            19,
            "create_audit_logs",
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                org_id TEXT,
                user_id TEXT,
                actor_type TEXT NOT NULL DEFAULT 'user',
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                status TEXT NOT NULL DEFAULT 'success',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_audit_logs_org ON audit_logs(org_id);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at);
            """,
        ),
        (
            20,
            "create_enterprise_audit_logs",
            """
            CREATE TABLE IF NOT EXISTS enterprise_audit_logs (
                id TEXT PRIMARY KEY,
                org_id TEXT,
                user_id TEXT,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                details TEXT,
                severity TEXT NOT NULL DEFAULT 'info',
                status TEXT NOT NULL DEFAULT 'success',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_enterprise_audit_org ON enterprise_audit_logs(org_id);
            CREATE INDEX IF NOT EXISTS idx_enterprise_audit_user ON enterprise_audit_logs(user_id);
            """,
        ),
        (
            21,
            "create_sso_connections",
            """
            CREATE TABLE IF NOT EXISTS sso_connections (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                provider_type TEXT NOT NULL,
                provider_name TEXT,
                config TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                last_used_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_sso_connections_org ON sso_connections(org_id);
            """,
        ),
        (
            22,
            "create_sso_users",
            """
            CREATE TABLE IF NOT EXISTS sso_users (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                provider_user_id TEXT NOT NULL,
                email TEXT NOT NULL,
                user_id TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE,
                UNIQUE(org_id, provider, email)
            );
            CREATE INDEX IF NOT EXISTS idx_sso_users_org ON sso_users(org_id);
            CREATE INDEX IF NOT EXISTS idx_sso_users_email ON sso_users(email);
            """,
        ),
        (
            23,
            "create_slas",
            """
            CREATE TABLE IF NOT EXISTS slas (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                account_id TEXT,
                tier TEXT NOT NULL,
                uptime_guarantee REAL NOT NULL,
                response_time_hours INTEGER NOT NULL,
                resolution_time_hours INTEGER,
                support_tier TEXT NOT NULL DEFAULT 'standard',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_slas_org ON slas(org_id);
            """,
        ),
        (
            24,
            "create_sla_breaches",
            """
            CREATE TABLE IF NOT EXISTS sla_breaches (
                id TEXT PRIMARY KEY,
                sla_id TEXT NOT NULL,
                org_id TEXT NOT NULL,
                breach_type TEXT NOT NULL,
                description TEXT,
                duration_minutes INTEGER,
                status TEXT NOT NULL DEFAULT 'open',
                resolved_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (sla_id) REFERENCES slas(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_sla_breaches_sla ON sla_breaches(sla_id);
            CREATE INDEX IF NOT EXISTS idx_sla_breaches_org ON sla_breaches(org_id);
            """,
        ),
        (
            25,
            "create_support_tickets",
            """
            CREATE TABLE IF NOT EXISTS support_tickets (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                user_id TEXT,
                ticket_number TEXT UNIQUE NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'medium',
                status TEXT NOT NULL DEFAULT 'open',
                category TEXT,
                assigned_to TEXT,
                tags TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolved_at TEXT,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_support_tickets_org ON support_tickets(org_id);
            CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status);
            CREATE INDEX IF NOT EXISTS idx_support_tickets_number ON support_tickets(ticket_number);
            """,
        ),
        (
            26,
            "create_support_ticket_messages",
            """
            CREATE TABLE IF NOT EXISTS support_ticket_messages (
                id TEXT PRIMARY KEY,
                ticket_id TEXT NOT NULL,
                user_id TEXT,
                message TEXT NOT NULL,
                message_type TEXT NOT NULL DEFAULT 'reply',
                attachments TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (ticket_id) REFERENCES support_tickets(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_ticket_messages_ticket ON support_ticket_messages(ticket_id);
            """,
        ),
        (
            27,
            "create_white_label_configs",
            """
            CREATE TABLE IF NOT EXISTS white_label_configs (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL UNIQUE,
                brand_name TEXT,
                logo_url TEXT,
                favicon_url TEXT,
                primary_color TEXT,
                secondary_color TEXT,
                accent_color TEXT,
                custom_css TEXT,
                email_from_name TEXT,
                email_from_address TEXT,
                support_email TEXT,
                privacy_policy_url TEXT,
                terms_of_service_url TEXT,
                hide_powered_by INTEGER DEFAULT 0,
                custom_domain TEXT,
                ssl_enabled INTEGER DEFAULT 0,
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_white_label_org ON white_label_configs(org_id);
            """,
        ),
        (
            28,
            "create_custom_domains",
            """
            CREATE TABLE IF NOT EXISTS custom_domains (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                domain TEXT NOT NULL UNIQUE,
                verification_token TEXT NOT NULL,
                verified INTEGER DEFAULT 0,
                ssl_status TEXT DEFAULT 'pending',
                ssl_cert_path TEXT,
                ssl_key_path TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                metadata TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_custom_domains_org ON custom_domains(org_id);
            CREATE INDEX IF NOT EXISTS idx_custom_domains_domain ON custom_domains(domain);
            """,
        ),
        (
            29,
            "create_data_retention_policies",
            """
            CREATE TABLE IF NOT EXISTS data_retention_policies (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                policy_name TEXT NOT NULL,
                data_type TEXT NOT NULL,
                retention_days INTEGER NOT NULL,
                auto_delete INTEGER DEFAULT 0,
                archive_before_delete INTEGER DEFAULT 0,
                archive_path TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_retention_policies_org ON data_retention_policies(org_id);
            """,
        ),
        (
            30,
            "create_data_deletion_requests",
            """
            CREATE TABLE IF NOT EXISTS data_deletion_requests (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                user_id TEXT,
                request_type TEXT NOT NULL,
                reason TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                processed_by TEXT,
                processed_at TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_deletion_requests_org ON data_deletion_requests(org_id);
            CREATE INDEX IF NOT EXISTS idx_deletion_requests_status ON data_deletion_requests(status);
            """,
        ),
        (
            31,
            "create_quota_limits",
            """
            CREATE TABLE IF NOT EXISTS quota_limits (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                user_id TEXT,
                resource_type TEXT NOT NULL,
                limit_value REAL NOT NULL,
                used_value REAL NOT NULL DEFAULT 0,
                period TEXT NOT NULL DEFAULT 'monthly',
                reset_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_quota_limits_org ON quota_limits(org_id);
            CREATE INDEX IF NOT EXISTS idx_quota_limits_user ON quota_limits(user_id);
            """,
        ),
        (
            32,
            "create_usage_metering",
            """
            CREATE TABLE IF NOT EXISTS usage_metering (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                user_id TEXT,
                resource_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit TEXT NOT NULL,
                cost REAL NOT NULL DEFAULT 0,
                billing_period TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_usage_metering_org ON usage_metering(org_id);
            CREATE INDEX IF NOT EXISTS idx_usage_metering_period ON usage_metering(billing_period);
            """,
        ),
        (
            33,
            "create_compliance_reports",
            """
            CREATE TABLE IF NOT EXISTS compliance_reports (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                report_type TEXT NOT NULL,
                framework TEXT NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'generated',
                findings TEXT,
                recommendations TEXT,
                generated_by TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_compliance_reports_org ON compliance_reports(org_id);
            CREATE INDEX IF NOT EXISTS idx_compliance_reports_type ON compliance_reports(report_type);
            """,
        ),
        (
            34,
            "create_security_certifications",
            """
            CREATE TABLE IF NOT EXISTS security_certifications (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                certification_name TEXT NOT NULL,
                certification_body TEXT NOT NULL,
                issued_at TEXT NOT NULL,
                expires_at TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                certificate_url TEXT,
                scope TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_security_certifications_org ON security_certifications(org_id);
            """,
        ),
        (
            35,
            "create_tenant_configs",
            """
            CREATE TABLE IF NOT EXISTS tenant_configs (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL UNIQUE,
                org_id TEXT NOT NULL,
                config_key TEXT NOT NULL,
                config_value TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE,
                UNIQUE(tenant_id, config_key)
            );
            CREATE INDEX IF NOT EXISTS idx_tenant_configs_tenant ON tenant_configs(tenant_id);
            """,
        ),
        (
            36,
            "create_consent_records",
            """
            CREATE TABLE IF NOT EXISTS consent_records (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                consent_type TEXT NOT NULL,
                granted INTEGER NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_consent_records_user ON consent_records(user_id);
            CREATE INDEX IF NOT EXISTS idx_consent_records_type ON consent_records(consent_type);
            """,
        ),
        (
            37,
            "create_billing_events",
            """
            CREATE TABLE IF NOT EXISTS billing_events (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                user_id TEXT,
                event_type TEXT NOT NULL,
                amount REAL,
                currency TEXT DEFAULT 'USD',
                stripe_event_id TEXT,
                description TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_billing_events_org ON billing_events(org_id);
            CREATE INDEX IF NOT EXISTS idx_billing_events_type ON billing_events(event_type);
            """,
        ),
        (
            38,
            "create_api_keys",
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                user_id TEXT,
                name TEXT NOT NULL,
                key_hash TEXT NOT NULL,
                key_prefix TEXT NOT NULL,
                permissions TEXT,
                last_used_at TEXT,
                expires_at TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_api_keys_org ON api_keys(org_id);
            CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);
            """,
        ),
        (
            39,
            "create_roles",
            """
            CREATE TABLE IF NOT EXISTS roles (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                permissions TEXT NOT NULL DEFAULT '[]',
                is_system INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE,
                UNIQUE(org_id, name)
            );
            CREATE INDEX IF NOT EXISTS idx_roles_org ON roles(org_id);
            """,
        ),
        (
            40,
            "create_user_roles",
            """
            CREATE TABLE IF NOT EXISTS user_roles (
                id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role_id TEXT NOT NULL,
                assigned_by TEXT,
                assigned_at TEXT NOT NULL,
                expires_at TEXT,
                FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE,
                FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
                UNIQUE(org_id, user_id, role_id)
            );
            CREATE INDEX IF NOT EXISTS idx_user_roles_org ON user_roles(org_id);
            CREATE INDEX IF NOT EXISTS idx_user_roles_user ON user_roles(user_id);
            """,
        ),
    ]


def run_enterprise_migrations(conn: sqlite3.Connection) -> None:
    from .migration_runner import MigrationRunner
    runner = MigrationRunner(conn)
    migrations = get_enterprise_migrations()
    pending = runner.pending(migrations)
    if not pending:
        return
    for version, name, sql in pending:
        try:
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (version, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        except Exception as _e:  # noqa: BLE001
            pass
