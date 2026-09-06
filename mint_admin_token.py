import asyncio, os, sys
sys.path.insert(0, '/app/backend')
os.chdir('/app/backend')
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
import jwt as pyjwt
from core.config import SECRET_KEY, ALGORITHM

async def main():
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]
    admin = await db.users.find_one({"is_admin": True})
    if not admin:
        # promote any existing user, else create one
        admin = await db.users.find_one({})
        if admin:
            await db.users.update_one({"_id": admin["_id"]}, {"$set": {"is_admin": True}})
        else:
            import uuid, datetime
            admin = {"id": str(uuid.uuid4()), "email": "verifyadmin@example.com",
                     "username": "verifyadmin", "is_admin": True, "balance_ton": 0,
                     "created_at": datetime.datetime.utcnow().isoformat()}
            await db.users.insert_one(admin)
    sub = admin.get("email") or admin.get("username") or admin.get("wallet_address")
    token = pyjwt.encode({"sub": sub}, SECRET_KEY, algorithm=ALGORITHM)
    print("SUB:", sub)
    print("TOKEN:", token)

asyncio.run(main())
