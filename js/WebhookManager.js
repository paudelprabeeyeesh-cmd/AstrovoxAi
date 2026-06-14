/**
 * Universal Webhook Manager
 * Handles incoming webhooks from all external services
 */

const crypto = require('crypto');
const { logger } = require('../utils/logger');

class WebhookManager {
    constructor() {
        this.webhooks = new Map();
        this.webhookHistory = [];
        this.initializeWebhookHandlers();
    }

    initializeWebhookHandlers() {
        // Stripe Webhooks
        this.registerWebhook('stripe', {
            secret: process.env.STRIPE_WEBHOOK_SECRET,
            handler: async (event) => {
                switch (event.type) {
                    case 'payment_intent.succeeded':
                        await this.handlePaymentSuccess(event.data.object);
                        break;
                    case 'customer.subscription.created':
                        await this.handleSubscriptionCreated(event.data.object);
                        break;
                    case 'invoice.payment_failed':
                        await this.handlePaymentFailed(event.data.object);
                        break;
                }
            }
        });

        // GitHub Webhooks
        this.registerWebhook('github', {
            secret: process.env.GITHUB_WEBHOOK_SECRET,
            handler: async (event) => {
                const action = event.headers['x-github-event'];
                switch (action) {
                    case 'push':
                        await this.handleGitPush(event.body);
                        break;
                    case 'pull_request':
                        await this.handlePullRequest(event.body);
                        break;
                }
            }
        });

        // Slack Webhooks
        this.registerWebhook('slack', {
            secret: process.env.SLACK_SIGNING_SECRET,
            handler: async (event) => {
                await this.handleSlackCommand(event.body);
            }
        });

        // Discord Webhooks
        this.registerWebhook('discord', {
            secret: process.env.DISCORD_PUBLIC_KEY,
            handler: async (event) => {
                await this.handleDiscordInteraction(event.body);
            }
        });

        // Twilio Webhooks
        this.registerWebhook('twilio', {
            secret: process.env.TWILIO_AUTH_TOKEN,
            handler: async (event) => {
                const { Body, From } = event.body;
                await this.handleSMS(Body, From);
            }
        });

        // SendGrid Webhooks
        this.registerWebhook('sendgrid', {
            secret: process.env.SENDGRID_WEBHOOK_SECRET,
            handler: async (event) => {
                const events = event.body;
                for (const ev of events) {
                    await this.handleEmailEvent(ev);
                }
            }
        });

        // Algolia Webhooks
        this.registerWebhook('algolia', {
            secret: process.env.ALGOLIA_WEBHOOK_SECRET,
            handler: async (event) => {
                await this.handleSearchEvent(event.body);
            }
        });

        // Mixpanel Webhooks
        this.registerWebhook('mixpanel', {
            secret: process.env.MIXPANEL_WEBHOOK_SECRET,
            handler: async (event) => {
                await this.handleAnalyticsEvent(event.body);
            }
        });

        // Zapier Webhooks
        this.registerWebhook('zapier', {
            secret: process.env.ZAPIER_WEBHOOK_SECRET,
            handler: async (event) => {
                await this.handleZapierAction(event.body);
            }
        });

        // Paddle Webhooks
        this.registerWebhook('paddle', {
            secret: process.env.PADDLE_WEBHOOK_SECRET,
            handler: async (event) => {
                await this.handlePaddleEvent(event.body);
            }
        });

        // RevenueCat Webhooks
        this.registerWebhook('revenuecat', {
            secret: process.env.REVENUECAT_WEBHOOK_SECRET,
            handler: async (event) => {
                await this.handleSubscriptionEvent(event.body);
            }
        });
    }

    registerWebhook(provider, config) {
        this.webhooks.set(provider, config);
        logger.info(`Registered webhook handler for ${provider}`);
    }

    async processWebhook(provider, request) {
        const webhook = this.webhooks.get(provider);
        
        if (!webhook) {
            logger.error(`No webhook handler found for ${provider}`);
            return { success: false, error: 'Unknown provider' };
        }

        // Verify signature
        const signature = request.headers['x-signature'] || request.headers['stripe-signature'];
        if (webhook.secret && !this.verifySignature(request.body, signature, webhook.secret)) {
            logger.error(`Invalid signature for ${provider} webhook`);
            return { success: false, error: 'Invalid signature' };
        }

        // Process webhook
        try {
            const result = await webhook.handler(request);
            this.logWebhook(provider, request, result);
            return { success: true, result };
        } catch (error) {
            logger.error(`Webhook processing failed for ${provider}:`, error);
            this.logWebhook(provider, request, null, error);
            return { success: false, error: error.message };
        }
    }

    verifySignature(payload, signature, secret) {
        try {
            const expectedSignature = crypto
                .createHmac('sha256', secret)
                .update(JSON.stringify(payload))
                .digest('hex');
            return crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expectedSignature));
        } catch (error) {
            return false;
        }
    }

    async handlePaymentSuccess(paymentIntent) {
        logger.info(`Payment succeeded: ${paymentIntent.id}`);
        // Update database, send confirmation email, trigger fulfillment
    }

    async handleSubscriptionCreated(subscription) {
        logger.info(`Subscription created: ${subscription.id}`);
        // Provision access, send welcome email, track analytics
    }

    async handlePaymentFailed(invoice) {
        logger.warn(`Payment failed for customer: ${invoice.customer}`);
        // Send dunning email, retry payment, update account status
    }

    async handleGitPush(pushEvent) {
        logger.info(`Git push to ${pushEvent.repository.full_name}`);
        // Trigger CI/CD, update deployment, notify team
    }

    async handlePullRequest(prEvent) {
        logger.info(`PR ${prEvent.pull_request.number}: ${prEvent.action}`);
        // Run automated tests, request reviews, update checks
    }

    async handleSlackCommand(command) {
        logger.info(`Slack command: ${command.command}`);
        // Execute custom commands, respond to user
    }

    async handleDiscordInteraction(interaction) {
        logger.info(`Discord interaction: ${interaction.type}`);
        // Handle slash commands, buttons, modals
    }

    async handleSMS(message, from) {
        logger.info(`SMS from ${from}: ${message.substring(0, 50)}`);
        // Process SMS, trigger AI response, update ticket
    }

    async handleEmailEvent(event) {
        logger.info(`Email event: ${event.event} for ${event.email}`);
        // Track opens, clicks, bounces, update analytics
    }

    async handleSearchEvent(event) {
        logger.info(`Search event: ${event.eventName}`);
        // Update search analytics, improve relevance
    }

    async handleAnalyticsEvent(event) {
        logger.info(`Analytics event: ${event.event}`);
        // Process real-time analytics, update dashboards
    }

    async handleZapierAction(action) {
        logger.info(`Zapier action: ${action.actionName}`);
        // Trigger automation workflows
    }

    async handlePaddleEvent(event) {
        logger.info(`Paddle event: ${event.alert_name}`);
        // Process payment, subscription changes
    }

    async handleSubscriptionEvent(event) {
        logger.info(`RevenueCat event: ${event.type}`);
        // Update subscription status, manage entitlements
    }

    logWebhook(provider, request, result, error = null) {
        const logEntry = {
            provider,
            timestamp: new Date().toISOString(),
            headers: request.headers,
            body: request.body,
            result,
            error: error?.message,
            ip: request.ip
        };
        
        this.webhookHistory.push(logEntry);
        
        // Keep only last 1000 entries
        if (this.webhookHistory.length > 1000) {
            this.webhookHistory.shift();
        }
        
        // Store in database for audit
        this.storeWebhookLog(logEntry);
    }

    async storeWebhookLog(logEntry) {
        try {
            // Store in PostgreSQL for audit trail
            const { getPostgresPool } = require('../config/db');
            const pool = getPostgresPool();
            
            await pool.query(
                `INSERT INTO webhook_logs (provider, payload, result, error, ip_address, created_at)
                 VALUES ($1, $2, $3, $4, $5, $6)`,
                [logEntry.provider, JSON.stringify(logEntry.body), logEntry.result, logEntry.error, logEntry.ip, logEntry.timestamp]
            );
        } catch (error) {
            logger.error('Failed to store webhook log:', error);
        }
    }

    getWebhookHistory(provider = null, limit = 100) {
        if (provider) {
            return this.webhookHistory.filter(log => log.provider === provider).slice(0, limit);
        }
        return this.webhookHistory.slice(0, limit);
    }
}

module.exports = new WebhookManager();