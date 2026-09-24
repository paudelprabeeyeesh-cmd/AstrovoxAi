from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user")
    email_verified = Column(Integer, default=0)
    plan = Column(String, default="free")
    stripe_customer_id = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id = Column(String, primary_key=True)
    ip = Column(String, nullable=False)
    success = Column(Integer, default=0)
    lockout_until = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False)
    expires_at = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Memory(Base):
    __tablename__ = "memories"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False)
    embedding = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Template(Base):
    __tablename__ = "templates"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    prompt = Column(String, nullable=False)
    variables = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    template_id = Column(String)
    cron = Column(String, nullable=False)
    email = Column(String, nullable=False)
    last_run = Column(DateTime)
    active = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())


class KnowledgeDoc(Base):
    __tablename__ = "knowledge_docs"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String)
    content = Column(String, nullable=False)
    embedding = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class UserProfile(Base):
    __tablename__ = "user_profiles"
    user_id = Column(String, primary_key=True)
    style_json = Column(String)
    updated_at = Column(DateTime, server_default=func.now())


class Workflow(Base):
    __tablename__ = "workflows"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    steps = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Tool(Base):
    __tablename__ = "tools"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)
    config = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Feedback(Base):
    __tablename__ = "feedback"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    request_id = Column(String)
    rating = Column(Integer)
    comment = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class ABTest(Base):
    __tablename__ = "ab_tests"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    variants = Column(String, nullable=False)
    traffic_split = Column(Float, nullable=False)
    active = Column(Integer, default=1)


class ABAssignment(Base):
    __tablename__ = "ab_assignments"
    id = Column(String, primary_key=True)
    test_id = Column(String, ForeignKey("ab_tests.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    variant = Column(String, nullable=False)


class Usage(Base):
    __tablename__ = "usage"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    tokens = Column(Integer, nullable=False)
    cost = Column(Float, nullable=False)
    model = Column(String, nullable=False)
    cached = Column(Integer, default=0)
    error = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    plan = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    stripe_customer_id = Column(String)
    stripe_subscription_id = Column(String)
    status = Column(String, default="active")
    created_at = Column(DateTime, server_default=func.now())


class Team(Base):
    __tablename__ = "teams"
    id = Column(String, primary_key=True)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class TeamMember(Base):
    __tablename__ = "team_members"
    id = Column(String, primary_key=True)
    team_id = Column(String, ForeignKey("teams.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    role = Column(String, default="member")
    created_at = Column(DateTime, server_default=func.now())


class APIKey(Base):
    __tablename__ = "api_keys"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    key_hash = Column(String, nullable=False)
    name = Column(String)
    last_used = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


class MarketplacePrompt(Base):
    __tablename__ = "marketplace_prompts"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    prompt = Column(String, nullable=False)
    price = Column(Float, default=0)
    downloads = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class Addon(Base):
    __tablename__ = "addons"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    stripe_price_id = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class IPOMetric(Base):
    __tablename__ = "ipo_metrics"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    target = Column(String, nullable=False)
    current = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Referral(Base):
    __tablename__ = "referrals"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    code = Column(String, unique=True, nullable=False)
    email = Column(String, nullable=False)
    signup_user_id = Column(String)
    signup_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


class Integration(Base):
    __tablename__ = "integrations"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)
    config = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Post(Base):
    __tablename__ = "posts"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    author = Column(String, default="founder")
    created_at = Column(DateTime, server_default=func.now())


class Comment(Base):
    __tablename__ = "comments"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    post_id = Column(String, ForeignKey("posts.id"), nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class AMA(Base):
    __tablename__ = "amas"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String)
    scheduled_at = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class CaseStudy(Base):
    __tablename__ = "case_studies"
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Outreach(Base):
    __tablename__ = "outreach"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    template_name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(String, nullable=False)
    recipient_email = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class AdCampaign(Base):
    __tablename__ = "ad_campaigns"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    budget = Column(Float, nullable=False)
    start_date = Column(String, nullable=False)
    end_date = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Affiliate(Base):
    __tablename__ = "affiliates"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    code = Column(String, unique=True, nullable=False)
    conversions = Column(Integer, default=0)
    revenue = Column(Float, default=0)
    created_at = Column(DateTime, server_default=func.now())


class EnterpriseAccount(Base):
    __tablename__ = "enterprise_accounts"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    company = Column(String, nullable=False)
    contact_email = Column(String, nullable=False)
    plan = Column(String, default="enterprise")
    created_at = Column(DateTime, server_default=func.now())


class EnterpriseAuditLog(Base):
    __tablename__ = "enterprise_audit_logs"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    metadata = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    metadata = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class SLA(Base):
    __tablename__ = "slas"
    id = Column(String, primary_key=True)
    account_id = Column(String, ForeignKey("users.id"), nullable=False)
    tier = Column(String, nullable=False)
    uptime_guarantee = Column(Float, nullable=False)
    response_time_hours = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class CustomModel(Base):
    __tablename__ = "custom_models"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    config = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Vertical(Base):
    __tablename__ = "verticals"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    config = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Region(Base):
    __tablename__ = "regions"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)
    config = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class SDKKey(Base):
    __tablename__ = "sdk_keys"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    key_hash = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class MATarget(Base):
    __tablename__ = "ma_targets"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    valuation = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Interaction(Base):
    __tablename__ = "interactions"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    prompt = Column(String, nullable=False)
    response = Column(String, nullable=False)
    model = Column(String, nullable=False)
    tokens = Column(Integer, nullable=False)
    cost = Column(Float, nullable=False)
    latency_ms = Column(Integer)
    rating = Column(Integer)
    correction = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class InteractionLabel(Base):
    __tablename__ = "interaction_labels"
    id = Column(String, primary_key=True)
    interaction_id = Column(String, ForeignKey("interactions.id"), nullable=False)
    label = Column(String, nullable=False)
    notes = Column(String)
    labeled_by = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class StripeEvent(Base):
    __tablename__ = "stripe_events"
    event_id = Column(String, primary_key=True)
    event_type = Column(String, nullable=False)
    processed_at = Column(DateTime, server_default=func.now())


class ConsentRecord(Base):
    __tablename__ = "consent_records"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    consent_type = Column(String, nullable=False)
    granted = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"
    id = Column(String, primary_key=True)
    event_type = Column(String, nullable=False)
    properties = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class RAGEvaluation(Base):
    __tablename__ = "rag_evaluations"
    id = Column(String, primary_key=True)
    query = Column(String, nullable=False)
    retrieved_ids = Column(String, nullable=False)
    golden_ids = Column(String, nullable=False)
    recall_at_5 = Column(Float, nullable=False)
    faithfulness_score = Column(Float, nullable=False)
    metadata = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class Experiment(Base):
    __tablename__ = "experiments"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    hypothesis = Column(String, nullable=False)
    variants = Column(String, nullable=False)
    traffic_split = Column(String, nullable=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="active")
    created_at = Column(DateTime, server_default=func.now())


class ExperimentAssignment(Base):
    __tablename__ = "experiment_assignments"
    id = Column(String, primary_key=True)
    experiment_id = Column(String, ForeignKey("experiments.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    variant = Column(String, nullable=False)


class ExperimentResult(Base):
    __tablename__ = "experiment_results"
    id = Column(String, primary_key=True)
    experiment_id = Column(String, ForeignKey("experiments.id"), nullable=False)
    variant = Column(String, nullable=False)
    metric = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    user_id = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())


class Organization(Base):
    __tablename__ = "organizations"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    id = Column(String, primary_key=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False)
    joined_at = Column(DateTime, server_default=func.now())


class Workspace(Base):
    __tablename__ = "workspaces"
    id = Column(String, primary_key=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    id = Column(String, primary_key=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False)
    joined_at = Column(DateTime, server_default=func.now())


class Invitation(Base):
    __tablename__ = "invitations"
    id = Column(String, primary_key=True)
    email = Column(String, nullable=False)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    invited_by = Column(String, ForeignKey("users.id"), nullable=False)
    token = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class SSOConnection(Base):
    __tablename__ = "sso_connections"
    id = Column(String, primary_key=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    provider = Column(String, nullable=False)
    config = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class SSOUser(Base):
    __tablename__ = "sso_users"
    id = Column(String, primary_key=True)
    sso_connection_id = Column(String, ForeignKey("sso_connections.id"), nullable=False)
    email = Column(String, nullable=False)
    name = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class KnowledgeEntity(Base):
    __tablename__ = "knowledge_entities"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    data = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class KnowledgeRelationship(Base):
    __tablename__ = "knowledge_relationships"
    id = Column(String, primary_key=True)
    source_id = Column(String, ForeignKey("knowledge_entities.id"), nullable=False)
    target_id = Column(String, ForeignKey("knowledge_entities.id"), nullable=False)
    relationship_type = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Role(Base):
    __tablename__ = "roles"
    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class Permission(Base):
    __tablename__ = "permissions"
    id = Column(String, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class UserRole(Base):
    __tablename__ = "user_roles"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    role_id = Column(String, ForeignKey("roles.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class RolePermission(Base):
    __tablename__ = "role_permissions"
    id = Column(String, primary_key=True)
    role_id = Column(String, ForeignKey("roles.id"), nullable=False)
    permission_id = Column(String, ForeignKey("permissions.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class File(Base):
    __tablename__ = "files"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    path = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    content = Column(String, nullable=False)
    version = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    embedding = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    content = Column(String, nullable=False)
    embedding = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


Index("idx_memories_user", Memory.user_id)
Index("idx_messages_conversation", Message.conversation_id)
Index("idx_conversations_user", Conversation.user_id)
Index("idx_templates_user", Template.user_id)
Index("idx_schedules_user", Schedule.user_id)
Index("idx_knowledge_user", KnowledgeDoc.user_id)
Index("idx_workflows_user", Workflow.user_id)
Index("idx_tools_user", Tool.user_id)
Index("idx_feedback_user", Feedback.user_id)
Index("idx_usage_user", Usage.user_id)
Index("idx_subscriptions_user", Subscription.user_id)
Index("idx_teams_user", Team.owner_id)
Index("idx_team_members_team", TeamMember.team_id)
Index("idx_api_keys_user", APIKey.user_id)
Index("idx_marketplace_user", MarketplacePrompt.user_id)
Index("idx_addons_user", Addon.user_id)
Index("idx_audit_user", AuditLog.user_id)
Index("idx_referrals_user", Referral.user_id)
Index("idx_referrals_code", Referral.code)
Index("idx_integrations_user", Integration.user_id)
Index("idx_comments_post", Comment.post_id)
Index("idx_amas_scheduled", AMA.scheduled_at)
Index("idx_case_studies_user", CaseStudy.user_id)
Index("idx_outreach_user", Outreach.user_id)
Index("idx_campaigns_dates", AdCampaign.start_date, AdCampaign.end_date)
Index("idx_affiliates_code", Affiliate.code)
Index("idx_enterprise_audit_user", EnterpriseAuditLog.user_id)
Index("idx_slas_account", SLA.account_id)
Index("idx_custom_models_user", CustomModel.user_id)
Index("idx_verticals_name", Vertical.name)
Index("idx_regions_code", Region.code)
Index("idx_sdk_keys_user", SDKKey.user_id)
Index("idx_ma_targets_name", MATarget.name)
Index("idx_ipo_metrics_name", IPOMetric.name)
Index("idx_interactions_user", Interaction.user_id)
Index("idx_posts_user", Post.user_id)
Index("idx_stripe_events_event_id", StripeEvent.event_id)
Index("idx_analytics_events_type", AnalyticsEvent.event_type)
Index("idx_rag_evaluations_query", RAGEvaluation.query)
Index("idx_experiments_owner", Experiment.owner_id)
Index("idx_experiment_results_exp", ExperimentResult.experiment_id)