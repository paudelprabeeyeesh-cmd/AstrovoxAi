import sys
sys.path.insert(0, '.')
try:
    from app.routers.audio import router
    print('audio router: OK')
except Exception as e:
    print(f'audio router: FAIL - {e}')
try:
    from app.routers.images import router
    print('images router: OK')
except Exception as e:
    print(f'images router: FAIL - {e}')
try:
    from app.routers.code_agent import router
    print('code_agent router: OK')
except Exception as e:
    print(f'code_agent router: FAIL - {e}')
