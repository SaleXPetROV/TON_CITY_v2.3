import asyncio, os, sys, uuid
from datetime import datetime, timezone
sys.path.insert(0, '/app/backend')
os.chdir('/app/backend')
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
from motor.motor_asyncio import AsyncIOMotorClient
from auth_handler import pwd_context

EMAIL = "admin@gramcity.dev"
USERNAME = "gcadmin"
PASSWORD = "GramCity!2025"

async def main():
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]
    ph = pwd_context.hash(PASSWORD)
    existing = await db.users.find_one({"$or": [{"email": EMAIL}, {"username": USERNAME}]})
    doc = {
        "email": EMAIL,
        "username": USERNAME,
        "display_name": "GC Admin",
        "hashed_password": ph,
        "is_admin": True,
        "is_blocked": False,
        "is_banned": False,
        "language": "ru",
        "balance_ton": 100.0,
        "bonus_balance": 0.0,
        "resources": {},
        "last_login": datetime.now(timezone.utc),
    }
    if existing:
        await db.users.update_one({"_id": existing["_id"]}, {"$set": doc})
        print("UPDATED existing user ->", EMAIL)
    else:
        doc["id"] = str(uuid.uuid4())
        doc["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.users.insert_one(doc)
        print("CREATED new admin ->", EMAIL)
    u = await db.users.find_one({"email": EMAIL}, {"_id": 0, "id": 1, "email": 1, "username": 1, "is_admin": 1})
    print("RESULT:", u)

asyncio.run(main())
