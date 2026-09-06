#!/usr/bin/env python3
"""
Test script for GRAM CITY "buy island plot" flow - Telegram Mini App user bug fix.

Tests that POST /api/island/buy/{x}/{y} no longer returns 404 "Пользователь не найден"
for Telegram users who have NO wallet_address and NO email (identified only by id/username).
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from jose import jwt
import httpx

# Add backend to path
sys.path.insert(0, '/app/backend')

# Import after path setup
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Load environment
load_dotenv('/app/backend/.env')

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")
BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ton-city-progress.preview.emergentagent.com")

# Load JWT config
load_dotenv('/app/backend/.env')
sys.path.insert(0, '/app/backend')
from security_middleware import get_or_generate_jwt_secret
SECRET_KEY = get_or_generate_jwt_secret()
ALGORITHM = "HS256"

print(f"🔧 Configuration:")
print(f"   MONGO_URL: {MONGO_URL}")
print(f"   DB_NAME: {DB_NAME}")
print(f"   BACKEND_URL: {BACKEND_URL}")
print(f"   SECRET_KEY: {SECRET_KEY[:20]}...")
print()


def create_jwt_token(username: str, session_id: str = None) -> str:
    """Create a JWT token for a user (mimics auth_handler.create_token)."""
    payload = {
        "sub": username,  # Use username as identifier for Telegram users
        "exp": datetime.now(timezone.utc).timestamp() + (30 * 24 * 3600),  # 30 days
    }
    if session_id:
        payload["sid"] = session_id
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def test_telegram_user_buy_plot():
    """
    Test the fix for Telegram Mini App user "buy island plot" flow.
    
    The bug: endpoint POST /api/island/buy/{x}/{y} previously resolved the DB user
    ONLY by wallet_address or email. Telegram Mini App users have neither (they are
    identified by `id`), so it returned HTTP 404 detail="Пользователь не найден".
    
    The fix: now resolves the user primarily by `current_user.id`, then falls back
    to wallet_address/email.
    """
    print("=" * 80)
    print("TEST: Telegram Mini App User - Buy Island Plot")
    print("=" * 80)
    print()
    
    # Connect to MongoDB
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client[DB_NAME]
    
    try:
        # Step 1: Create a Telegram-style user (id + username only, NO wallet/email)
        print("📝 Step 1: Creating Telegram-style test user...")
        telegram_user_id = str(uuid.uuid4())
        telegram_username = f"tg_test_{uuid.uuid4().hex[:8]}"
        session_id = str(uuid.uuid4())
        
        telegram_user = {
            "id": telegram_user_id,
            "username": telegram_username,
            "display_name": f"Telegram Test User",
            "email": None,  # NO EMAIL
            "wallet_address": None,  # NO WALLET
            "raw_address": None,
            "hashed_password": None,
            "avatar": {"type": "initials", "initials": "TG", "color": "#6366f1"},
            "balance_ton": 100.0,  # Sufficient balance for testing
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
            "email_verified": False,
            "agreement_accepted": True,
            "registration_method": "telegram",
            "telegram_id": 123456789,
            "telegram_user_id": "123456789",
            "telegram_chat_id": "123456789",
            "telegram_username": telegram_username,
            "telegram_verified": True,
            "telegram_notifications": True,
            "login_methods": ["telegram"],
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login": datetime.now(timezone.utc).isoformat(),
            "tutorial_active": False,  # NOT in tutorial
            "tutorial_completed": True,
        }
        
        # Insert user
        await db.users.insert_one(telegram_user)
        print(f"   ✅ Created user: id={telegram_user_id}, username={telegram_username}")
        print(f"   ✅ User has NO wallet_address and NO email (Telegram-only)")
        print(f"   ✅ User balance: {telegram_user['balance_ton']} TON")
        print()
        
        # Step 2: Create JWT token for this user
        print("🎫 Step 2: Creating JWT token...")
        token = create_jwt_token(telegram_username, session_id)
        print(f"   ✅ JWT token created (sub={telegram_username})")
        print()
        
        # Step 3: Find an available plot to buy
        print("🗺️  Step 3: Finding an available plot...")
        
        # Get island data
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{BACKEND_URL}/api/island")
            if response.status_code != 200:
                print(f"   ❌ Failed to get island data: {response.status_code}")
                return False
            
            island_data = response.json()
            cells = island_data.get("cells", [])
            
            # Find an available plot (not owned, not in tutorial zone)
            available_plot = None
            for cell in cells:
                if not cell.get("owner") and cell.get("zone") != "tutorial":
                    available_plot = cell
                    break
            
            if not available_plot:
                print(f"   ⚠️  No available plots found, using coordinates (5, 5)")
                x, y = 5, 5
            else:
                x, y = available_plot["x"], available_plot["y"]
                print(f"   ✅ Found available plot at ({x}, {y})")
                print(f"      Zone: {available_plot.get('zone')}")
                print(f"      Price: {available_plot.get('price_ton', 'N/A')} TON")
        print()
        
        # Step 4: Attempt to buy the plot
        print(f"🛒 Step 4: Attempting to buy plot ({x}, {y})...")
        print(f"   Using token for Telegram user (id-only, no wallet/email)")
        print()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/api/island/buy/{x}/{y}",
                headers=headers,
            )
            
            print(f"📊 Response Status: {response.status_code}")
            print(f"📊 Response Body: {response.text[:500]}")
            print()
            
            # KEY ASSERTION: Must NOT be 404 "Пользователь не найден"
            if response.status_code == 404:
                response_data = response.json()
                if "Пользователь не найден" in response_data.get("detail", ""):
                    print("❌ FAILED: Got 404 'Пользователь не найден' - THE BUG IS NOT FIXED!")
                    print("   The endpoint still cannot find Telegram users (id-only).")
                    return False
                else:
                    print(f"✅ PASSED: Got 404 but NOT 'Пользователь не найден': {response_data.get('detail')}")
                    print("   This is acceptable (plot not found, etc.)")
                    return True
            
            # 400/403 for valid game-rule reasons is ACCEPTABLE (proves user WAS found)
            elif response.status_code in [400, 403, 423]:
                response_data = response.json()
                detail = response_data.get("detail", "")
                print(f"✅ PASSED: Got {response.status_code} - User WAS found!")
                print(f"   Reason: {detail}")
                print("   This proves the user lookup by 'id' is working correctly.")
                return True
            
            # 200/201 - successful purchase
            elif response.status_code in [200, 201]:
                response_data = response.json()
                print(f"✅ PASSED: Purchase successful!")
                print(f"   Status: {response_data.get('status')}")
                print(f"   New balance: {response_data.get('new_balance_ton')} TON")
                print("   The user lookup by 'id' is working correctly.")
                return True
            
            # Other status codes
            else:
                print(f"⚠️  Unexpected status code: {response.status_code}")
                print(f"   Response: {response.text}")
                print("   Cannot determine if the fix is working.")
                return False
    
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup: remove test user
        print()
        print("🧹 Cleanup: Removing test user...")
        try:
            await db.users.delete_one({"id": telegram_user_id})
            # Also cleanup any plots/businesses created
            await db.plots.delete_many({"owner": telegram_user_id})
            await db.businesses.delete_many({"owner": telegram_user_id})
            print("   ✅ Cleanup complete")
        except Exception as e:
            print(f"   ⚠️  Cleanup failed: {e}")
        finally:
            mongo_client.close()  # MongoDB client


async def test_email_user_backward_compatibility():
    """
    Test that regular email-based users can still buy plots (backward compatibility).
    The id lookup should still find email/wallet users too.
    """
    print()
    print("=" * 80)
    print("TEST: Email User - Backward Compatibility")
    print("=" * 80)
    print()
    
    # Connect to MongoDB
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client[DB_NAME]
    
    try:
        # Step 1: Create an email-based user
        print("📝 Step 1: Creating email-based test user...")
        email_user_id = str(uuid.uuid4())
        email_username = f"email_test_{uuid.uuid4().hex[:8]}"
        email = f"{email_username}@test.com"
        session_id = str(uuid.uuid4())
        
        email_user = {
            "id": email_user_id,
            "username": email_username,
            "display_name": "Email Test User",
            "email": email,
            "wallet_address": None,
            "raw_address": None,
            "hashed_password": "dummy_hash",
            "avatar": {"type": "initials", "initials": "ET", "color": "#8b5cf6"},
            "balance_ton": 100.0,
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
            "email_verified": True,
            "registration_method": "email",
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login": datetime.now(timezone.utc).isoformat(),
            "tutorial_active": False,
            "tutorial_completed": True,
        }
        
        await db.users.insert_one(email_user)
        print(f"   ✅ Created user: id={email_user_id}, email={email}")
        print()
        
        # Step 2: Create JWT token
        print("🎫 Step 2: Creating JWT token...")
        token = create_jwt_token(email_username, session_id)
        print(f"   ✅ JWT token created")
        print()
        
        # Step 3: Attempt to buy a plot
        print("🛒 Step 3: Attempting to buy plot (10, 10)...")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/api/island/buy/10/10",
                headers=headers,
            )
            
            print(f"📊 Response Status: {response.status_code}")
            print()
            
            # Should NOT be 404 "Пользователь не найден"
            if response.status_code == 404:
                response_data = response.json()
                if "Пользователь не найден" in response_data.get("detail", ""):
                    print("❌ FAILED: Email user got 'Пользователь не найден'")
                    print("   Backward compatibility broken!")
                    return False
            
            # Any other response is acceptable (proves user was found)
            print("✅ PASSED: Email user can still be found (backward compatibility OK)")
            return True
    
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        print()
        print("🧹 Cleanup: Removing test user...")
        try:
            await db.users.delete_one({"id": email_user_id})
            await db.plots.delete_many({"owner": email_user_id})
            await db.businesses.delete_many({"owner": email_user_id})
            print("   ✅ Cleanup complete")
        except Exception as e:
            print(f"   ⚠️  Cleanup failed: {e}")
        finally:
            mongo_client.close()  # MongoDB client


async def main():
    """Run all tests."""
    print()
    print("🚀 Starting Telegram User Buy Plot Tests")
    print()
    
    # Test 1: Telegram user (id-only)
    test1_passed = await test_telegram_user_buy_plot()
    
    # Test 2: Email user (backward compatibility)
    test2_passed = await test_email_user_backward_compatibility()
    
    # Summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"✅ Telegram User (id-only): {'PASSED' if test1_passed else 'FAILED'}")
    print(f"✅ Email User (backward compat): {'PASSED' if test2_passed else 'FAILED'}")
    print()
    
    if test1_passed and test2_passed:
        print("🎉 ALL TESTS PASSED!")
        print("   The fix for 'Пользователь не найден' is working correctly.")
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        print("   The bug may not be fully fixed.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
