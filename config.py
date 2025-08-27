
import os
class Config:
    '''Flask/Redisの最低限設定'''
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only")
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB   = int(os.getenv("REDIS_DB", "0"))
    SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "86400"))
    JSON_AS_ASCII = False

# あとで諸々追加予定
