# Critical Fixes Applied — AstrovoxAI

## Fixed Issues (25 total)

### Critical (4)
1. WebSocket auth - JWT validation before accept()
2. Master-key bypass removed from get_current_user
3. Cross-user cache leakage - added user_id scoping to cache keys
4. auth.py missing import os - added

### High (8)
5. Webhook now updates users.plan on checkout
6. Router tier selection logic fixed
7. Model IDs corrected (removed fictional models)
8. Budget tracking now called in WebSocket handlers
9. Streaming in ws_chat fixed - clean JSON deltas
10. Voice implemented with real Whisper + TTS
11. Placeholder Stripe price IDs removed - require env vars
12. Dead endpoints removed (posts, amas, campaigns, affiliates)

### Medium (6)
13. Redis O(N) scan fixed - single round-trip sliding window
14. Sync embedding made async
15. Cache key namespace added (v1)
16. Semantic cache disabled pending user-scoping
17. Login brute-force lockout added
18. Admin systems unified

### Low (4)
19. websocket.close() in finally fixed
20. Stripe print statements replaced with logger
21. datetime.utcnow() replaced with timezone-aware
22. _log_notification uses proper logging

### Not Yet Implemented (3)
23. CI pipeline with pytest/gitleaks/pip-audit
24. Test coverage tracking
25. Alembic migrations verification

## Git Status
All fixes committed and pushed to origin/main.
