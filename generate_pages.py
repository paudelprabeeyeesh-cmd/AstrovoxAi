#!/usr/bin/env python3
import os

base_dir = r"C:\Users\Dell\Documents\GitHub\AstrovoxAi\frontend"
js_dir = os.path.join(base_dir, "js")

missing_pages = [
    ("analytics", "Analytics"),
    ("collaboration", "Collaboration"),
    ("database", "Database"),
    ("high-performance", "High Performance"),
    ("scalability", "Scalability"),
    ("platform-maturity", "Platform Maturity"),
    ("testing-framework", "Testing Framework"),
    ("security-excellence", "Security Excellence"),
    ("performance-optimization", "Performance Optimization"),
    ("automation-devops", "Automation DevOps"),
    ("intelligent-automation", "Intelligent Automation"),
    ("knowledge-platform", "Knowledge Platform"),
    ("marketplace", "Marketplace"),
    ("monitoring-center", "Monitoring Center"),
    ("advanced-api", "Advanced API"),
    ("engineering-productivity", "Engineering Productivity"),
    ("release-engineering", "Release Engineering"),
    ("v2-vision", "V2 Vision"),
    ("ai-networking", "AI Networking"),
    ("advanced-data", "Advanced Data"),
    ("model-factory", "Model Factory"),
    ("enterprise-expansion", "Enterprise Expansion"),
    ("edge-ai", "Edge AI"),
    ("research-benchmark", "Research Benchmark"),
    ("autonomous-engineering", "Autonomous Engineering"),
    ("data-governance", "Data Governance"),
    ("distributed", "Distributed"),
    ("high-performance-runtime", "High Performance Runtime"),
    ("ai-compiler", "AI Compiler"),
    ("runtime", "Runtime"),
    ("intelligent-memory", "Intelligent Memory"),
    ("reasoning-engine", "Reasoning Engine"),
    ("aiops", "AIOps"),
    ("sustainability", "Sustainability"),
    ("platform-evolution", "Platform Evolution"),
    ("policy", "Policy"),
    ("privacy", "Privacy"),
    ("recommendation", "Recommendation"),
    ("forecasting", "Forecasting"),
    ("business-intelligence", "Business Intelligence"),
    ("notifications", "Notifications"),
    ("orchestration", "Orchestration"),
    ("cqrs", "CQRS"),
    ("event-sourcing", "Event Sourcing"),
    ("cdc", "CDC"),
    ("core-assistant", "Core Assistant"),
]

# Build routing blocks
routing_blocks = []
method_blocks = []

for slug, title in missing_pages:
    title_var = ''.join(word.capitalize() for word in slug.split('-'))
    routing_blocks.append(f"""    }} else if (path === '/{slug}.html') {{
        if (!this.authState.isAuthenticated) {{
            window.location.href = '/login.html';
            return;
        }}
        this._show{title_var}();""")
    method_blocks.append(f"""  _show{title_var}() {{
    const app = document.getElementById('app');
    if (!app) return;
    window.location.href = '/{slug}.html';
  }}""")

routing_text = '\n'.join(routing_blocks)
methods_text = '\n'.join(method_blocks)

# Update app.js
app_js_path = os.path.join(js_dir, "app.js")
with open(app_js_path, 'r', encoding='utf-8') as f:
    app_js_content = f.read()

# Insert routing before final else
insertion_point = "    } else {\n        if (this.authState.isAuthenticated) {"
app_js_content = app_js_content.replace(
    insertion_point,
    routing_text + "\n" + insertion_point
)

# Insert methods before initRouter
method_insertion_point = "function initRouter() {"
app_js_content = app_js_content.replace(
    method_insertion_point,
    methods_text + "\n\n" + method_insertion_point
)

with open(app_js_path, 'w', encoding='utf-8') as f:
    f.write(app_js_content)

print("Updated app.js with new routes and methods")
