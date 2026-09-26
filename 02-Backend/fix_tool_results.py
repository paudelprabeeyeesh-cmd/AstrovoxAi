import re

with open('app/tools/__init__.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace ToolResult(False, "...", "tool_name") with ToolResult(False, "...", "tool_name", error="...")
def replacer(m):
    msg = m.group(1)
    tool = m.group(2)
    return f'ToolResult(False, {msg}, {tool}, error={msg})'

content = re.sub(
    r'ToolResult\(False, (f?"[^"]*"|\'[^\']*\'), ([A-Za-z_][A-Za-z0-9_]*)\)',
    replacer,
    content
)

with open('app/tools/__init__.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
