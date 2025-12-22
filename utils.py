# utils.py
import os

SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "changeme")
ALGORITHM = os.getenv("AUTH_ALGORITHM", "HS256")
AUDIENCE = os.getenv("AUTH_AUDIENCE", "sentracare-users")
ISSUER = os.getenv("AUTH_ISSUER", "sentracare-auth")
