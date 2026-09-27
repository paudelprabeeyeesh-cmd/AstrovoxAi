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

# Find and remove any standalone methods that are outside the class
# They look like: `  _showXxx() {` followed by content and `  }`
# But we need to be careful not to remove methods inside the class.
# Since we already inserted them after the class closing brace, they are standalone.
# Let's find all `  _show` blocks that are after the last `}` before initRouter

init_router_idx = content.find('\nfunction initRouter()')

# Find the last `}` before initRouter that closes the class
# The pattern should be: method content ends with `  }\n\nfunction initRouter()`
# But currently it's: method content ends with `  }\n\nfunction initRouter()`
# Actually, looking at the output, the last thing before initRouter is a method `  _showCoreAssistant() { ... }`
# and there's no class closing brace.

# Let's find where the App class actually closes. Search backwards from initRouter for the class definition.
class_def_idx = content.rfind('class App {')
if class_def_idx == -1:
    print("ERROR: No class App found")
    exit(1)

# Find the last `}` before initRouter that is at the class level (2 spaces indent)
section_before_init = content[:init_router_idx]
lines = section_before_init.split('\n')

# Find the last line that is exactly `  }` - this should be the class closing brace
# But wait, if methods were inserted outside the class, there might be multiple `  }` lines
# Let's look for the pattern: a `  }` that is followed by blank line then `function initRouter()`

# Actually, looking at the current state, there might not be a class closing brace at all.
# Let's check:
last_50 = section_before_init[-100:]
print("Last 100 chars before initRouter:")
print(repr(last_50))

# If the class closing brace is missing, we need to add it before the methods
# and remove the extra `}` from the last method if needed

# First, let's rebuild the methods properly inside the class
methods_lines = []
for slug, title in missing_pages:
    title_var = ''.join(word.capitalize() for word in slug.split('-'))
    methods_lines.append(f"  _show{title_var}() {{")
    methods_lines.append(f"    const app = document.getElementById('app');")
    methods_lines.append(f"    if (!app) return;")
    methods_lines.append(f"    window.location.href = '/{slug}.html';")
    methods_lines.append(f"  }}")

methods_text = '\n'.join(methods_lines)

# Find the last occurrence of methods outside the class
# Pattern: _showCoreAssistant block ending with `  }\n\nfunction initRouter()`
core_assistant_idx = content.find("_showCoreAssistant()")
if core_assistant_idx != -1:
    # Find the end of this method
    method_end_idx = content.find("}\n\nfunction initRouter()", core_assistant_idx)
    if method_end_idx != -1:
        # Remove all standalone methods (from the first _showAnalytics to before initRouter)
        analytics_idx = content.find("  _showAnalytics() {")
        if analytics_idx != -1 and analytics_idx < method_end_idx:
            # Keep everything before the standalone methods
            before = content[:analytics_idx]
            # Keep everything from initRouter onwards
            after = content[method_end_idx + 1:]  # +1 to skip the `}` that was the last method's end
            # But wait, we need to add the class closing `}` and then the methods inside the class
            # Actually, the methods should be inside the class, before the class closing `}`
            # So: before + class_close + methods + newline + initRouter
            new_content = before.rstrip() + "\n  }\n" + methods_text + "\n\n" + after.lstrip('\n')
            content = new_content
            print("Rebuilt methods inside class")

with open(app_js_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed app.js class structure")
