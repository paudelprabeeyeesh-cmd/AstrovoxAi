import re
import os

main_path = r'C:\AstrovoxAi\02-Backend\app\main.py'

with open(main_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add router imports after the admin_router import
content = content.replace(
    'from .admin_panel import router as admin_router',
    'from .admin_panel import router as admin_router\nfrom .routers import solve as solve_router\nfrom .routers import memory as memory_router\nfrom .routers import rag as rag_router\nfrom .routers import files as files_router'
)

# Add router includes after admin_router include
content = content.replace(
    'app.include_router(admin_router)',
    'app.include_router(admin_router)\napp.include_router(solve_router.router)\napp.include_router(memory_router.router)\napp.include_router(rag_router.router)\napp.include_router(files_router.router)'
)

# Remove inline solve endpoints
solve_pattern = r'@app\.post\("/solve"\)\s+async def solve\(.*?\n\n(?=\s*@app\.|\Z)'
content = re.sub(solve_pattern, '', content, flags=re.DOTALL)

solve_stream_pattern = r'@app\.post\("/solve/stream"\)\s+async def solve_stream\(.*?\n\n(?=\s*@app\.|\Z)'
content = re.sub(solve_stream_pattern, '', content, flags=re.DOTALL)

# Remove memory endpoints
memory_routes = [
    r'@app\.post\("/memory".*?(?=\n@app\.)',
    r'@app\.get\("/memory".*?(?=\n@app\.)',
    r'@app\.get\("/memory/search".*?(?=\n@app\.)',
    r'@app\.put\("/memory/\{memory_id\}".*?(?=\n@app\.)',
    r'@app\.delete\("/memory/\{memory_id\}".*?(?=\n@app\.)',
    r'@app\.get\("/memory/export".*?(?=\n@app\.)',
    r'@app\.post\("/memory/classify".*?(?=\n@app\.)',
]
for pat in memory_routes:
    content = re.sub(pat, '', content, flags=re.DOTALL)

# Remove rag endpoints
rag_routes = [
    r'@app\.post\("/rag/ingest".*?(?=\n@app\.)',
    r'@app\.post\("/rag/ingest/website".*?(?=\n@app\.)',
    r'@app\.post\("/rag/ingest/github".*?(?=\n@app\.)',
    r'@app\.post\("/rag/search".*?(?=\n@app\.)',
    r'@app\.get\("/rag/documents".*?(?=\n@app\.)',
    r'@app\.delete\("/rag/documents/\{doc_id\}".*?(?=\n@app\.)',
]
for pat in rag_routes:
    content = re.sub(pat, '', content, flags=re.DOTALL)

# Remove files endpoints
files_routes = [
    r'@app\.post\("/files/upload".*?(?=\n@app\.)',
    r'@app\.get\("/files\".*?(?=\n@app\.)',
    r'@app\.get\("/files/\{file_id\}".*?(?=\n@app\.)',
    r'@app\.delete\("/files/\{file_id\}".*?(?=\n@app\.)',
]
for pat in files_routes:
    content = re.sub(pat, '', content, flags=re.DOTALL)

with open(main_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
