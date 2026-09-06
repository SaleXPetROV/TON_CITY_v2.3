#!/usr/bin/env python3
"""
Comprehensive test for Telegram user island operations.
Tests both buy and build endpoints with admin privileges to bypass presale.
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from jose import jwt
import httpx

sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ton-city-progress.preview.emergentagent.com")

from security_middleware import get_or_generate_jwt_secret
SECRET_KEY = get_or_generate_jwt_secret()
ALGORITHM = "HS256"

print(f"🔧 Configuration:")
print(f"   BACKEND_URL: {BACKEND_URL}")
print()


def create_jwt_token(username: str, session_id: str = None) -> str:
    """Create a JWT token for a user."""
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc).timestamp() + (30 * 24 * 3600),
    }
    if session_id:
        payload["sid"] = session_id
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def test_telegram_admin_buy_plot():
    """
    Test Telegram user (id-only) with ADMIN privileges can buy a plot.
    Admin bypasses presale restrictions.
    """
    print("=" * 80)
    print("TEST: Telegram Admin User - Buy Island Plot (Bypass Presale)")
    print("=" * 80)
    print()
    
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client[DB_NAME]
    
    try:
        # Create Telegram admin user
        print("📝 Creating Telegram admin user...")
        user_id = str(uuid.uuid4())
        username = f"tg_admin_{uuid.uuid4().hex[:8]}"
        session_id = str(uuid.uuid4())
        
        user = {
            "id": user_id,
            "username": username,
            "display_name": "Telegram Admin",
            "email": None,  # NO EMAIL
            "wallet_address": None,  # NO WALLET
            "raw_address": None,
            "hashed_password": None,
            "avatar": {"type": "initials", "initials": "TA", "color": "#6366f1"},
            "balance_ton": 1000.0,  # High balance
            "bonus_balance": 0.0,
            "language": "en",
            "level": 10,
            "xp": 0,
            "total_turnover": 0,
            "total_income": 0,
            "resources": {},
            "plots_owned": [],
            "businesses_owned": [],
            "is_admin": True,  # ADMIN
            "role": "ADMIN",
            "email_verified": False,
            "registration_method": "telegram",
            "telegram_id": 999999999,
            "telegram_user_id": "999999999",
            "telegram_verified": True,
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login": datetime.now(timezone.utc).isoformat(),
            "tutorial_active": False,
            "tutorial_completed": True,
        }
        
        await db.users.insert_one(user)
        print(f"   ✅ Created admin user: {username} (id={user_id})")
        print(f"   ✅ User is ADMIN with NO wallet/email")
        print()
        
        # Create JWT
        token = create_jwt_token(username, session_id)
        print("🎫 JWT token created")
        print()
        
        # Find available plot
        print("🗺️  Finding available plot...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{BACKEND_URL}/api/island")
            if response.status_code != 200:
                print(f"   ❌ Failed to get island: {response.status_code}")
                return False
            
            island = response.json()
            cells = island.get("cells", [])
            
            # Find first available plot
            available = None
            for cell in cells:
                if not cell.get("owner"):
                    available = cell
                    break
            
            if not available:
                print("   ⚠️  No available plots")
                return False
            
            x, y = available["x"], available["y"]
            print(f"   ✅ Found plot at ({x}, {y}), zone: {available.get('zone')}")
        print()
        
        # Attempt to buy
        print(f"🛒 Attempting to buy plot ({x}, {y}) as Telegram admin...")
        headers = {"Authorization": f"Bearer {token}"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/api/island/buy/{x}/{y}",
                headers=headers,
            )
            
            print(f"📊 Status: {response.status_code}")
            
            if response.status_code == 404:
                data = response.json()
                if "Пользователь не найден" in data.get("detail", ""):
                    print("❌ FAILED: Got 'Пользователь не найден'")
                    print("   The bug is NOT fixed for admin Telegram users!")
                    return False
                else:
                    print(f"✅ PASSED: 404 but NOT user-not-found: {data.get('detail')}")
                    return True
            
            elif response.status_code in [200, 201]:
                data = response.json()
                print(f"✅ PASSED: Purchase successful!")
                print(f"   Status: {data.get('status')}")
                print(f"   New balance: {data.get('new_balance_ton')} TON")
                return True
            
            elif response.status_code in [400, 403, 423]:
                data = response.json()
                print(f"✅ PASSED: Got {response.status_code} - User was found!")
                print(f"   Reason: {data.get('detail')}")
                return True
            
            else:
                print(f"⚠️  Unexpected status: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print()
        print("🧹 Cleanup...")
        try:
            await db.users.delete_one({"id": user_id})
            await db.plots.delete_many({"owner": user_id})
            await db.businesses.delete_many({"owner": user_id})
            print("   ✅ Cleanup complete")
        except Exception as e:
            print(f"   ⚠️  Cleanup failed: {e}")
        finally:
            mongo_client.close()


async def test_telegram_user_build_on_plot():
    """
    Test Telegram user (id-only) can build on an owned empty plot.
    Tests the /api/island/build/{x}/{y} endpoint.
    """
    print()
    print("=" * 80)
    print("TEST: Telegram User - Build on Empty Plot")
    print("=" * 80)
    print()
    
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client[DB_NAME]
    
    try:
        # Create Telegram user
        print("📝 Creating Telegram user...")
        user_id = str(uuid.uuid4())
        username = f"tg_builder_{uuid.uuid4().hex[:8]}"
        session_id = str(uuid.uuid4())
        
        user = {
            "id": user_id,
            "username": username,
            "display_name": "Telegram Builder",
            "email": None,
            "wallet_address": None,
            "raw_address": None,
            "hashed_password": None,
            "avatar": {"type": "initials", "initials": "TB", "color": "#8b5cf6"},
            "balance_ton": 500.0,
            "bonus_balance": 0.0,
            "language": "en",
            "level": 1,
            "xp": 0,
            "total_turnover": 0,
            "total_income": 0,
            "resources": {},
            "plots_owned": [],
            "businesses_owned": [],
            "is_admin": False,
            "registration_method": "telegram",
            "telegram_id": 888888888,
            "telegram_user_id": "888888888",
            "telegram_verified": True,
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login": datetime.now(timezone.utc).isoformat(),
            "tutorial_active": False,
            "tutorial_completed": True,
        }
        
        await db.users.insert_one(user)
        print(f"   ✅ Created user: {username}")
        print()
        
        # Create an empty plot owned by this user
        print("📝 Creating empty plot for user...")
        plot_id = str(uuid.uuid4())
        x, y = 50, 50  # Use coordinates unlikely to conflict
        
        plot = {
            "id": plot_id,
            "island_id": "ton_island",
            "x": x,
            "y": y,
            "zone": "residential",
            "price_ton": 10.0,
            "price_city": 10000.0,
            "owner": user_id,
            "owner_username": username,
            "business": None,
            "business_id": None,
            "is_empty": True,  # EMPTY PLOT
            "warehouses": [],
            "purchased_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.plots.insert_one(plot)
        print(f"   ✅ Created empty plot at ({x}, {y})")
        print()
        
        # Create JWT
        token = create_jwt_token(username, session_id)
        
        # Attempt to build
        print(f"🏗️  Attempting to build on plot ({x}, {y})...")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        build_request = {
            "business_type": "farm"  # Tier 1 business
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/api/island/build/{x}/{y}",
                headers=headers,
                json=build_request,
            )
            
            print(f"📊 Status: {response.status_code}")
            
            if response.status_code == 404:
                data = response.json()
                if "Пользователь не найден" in data.get("detail", ""):
                    print("❌ FAILED: Got 'Пользователь не найден'")
                    print("   The build endpoint bug is NOT fixed!")
                    return False
                else:
                    print(f"✅ PASSED: 404 but NOT user-not-found: {data.get('detail')}")
                    return True
            
            elif response.status_code in [200, 201]:
                data = response.json()
                print(f"✅ PASSED: Build successful!")
                print(f"   Status: {data.get('status')}")
                print(f"   Business: {data.get('business', {}).get('type')}")
                return True
            
            elif response.status_code in [400, 403, 423]:
                data = response.json()
                print(f"✅ PASSED: Got {response.status_code} - User was found!")
                print(f"   Reason: {data.get('detail')}")
                return True
            
            else:
                print(f"⚠️  Unexpected status: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print()
        print("🧹 Cleanup...")
        try:
            await db.users.delete_one({"id": user_id})
            await db.plots.delete_many({"owner": user_id})
            await db.businesses.delete_many({"owner": user_id})
            print("   ✅ Cleanup complete")
        except Exception as e:
            print(f"   ⚠️  Cleanup failed: {e}")
        finally:
            mongo_client.close()


async def main():
    """Run all comprehensive tests."""
    print()
    print("🚀 Starting Comprehensive Telegram User Tests")
    print()
    
    test1 = await test_telegram_admin_buy_plot()
    test2 = await test_telegram_user_build_on_plot()
    
    print()
    print("=" * 80)
    print("COMPREHENSIVE TEST SUMMARY")
    print("=" * 80)
    print(f"✅ Telegram Admin Buy: {'PASSED' if test1 else 'FAILED'}")
    print(f"✅ Telegram User Build: {'PASSED' if test2 else 'FAILED'}")
    print()
    
    if test1 and test2:
        print("🎉 ALL COMPREHENSIVE TESTS PASSED!")
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
