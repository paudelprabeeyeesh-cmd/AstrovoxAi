#!/usr/bin/env python3
import os

js_dir = r"C:\Users\Dell\Documents\GitHub\AstrovoxAi\frontend\js"
app_js_path = os.path.join(js_dir, "app.js")

with open(app_js_path, 'r', encoding='utf-8') as f:
    content = f.read()

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

methods_lines = []
for slug, title in missing_pages:
    title_var = ''.join(word.capitalize() for word in slug.split('-'))
    methods_lines.append(f"  _show{title_var}() {{")
    methods_lines.append(f"    const app = document.getElementById('app');")
    methods_lines.append(f"    if (!app) return;")
    methods_lines.append(f"    window.location.href = '/{slug}.html';")
    methods_lines.append(f"  }}")

methods_text = '\n'.join(methods_lines)

# Insert methods inside App class, before the class closing brace
# The pattern is: `  }\n\nfunction initRouter() {`
old_class_end = "  }\n\nfunction initRouter() {"
new_class_end = "  }\n" + methods_text + "\n\nfunction initRouter() {"

if old_class_end in content:
    content = content.replace(old_class_end, new_class_end, 1)
    print("Inserted methods inside App class")
else:
    print("ERROR: Could not find class end")

# Build routing blocks
routing_lines = []
for slug, title in missing_pages:
    title_var = ''.join(word.capitalize() for word in slug.split('-'))
    routing_lines.append(f"    }} else if (path === '/{slug}.html') {{")
    routing_lines.append(f"      if (!this.authState.isAuthenticated) {{")
    routing_lines.append(f"        window.location.href = '/login.html';")
    routing_lines.append(f"        return;")
    routing_lines.append(f"      }}")
    routing_lines.append(f"      this._show{title_var}();")

routing_text = '\n'.join(routing_lines)

# Insert routing before final else block
# Exact pattern: `      this._showMemory();\n    } else {`
insertion_marker = "      this._showMemory();\n    } else {"
replacement = "      this._showMemory();\n" + routing_text + "\n    } else {"

if insertion_marker in content:
    content = content.replace(insertion_marker, replacement, 1)
    print("Inserted routing before final else")
else:
    print("ERROR: Could not find routing insertion point")
    print("Content around memory route:")
    idx = content.find("_showMemory();")
    if idx != -1:
        print(repr(content[idx:idx+200]))

with open(app_js_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
