from slowapi import Limiter
from slowapi.util import get_remote_address

# In-memory limiter: fine for a single instance. Behind a proxy, run uvicorn
# with --proxy-headers so the client IP (not the proxy's) is used.
limiter = Limiter(key_func=get_remote_address)
