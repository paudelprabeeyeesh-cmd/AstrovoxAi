#!/usr/bin/env python3
import os

js_dir = r"C:\Users\Dell\Documents\GitHub\AstrovoxAi\frontend\js"
app_js_path = os.path.join(js_dir, "app.js")

with open(app_js_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the class closing brace
# Pattern: `}\n\n  _showAnalytics()`
class_end_pattern = "}\n\n  _showAnalytics()"
idx = content.find(class_end_pattern)

if idx == -1:
    print("ERROR: Could not find class end pattern")
    exit(1)

# Extract all the standalone methods
methods_start = idx + 1  # skip the `}`
methods_end = content.find("\n\nfunction initRouter()", methods_start)
if methods_end == -1:
    print("ERROR: Could not find initRouter")
    exit(1)

methods_text = content[methods_start:methods_end]
# Remove leading newline from methods
methods_text = methods_text.lstrip('\n')

# Remove the methods from after the class
before_methods = content[:idx + 1]  # include the `}`
after_methods = content[methods_end:]

# Insert methods inside the class, before the closing `}`
new_content = before_methods.rstrip() + "\n" + methods_text + "\n" + after_methods.lstrip('\n')

with open(app_js_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Moved methods inside App class")
