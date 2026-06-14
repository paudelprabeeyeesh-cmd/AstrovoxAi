// ============================================
// ASTRAVOX PRIME — AUTHENTICATION SYSTEM
// Sovereign AI Security Core
// Created by: Prabesh Paudel
// ============================================

// Storage Keys
const STORAGE = {
    USERS: 'astravox_users',
    SESSION: 'astravox_session'
};

// ============================================
// HASHING & SECURITY
// ============================================

function hashPassword(password) {
    let hash = 0;
    for (let i = 0; i < password.length; i++) {
        const char = password.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
    }
    return hash.toString(16);
}

function generateToken() {
    return 'token_' + Date.now() + '_' + Math.random().toString(36).substr(2, 16);
}

// ============================================
// USER MANAGEMENT
// ============================================

function getUsers() {
    const users = localStorage.getItem(STORAGE.USERS);
    return users ? JSON.parse(users) : [];
}

function saveUsers(users) {
    localStorage.setItem(STORAGE.USERS, JSON.stringify(users));
}

function findUserByEmail(email) {
    return getUsers().find(u => u.email === email);
}

function findUserByUsername(username) {
    return getUsers().find(u => u.username === username);
}

// Register
function registerUser(username, email, password) {
    // Validation
    if (!username || username.length < 3) {
        return { success: false, message: 'Username must be at least 3 characters' };
    }
    if (!email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
        return { success: false, message: 'Invalid email address' };
    }
    if (password.length < 6) {
        return { success: false, message: 'Password must be at least 6 characters' };
    }
    if (findUserByEmail(email)) {
        return { success: false, message: 'Email already registered' };
    }
    if (findUserByUsername(username)) {
        return { success: false, message: 'Username already taken' };
    }

    // Create user
    const newUser = {
        id: Date.now(),
        username: username,
        email: email,
        passwordHash: hashPassword(password),
        createdAt: new Date().toISOString(),
        memberSince: new Date().getFullYear(),
        preferences: { theme: 'dark', notifications: true }
    };

    const users = getUsers();
    users.push(newUser);
    saveUsers(users);

    return { success: true, message: 'Account created successfully!' };
}

// Login
function loginUser(email, password) {
    const user = findUserByEmail(email);
    
    if (!user) {
        return { success: false, message: 'Email not found' };
    }
    
    if (user.passwordHash !== hashPassword(password)) {
        return { success: false, message: 'Incorrect password' };
    }

    // Create session
    const session = {
        userId: user.id,
        username: user.username,
        email: user.email,
        memberSince: user.memberSince,
        token: generateToken(),
        loginTime: new Date().toISOString()
    };

    localStorage.setItem(STORAGE.SESSION, JSON.stringify(session));
    
    return { success: true, message: 'Login successful!', user: session };
}

// Logout
function logoutUser() {
    localStorage.removeItem(STORAGE.SESSION);
    window.location.href = 'login.html';
}

// Check if logged in
function isLoggedIn() {
    return localStorage.getItem(STORAGE.SESSION) !== null;
}

// Get current user
function getCurrentUser() {
    const session = localStorage.getItem(STORAGE.SESSION);
    return session ? JSON.parse(session) : null;
}

// Update user preferences
function updateUserPreferences(preferences) {
    const session = getCurrentUser();
    if (!session) return false;
    
    const users = getUsers();
    const userIndex = users.findIndex(u => u.id === session.userId);
    
    if (userIndex !== -1) {
        users[userIndex].preferences = { ...users[userIndex].preferences, ...preferences };
        saveUsers(users);
        return true;
    }
    return false;
}

// ============================================
// PAGE PROTECTION
// ============================================

function requireAuth() {
    if (!isLoggedIn()) {
        window.location.href = 'login.html';
        return false;
    }
    return true;
}

function requireGuest() {
    if (isLoggedIn()) {
        window.location.href = 'dashboard.html';
        return false;
    }
    return true;
}

// ============================================
// FORM HANDLERS
// ============================================

function showMessage(elementId, message, isError = true) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = message;
        element.style.display = 'block';
        if (isError) {
            element.style.background = 'rgba(255,68,102,0.1)';
            element.style.borderColor = '#ff4466';
            element.style.color = '#ff4466';
        } else {
            element.style.background = 'rgba(0,255,136,0.1)';
            element.style.borderColor = '#00ff88';
            element.style.color = '#00ff88';
        }
        setTimeout(() => {
            element.style.display = 'none';
        }, 3000);
    }
}

// Login form handler
function initLoginForm() {
    const form = document.getElementById('loginForm');
    if (!form) return;
    
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        
        const result = loginUser(email, password);
        
        if (result.success) {
            showMessage('successMsg', result.message, false);
            setTimeout(() => {
                window.location.href = 'dashboard.html';
            }, 1000);
        } else {
            showMessage('errorMsg', result.message, true);
        }
    });
}

// Register form handler
function initRegisterForm() {
    const form = document.getElementById('registerForm');
    if (!form) return;
    
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        
        if (password !== confirmPassword) {
            showMessage('errorMsg', 'Passwords do not match', true);
            return;
        }
        
        const result = registerUser(username, email, password);
        
        if (result.success) {
            showMessage('errorMsg', result.message, false);
            setTimeout(() => {
                window.location.href = 'login.html';
            }, 1500);
        } else {
            showMessage('errorMsg', result.message, true);
        }
    });
}

// ============================================
// INITIALIZE
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;
    
    if (path.includes('login.html')) {
        requireGuest();
        initLoginForm();
    }
    
    if (path.includes('register.html')) {
        requireGuest();
        initRegisterForm();
    }
    
    if (path.includes('dashboard.html') || path.includes('profile.html')) {
        requireAuth();
    }
});

// Global functions
window.logout = function() {
    logoutUser();
    window.location.href = 'login.html';
};

window.getCurrentUser = getCurrentUser;
window.isLoggedIn = isLoggedIn;