// ============================================
// ASTRAVOX PRIME — KNOWLEDGE BASE
// Local Knowledge Repository
// ============================================

const KnowledgeBase = {
    creators: `🧠 <strong>ASTRAVOX PRIME Development Team</strong><br><br>
            🎯 <strong style="color:#00F2FE;">Prabesh Paudel</strong> — AI Architect & Creator<br>
            ⚙️ <strong style="color:#9B51E0;">Dipson Baral</strong> — Backend Developer<br>
            🎨 <strong style="color:#FF007F;">Susanta Baral</strong> — Frontend Developer<br><br>
            Together they built this web intelligence AI system! 🚀`,
    
    python_factorial: `💻 <strong>Python Factorial Function</strong><br><br>
            <pre><code>def factorial(n):
    """Calculate factorial recursively"""
    if n <= 1:
        return 1
    return n * factorial(n - 1)

# Example
print(factorial(5))  # 120

# Iterative version
def factorial_iterative(n):
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result</code></pre>`,
    
    python_fibonacci: `💻 <strong>Python Fibonacci Sequence</strong><br><br>
            <pre><code>def fibonacci(n):
    if n <= 0:
        return []
    if n == 1:
        return [0]
    
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[-1] + fib[-2])
    return fib

print(fibonacci(10))  # [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]</code></pre>`,
    
    quantum_physics: `⚛️ <strong>Quantum Physics Explained</strong><br><br>
            Quantum physics studies matter and energy at atomic scales.<br><br>
            <strong>Key Principles:</strong><br>
            • Wave-Particle Duality<br>
            • Superposition<br>
            • Quantum Entanglement<br>
            • Uncertainty Principle<br><br>
            Applications: Lasers, Transistors, Quantum Computers`,
    
    black_hole: `🕳️ <strong>Black Holes</strong><br><br>
            A black hole is a region of spacetime where gravity is so strong that nothing can escape.<br><br>
            <strong>Key Facts:</strong><br>
            • Formed from collapsed stars<br>
            • Event horizon is point of no return<br>
            • Schwarzschild radius: R = 2GM/c²`,
    
    meaning_of_life: `🌍 <strong>The Meaning of Life</strong><br><br>
            Philosophical question with many perspectives:<br>
            • Existentialism: Create your own meaning<br>
            • Stoicism: Live virtuously<br>
            • Utilitarianism: Maximize happiness<br><br>
            What gives YOUR life meaning? 🤔`,
    
    react_component: `💻 <strong>React Component with Hooks</strong><br><br>
            <pre><code>import React, { useState, useEffect } from 'react';

const DataFetcher = ({ url }) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    
    useEffect(() => {
        fetch(url)
            .then(res => res.json())
            .then(setData)
            .finally(() => setLoading(false));
    }, [url]);
    
    if (loading) return <div>Loading...</div>;
    return <pre>{JSON.stringify(data, null, 2)}</pre>;
};</code></pre>`
};

window.KnowledgeBase = KnowledgeBase;