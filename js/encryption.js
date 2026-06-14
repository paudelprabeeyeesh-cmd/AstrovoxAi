// ============================================
// PRABESH PAUDEL — SECURITY CONTROLLER
// Security Controller | Input Validation
// ============================================

class SecurityManager {
    constructor() {
        this.saltRounds = 12;
        this.blacklistedPatterns = [
            /<script/i,
            /javascript:/i,
            /onerror=/i,
            /onload=/i,
            /eval\(/i
        ];
    }
    
    sanitizeInput(input) {
        if (typeof input !== 'string') return '';
        
        let sanitized = input;
        
        // Remove HTML tags
        sanitized = sanitized.replace(/<[^>]*>/g, '');
        
        // Remove script patterns
        for (const pattern of this.blacklistedPatterns) {
            sanitized = sanitized.replace(pattern, '');
        }
        
        // Escape special characters
        sanitized = sanitized
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
        
        return sanitized;
    }
    
    validateEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    validatePassword(password) {
        const minLength = 8;
        const hasUpperCase = /[A-Z]/.test(password);
        const hasLowerCase = /[a-z]/.test(password);
        const hasNumbers = /\d/.test(password);
        const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);
        
        return {
            isValid: password.length >= minLength && hasUpperCase && hasLowerCase && hasNumbers,
            requirements: {
                minLength: password.length >= minLength,
                hasUpperCase,
                hasLowerCase,
                hasNumbers,
                hasSpecialChar
            }
        };
    }
    
    generateToken(length = 32) {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        let token = '';
        for (let i = 0; i < length; i++) {
            token += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return token;
    }
    
    rateLimit(key, limit = 100, windowMs = 60000) {
        const now = Date.now();
        const requests = this.rateLimitStore?.get(key) || [];
        
        // Clean old requests
        const validRequests = requests.filter(timestamp => now - timestamp < windowMs);
        
        if (validRequests.length >= limit) {
            return { allowed: false, remaining: 0, resetAfter: windowMs };
        }
        
        validRequests.push(now);
        this.rateLimitStore.set(key, validRequests);
        
        return {
            allowed: true,
            remaining: limit - validRequests.length,
            resetAfter: windowMs
        };
    }
    
    encryptData(data) {
        // Simple encryption for demo
        const jsonString = JSON.stringify(data);
        const encrypted = btoa(jsonString);
        return encrypted;
    }
    
    decryptData(encrypted) {
        try {
            const decrypted = atob(encrypted);
            return JSON.parse(decrypted);
        } catch {
            return null;
        }
    }
    
    logSecurityEvent(event, details) {
        const logEntry = {
            timestamp: new Date().toISOString(),
            event,
            details,
            ip: this.getClientIP()
        };
        
        console.log('🔒 SECURITY:', logEntry);
        
        // Store in localStorage for demo
        const logs = JSON.parse(localStorage.getItem('security_logs') || '[]');
        logs.push(logEntry);
        localStorage.setItem('security_logs', JSON.stringify(logs.slice(-100)));
    }
    
    getClientIP() {
        // In browser context, we can't get real IP easily
        return 'client-side';
    }
}

window.security = new SecurityManager();