/**
 * Astravox AI - Theme Configuration Engine
 * Seamless runtime state modifications without matrix dropouts
 */

class ThemeMatrixEngine {
    constructor() {
        this.currentTheme = localStorage.getItem('astravox-theme') || 'dark';
        this.init();
    }

    init() {
        this.applyTheme(this.currentTheme);
    }

    /**
     * Swaps structural color palettes across global elements
     * @param {'dark' | 'light'} targetMode 
     */
    applyTheme(targetMode) {
        const rootElement = document.documentElement;
        
        if (targetMode === 'light') {
            rootElement.style.setProperty('--bg-dark', '#f4f4fa');
            rootElement.style.setProperty('--panel-bg', 'rgba(240, 240, 250, 0.75)');
            rootElement.style.setProperty('--border-glow', 'rgba(155, 81, 224, 0.1)');
            document.body.style.color = '#12121f';
        } else {
            rootElement.style.setProperty('--bg-dark', '#05050e');
            rootElement.style.setProperty('--panel-bg', 'rgba(10, 10, 26, 0.55)');
            rootElement.style.setProperty('--border-glow', 'rgba(0, 242, 254, 0.15)');
            document.body.style.color = '#ffffff';
        }
        
        this.currentTheme = targetMode;
        localStorage.setItem('astravox-theme', targetMode);
        
        if (window.Notifications) {
            window.Notifications.spawn(`Visual matrix modified: ${targetMode.toUpperCase()} mode.`, 'info');
        }
    }

    toggle() {
        this.applyTheme(this.currentTheme === 'dark' ? 'light' : 'dark');
    }
}

// Global invocation hook
window.ThemeEngine = new ThemeMatrixEngine();