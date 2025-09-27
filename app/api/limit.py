import time
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status

RATE_LIMIT = 100           # requests
WINDOW_SEC = 60 * 60       # per hour
_store: dict[str, deque[float]] = defaultdict(deque)

async def rate_limit(request: Request):
    api_key = request.headers.get("X-API-Key", "anon")
    key = f"{api_key}:{request.url.path}"
    now = time.time()
    q = _store[key]
    while q and (now - q[0]) > WINDOW_SEC:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {RATE_LIMIT}/hour"
        )
    q.append(now)
