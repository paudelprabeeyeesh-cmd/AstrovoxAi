-- ============================================
-- ASTRAVOX-AI Complete Database Schema
-- PostgreSQL + MongoDB Hybrid Architecture
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- CORE TABLES
-- ============================================

-- Users table (comprehensive)
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    uuid UUID DEFAULT gen_random_uuid() UNIQUE,
    
    -- Basic info
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    display_name VARCHAR(100),
    
    -- Profile
    avatar_url TEXT,
    cover_image_url TEXT,
    bio TEXT,
    website VARCHAR(255),
    location VARCHAR(255),
    timezone VARCHAR(50) DEFAULT 'UTC',
    language VARCHAR(10) DEFAULT 'en',
    
    -- Roles & Permissions
    role VARCHAR(50) DEFAULT 'user',
    permissions JSONB DEFAULT '[]',
    tier VARCHAR(50) DEFAULT 'free',
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    is_suspended BOOLEAN DEFAULT false,
    is_deleted BOOLEAN DEFAULT false,
    verification_token VARCHAR(255),
    password_reset_token VARCHAR(255),
    password_reset_expires TIMESTAMP,
    
    -- Preferences
    preferences JSONB DEFAULT '{
        "theme": "dark",
        "notifications": true,
        "emailNotifications": true,
        "pushNotifications": true,
        "twoFactorEnabled": false,
        "language": "en",
        "timezone": "UTC"
    }',
    
    -- AI Settings
    ai_preferences JSONB DEFAULT '{
        "defaultModel": "gpt4",
        "temperature": 0.7,
        "maxTokens": 2000,
        "voiceEnabled": true,
        "memoryEnabled": true
    }',
    
    -- Security
    two_factor_secret VARCHAR(255),
    backup_codes TEXT[],
    last_login_ip INET,
    last_login_at TIMESTAMP,
    login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

-- Indexes for users
CREATE INDEX idx_users_email ON users(email) WHERE is_deleted = false;
CREATE INDEX idx_users_username ON users(username) WHERE is_deleted = false;
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_tier ON users(tier);
CREATE INDEX idx_users_created_at ON users(created_at);

-- Sessions table (enhanced)
CREATE TABLE sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token VARCHAR(255) UNIQUE,
    
    -- Device info
    device_type VARCHAR(50),
    device_name VARCHAR(255),
    device_model VARCHAR(255),
    os VARCHAR(50),
    os_version VARCHAR(50),
    browser VARCHAR(50),
    browser_version VARCHAR(50),
    
    -- Location
    ip_address INET,
    city VARCHAR(100),
    country VARCHAR(100),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    
    -- Metadata
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP NOT NULL,
    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sessions_token ON sessions(session_token);
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);

-- User activity log
CREATE TABLE user_activity (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_activity_user ON user_activity(user_id);
CREATE INDEX idx_activity_action ON user_activity(action);
CREATE INDEX idx_activity_created ON user_activity(created_at);

-- ============================================
-- AI & CONVERSATION TABLES
-- ============================================

-- Conversations
CREATE TABLE conversations (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    summary TEXT,
    
    -- AI Configuration
    model VARCHAR(50) DEFAULT 'gpt-4',
    temperature DECIMAL(3, 2) DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 2000,
    system_prompt TEXT,
    
    -- Context
    context_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    
    -- Stats
    message_count INTEGER DEFAULT 0,
    token_count INTEGER DEFAULT 0,
    
    is_archived BOOLEAN DEFAULT false,
    is_deleted BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP
);

CREATE INDEX idx_conversations_user ON conversations(user_id);
CREATE INDEX idx_conversations_updated ON conversations(updated_at);
CREATE INDEX idx_conversations_context ON conversations(context_id);

-- Messages
CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT REFERENCES conversations(id) ON DELETE CASCADE,
    
    role VARCHAR(20) NOT NULL, -- user, assistant, system, tool
    content TEXT NOT NULL,
    
    -- AI Metadata
    model_used VARCHAR(50),
    tokens_used INTEGER,
    finish_reason VARCHAR(50),
    confidence DECIMAL(3, 2),
    
    -- References
    parent_message_id BIGINT,
    tool_calls JSONB,
    attachments JSONB,
    
    -- Reactions & Feedback
    user_rating INTEGER, -- 1-5
    user_feedback TEXT,
    
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_parent ON messages(parent_message_id);
CREATE INDEX idx_messages_created ON messages(created_at);

-- AI Agents
CREATE TABLE ai_agents (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    
    name VARCHAR(100) NOT NULL,
    description TEXT,
    avatar_url TEXT,
    
    -- Agent Configuration
    model VARCHAR(50) NOT NULL,
    system_prompt TEXT NOT NULL,
    temperature DECIMAL(3, 2) DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 2000,
    
    -- Capabilities
    tools JSONB DEFAULT '[]',
    knowledge_base_ids BIGINT[],
    
    -- Personality
    personality_traits JSONB,
    communication_style VARCHAR(50),
    
    is_active BOOLEAN DEFAULT true,
    is_public BOOLEAN DEFAULT false,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_agents_user ON ai_agents(user_id);
CREATE INDEX idx_agents_active ON ai_agents(is_active);
CREATE INDEX idx_agents_public ON ai_agents(is_public);

-- Vector Embeddings (MongoDB alternative - PostgreSQL with pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE embeddings (
    id BIGSERIAL PRIMARY KEY,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(255) NOT NULL,
    embedding VECTOR(1536),
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_embeddings_resource ON embeddings(resource_type, resource_id);
CREATE INDEX idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops);

-- ============================================
-- SUBSCRIPTION & PAYMENT TABLES
-- ============================================

-- Subscriptions
CREATE TABLE subscriptions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    
    -- Plan details
    plan_name VARCHAR(50) NOT NULL,
    plan_tier VARCHAR(50) NOT NULL,
    interval VARCHAR(20), -- monthly, yearly, lifetime
    
    -- Pricing
    amount DECIMAL(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Status
    status VARCHAR(50) NOT NULL, -- active, cancelled, expired, trialing
    is_trialing BOOLEAN DEFAULT false,
    trial_ends_at TIMESTAMP,
    
    -- Dates
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    cancelled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- External references
    stripe_subscription_id VARCHAR(255),
    paypal_subscription_id VARCHAR(255),
    paddle_subscription_id VARCHAR(255)
);

CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_stripe ON subscriptions(stripe_subscription_id);

-- Payments
CREATE TABLE payments (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    subscription_id BIGINT REFERENCES subscriptions(id),
    
    -- Payment details
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(50) NOT NULL, -- pending, succeeded, failed, refunded
    
    -- Payment method
    payment_method VARCHAR(50),
    payment_provider VARCHAR(50), -- stripe, paypal, crypto
    
    -- Description
    description TEXT,
    invoice_url TEXT,
    
    -- Metadata
    metadata JSONB,
    
    -- External references
    provider_payment_id VARCHAR(255),
    provider_invoice_id VARCHAR(255),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    refunded_at TIMESTAMP
);

CREATE INDEX idx_payments_user ON payments(user_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_provider ON payments(provider_payment_id);

-- ============================================
-- NOTIFICATION & MESSAGING TABLES
-- ============================================

-- Notifications
CREATE TABLE notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT,
    
    -- Action
    action_url TEXT,
    action_label VARCHAR(100),
    
    -- Status
    is_read BOOLEAN DEFAULT false,
    is_delivered BOOLEAN DEFAULT false,
    read_at TIMESTAMP,
    
    -- Priority
    priority INTEGER DEFAULT 0,
    
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(is_read);
CREATE INDEX idx_notifications_created ON notifications(created_at);

-- Push notification tokens
CREATE TABLE push_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    
    token VARCHAR(255) NOT NULL,
    platform VARCHAR(20) NOT NULL, -- web, ios, android
    device_id VARCHAR(255),
    
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, token)
);

-- ============================================
-- ANALYTICS & METRICS TABLES
-- ============================================

-- User events (for analytics)
CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    session_id VARCHAR(255),
    
    event_name VARCHAR(100) NOT NULL,
    event_category VARCHAR(50),
    event_action VARCHAR(50),
    event_label VARCHAR(255),
    
    -- Values
    numeric_value DECIMAL(10, 2),
    string_value TEXT,
    
    -- Context
    page_url TEXT,
    referrer TEXT,
    ip_address INET,
    user_agent TEXT,
    
    -- Device info
    device_type VARCHAR(50),
    browser VARCHAR(50),
    os VARCHAR(50),
    
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_events_user ON events(user_id);
CREATE INDEX idx_events_name ON events(event_name);
CREATE INDEX idx_events_created ON events(created_at);
CREATE INDEX idx_events_session ON events(session_id);

-- Daily metrics aggregations
CREATE TABLE daily_metrics (
    id BIGSERIAL PRIMARY KEY,
    metric_date DATE NOT NULL,
    
    -- User metrics
    total_users INTEGER,
    new_users INTEGER,
    active_users INTEGER,
    
    -- AI metrics
    total_conversations INTEGER,
    total_messages INTEGER,
    total_tokens_used BIGINT,
    avg_response_time DECIMAL(10, 2),
    
    -- Revenue metrics
    total_revenue DECIMAL(10, 2),
    new_subscriptions INTEGER,
    churned_users INTEGER,
    
    -- System metrics
    api_calls INTEGER,
    error_count INTEGER,
    avg_load_time DECIMAL(10, 2),
    
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(metric_date)
);

CREATE INDEX idx_metrics_date ON daily_metrics(metric_date);

-- ============================================
-- SYSTEM TABLES
-- ============================================

-- API rate limits
CREATE TABLE rate_limits (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    api_key VARCHAR(255),
    endpoint VARCHAR(255),
    
    requests INTEGER DEFAULT 0,
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, api_key, endpoint, window_start)
);

-- Webhook delivery logs
CREATE TABLE webhook_logs (
    id BIGSERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    payload JSONB,
    result JSONB,
    error TEXT,
    ip_address INET,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_webhook_provider ON webhook_logs(provider);
CREATE INDEX idx_webhook_created ON webhook_logs(created_at);

-- Audit logs
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_created ON audit_logs(created_at);

-- ============================================
-- TRIGGERS & FUNCTIONS
-- ============================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_ai_agents_updated_at BEFORE UPDATE ON ai_agents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Update conversation message count
CREATE OR REPLACE FUNCTION update_conversation_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE conversations 
        SET message_count = message_count + 1,
            last_message_at = NEW.created_at
        WHERE id = NEW.conversation_id;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_conversation_stats_trigger
AFTER INSERT ON messages
FOR EACH ROW
EXECUTE FUNCTION update_conversation_stats();

-- ============================================
-- VIEWS FOR COMMON QUERIES
-- ============================================

-- Active users view
CREATE VIEW active_users_view AS
SELECT 
    u.id,
    u.uuid,
    u.username,
    u.email,
    u.full_name,
    u.role,
    u.tier,
    u.last_login_at,
    COUNT(DISTINCT s.id) as session_count,
    COUNT(DISTINCT c.id) as conversation_count
FROM users u
LEFT JOIN sessions s ON u.id = s.user_id AND s.is_active = true
LEFT JOIN conversations c ON u.id = c.user_id AND c.is_deleted = false
WHERE u.is_active = true AND u.is_deleted = false
GROUP BY u.id;

-- User subscription summary view
CREATE VIEW user_subscription_summary AS
SELECT 
    u.id,
    u.username,
    u.email,
    s.plan_name,
    s.plan_tier,
    s.status as subscription_status,
    s.current_period_end,
    COUNT(p.id) as total_payments,
    SUM(p.amount) as total_spent
FROM users u
LEFT JOIN subscriptions s ON u.id = s.user_id AND s.status = 'active'
LEFT JOIN payments p ON u.id = p.user_id AND p.status = 'succeeded'
WHERE u.is_deleted = false
GROUP BY u.id, s.id;