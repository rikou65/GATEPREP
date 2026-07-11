from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import Settings


def create_db_client(settings: Settings):
    mongo_url = settings.MONGO_URL
    use_tls = (
        "mongodb+srv://" in mongo_url
        or "replicaSet" in mongo_url
        or "ssl=true" in mongo_url.lower()
    )
    client = AsyncIOMotorClient(
        mongo_url,
        tls=use_tls,
        tlsAllowInvalidCertificates=not settings.is_production(),
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )
    db = client[settings.DB_NAME]
    return client, db
