/**
 * Real-time Sync Engine
 * Synchronizes data across all services in real-time
 */

const { EventEmitter } = require('events');
const { logger } = require('../utils/logger');
const Redis = require('ioredis');
const WebSocket = require('ws');

class RealTimeSyncEngine extends EventEmitter {
    constructor() {
        super();
        this.connections = new Map();
        this.channels = new Map();
        this.syncQueues = new Map();
        this.pubClient = null;
        this.subClient = null;
        this.initialized = false;
    }

    async initialize() {
        this.pubClient = new Redis({
            host: process.env.REDIS_HOST,
            port: process.env.REDIS_PORT,
            password: process.env.REDIS_PASSWORD,
            retryStrategy: (times) => Math.min(times * 50, 2000)
        });

        this.subClient = this.pubClient.duplicate();

        await this.subClient.subscribe('sync:global', 'sync:presence', 'sync:data', 'sync:ai', 'sync:notifications');
        
        this.subClient.on('message', (channel, message) => {
            this.handleMessage(channel, JSON.parse(message));
        });

        this.initialized = true;
        logger.info('Real-time Sync Engine initialized');
        
        return this;
    }

    handleMessage(channel, message) {
        switch (channel) {
            case 'sync:global':
                this.handleGlobalSync(message);
                break;
            case 'sync:presence':
                this.handlePresenceUpdate(message);
                break;
            case 'sync:data':
                this.handleDataSync(message);
                break;
            case 'sync:ai':
                this.handleAISync(message);
                break;
            case 'sync:notifications':
                this.handleNotificationSync(message);
                break;
        }
    }

    async syncUserData(userId, data, targetServices = []) {
        const syncMessage = {
            id: crypto.randomUUID(),
            userId,
            data,
            targetServices,
            timestamp: Date.now(),
            type: 'user_data_sync'
        };

        await this.pubClient.publish('sync:data', JSON.stringify(syncMessage));
        
        // Store in sync queue for retry
        if (!this.syncQueues.has(userId)) {
            this.syncQueues.set(userId, []);
        }
        this.syncQueues.get(userId).push(syncMessage);
        
        return syncMessage.id;
    }

    async syncAIContext(contextId, contextData, agents = []) {
        const syncMessage = {
            id: crypto.randomUUID(),
            contextId,
            contextData,
            agents,
            timestamp: Date.now(),
            type: 'ai_context_sync'
        };

        await this.pubClient.publish('sync:ai', JSON.stringify(syncMessage));
        
        // Broadcast to connected WebSocket clients
        this.broadcastToChannel('ai_context', syncMessage);
        
        return syncMessage.id;
    }

    async syncPresence(userId, status, metadata = {}) {
        const presenceMessage = {
            userId,
            status,
            metadata,
            timestamp: Date.now(),
            type: 'presence_update'
        };

        await this.pubClient.publish('sync:presence', JSON.stringify(presenceMessage));
        this.broadcastToChannel('presence', presenceMessage);
        
        return presenceMessage;
    }

    async syncNotification(userId, notification) {
        const notificationMessage = {
            userId,
            notification: {
                ...notification,
                id: crypto.randomUUID(),
                timestamp: Date.now()
            },
            type: 'notification_sync'
        };

        await this.pubClient.publish('sync:notifications', JSON.stringify(notificationMessage));
        
        // Direct push to user's WebSocket connection
        const userConnection = this.connections.get(userId);
        if (userConnection && userConnection.ws.readyState === WebSocket.OPEN) {
            userConnection.ws.send(JSON.stringify(notificationMessage));
        }
        
        return notificationMessage;
    }

    registerWebSocket(ws, userId) {
        this.connections.set(userId, {
            ws,
            connectedAt: Date.now(),
            channels: new Set(['global', 'presence'])
        });

        ws.on('message', async (message) => {
            const data = JSON.parse(message);
            await this.handleWebSocketMessage(userId, data);
        });

        ws.on('close', () => {
            this.connections.delete(userId);
            this.syncPresence(userId, 'offline');
        });

        this.syncPresence(userId, 'online');
        
        // Send initial sync data
        this.sendInitialSync(ws, userId);
    }

    async handleWebSocketMessage(userId, message) {
        switch (message.type) {
            case 'subscribe':
                this.subscribeToChannel(userId, message.channel);
                break;
            case 'unsubscribe':
                this.unsubscribeFromChannel(userId, message.channel);
                break;
            case 'sync_request':
                await this.handleSyncRequest(userId, message);
                break;
            case 'action':
                await this.handleAction(userId, message);
                break;
        }
    }

    subscribeToChannel(userId, channel) {
        const connection = this.connections.get(userId);
        if (connection) {
            connection.channels.add(channel);
            
            if (!this.channels.has(channel)) {
                this.channels.set(channel, new Set());
            }
            this.channels.get(channel).add(userId);
        }
    }

    unsubscribeFromChannel(userId, channel) {
        const connection = this.connections.get(userId);
        if (connection) {
            connection.channels.delete(channel);
            
            const channelUsers = this.channels.get(channel);
            if (channelUsers) {
                channelUsers.delete(userId);
                if (channelUsers.size === 0) {
                    this.channels.delete(channel);
                }
            }
        }
    }

    broadcastToChannel(channel, message, excludeUserId = null) {
        const channelUsers = this.channels.get(channel);
        if (!channelUsers) return;
        
        for (const userId of channelUsers) {
            if (userId === excludeUserId) continue;
            
            const connection = this.connections.get(userId);
            if (connection && connection.ws.readyState === WebSocket.OPEN) {
                connection.ws.send(JSON.stringify(message));
            }
        }
    }

    async sendInitialSync(ws, userId) {
        const initialData = {
            type: 'initial_sync',
            timestamp: Date.now(),
            data: {
                user: await this.getUserData(userId),
                presence: await this.getAllPresence(),
                notifications: await this.getUserNotifications(userId),
                aiContext: await this.getAIContext(userId)
            }
        };
        
        ws.send(JSON.stringify(initialData));
    }

    async getUserData(userId) {
        // Fetch from PostgreSQL
        const { getPostgresPool } = require('../config/db');
        const pool = getPostgresPool();
        const result = await pool.query('SELECT * FROM users WHERE id = $1', [userId]);
        return result.rows[0];
    }

    async getAllPresence() {
        const presence = [];
        for (const [userId, connection] of this.connections) {
            presence.push({
                userId,
                status: 'online',
                lastSeen: connection.connectedAt
            });
        }
        return presence;
    }

    async getUserNotifications(userId) {
        // Fetch from Redis or database
        return [];
    }

    async getAIContext(userId) {
        // Fetch from vector database
        return {};
    }

    async handleSyncRequest(userId, request) {
        // Handle specific sync requests from client
        switch (request.target) {
            case 'messages':
                await this.syncMessages(userId, request);
                break;
            case 'conversations':
                await this.syncConversations(userId, request);
                break;
            case 'agents':
                await this.syncAgents(userId, request);
                break;
        }
    }

    async syncMessages(userId, request) {
        // Implement message sync logic
    }

    async syncConversations(userId, request) {
        // Implement conversation sync logic
    }

    async syncAgents(userId, request) {
        // Implement agent sync logic
    }

    async handleAction(userId, action) {
        // Handle real-time actions
        switch (action.action) {
            case 'typing':
                this.handleTypingIndicator(userId, action);
                break;
            case 'read_receipt':
                this.handleReadReceipt(userId, action);
                break;
            case 'reaction':
                this.handleReaction(userId, action);
                break;
        }
    }

    handleTypingIndicator(userId, action) {
        const message = {
            type: 'typing',
            userId,
            conversationId: action.conversationId,
            isTyping: action.isTyping,
            timestamp: Date.now()
        };
        
        this.broadcastToChannel(`conversation:${action.conversationId}`, message);
    }

    handleReadReceipt(userId, action) {
        const message = {
            type: 'read_receipt',
            userId,
            messageId: action.messageId,
            timestamp: Date.now()
        };
        
        this.broadcastToChannel(`conversation:${action.conversationId}`, message);
    }

    handleReaction(userId, action) {
        const message = {
            type: 'reaction',
            userId,
            messageId: action.messageId,
            reaction: action.reaction,
            timestamp: Date.now()
        };
        
        this.broadcastToChannel(`conversation:${action.conversationId}`, message);
    }

    handleGlobalSync(message) {
        this.broadcastToChannel('global', message);
    }

    handleDataSync(message) {
        // Route data sync to appropriate handlers
        if (message.targetServices && message.targetServices.length > 0) {
            for (const service of message.targetServices) {
                this.routeToService(service, message);
            }
        }
    }

    handleAISync(message) {
        this.broadcastToChannel('ai_updates', message);
        this.emit('ai_sync', message);
    }

    handleNotificationSync(message) {
        const userConnection = this.connections.get(message.userId);
        if (userConnection) {
            userConnection.ws.send(JSON.stringify(message));
        }
    }

    handlePresenceUpdate(message) {
        this.broadcastToChannel('presence', message, message.userId);
        this.emit('presence_update', message);
    }

    routeToService(service, message) {
        // Route sync messages to specific services
        switch (service) {
            case 'elasticsearch':
                this.syncToElasticsearch(message);
                break;
            case 'algolia':
                this.syncToAlgolia(message);
                break;
            case 'redis':
                this.syncToRedis(message);
                break;
        }
    }

    async syncToElasticsearch(message) {
        // Implement Elasticsearch sync
    }

    async syncToAlgolia(message) {
        // Implement Algolia sync
    }

    async syncToRedis(message) {
        // Implement Redis sync
    }

    getConnectionStats() {
        return {
            totalConnections: this.connections.size,
            activeChannels: this.channels.size,
            syncQueueSize: Array.from(this.syncQueues.values()).reduce((acc, queue) => acc + queue.length, 0)
        };
    }
}

module.exports = new RealTimeSyncEngine();