#!/usr/bin/env python3
"""
Test script for GRAM CITY per-skin display SIZE feature.

Tests the new PATCH /api/admin/skins/{skin_id}/size endpoint and the updated
GET /api/skins/index endpoint that now returns both "index" and "sizes" maps.
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

# Load frontend env for backend URL
load_dotenv('/app/frontend/.env')
BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ton-city-progress.preview.emergentagent.com")

# Load JWT config
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


def create_jwt_token(identifier: str, session_id: str = None) -> str:
    """Create a JWT token for a user."""
    payload = {
        "sub": identifier,
        "exp": datetime.now(timezone.utc).timestamp() + (30 * 24 * 3600),  # 30 days
    }
    if session_id:
        payload["sid"] = session_id
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def setup_admin_user(db):
    """Create or get an admin user for testing."""
    print("👤 Setting up admin user...")
    
    # Check if admin user exists
    admin_user = await db.users.find_one({"is_admin": True})
    
    if admin_user:
        print(f"   ✅ Found existing admin user: {admin_user.get('username', admin_user.get('email', admin_user.get('id')))}")
        identifier = admin_user.get("username") or admin_user.get("email") or admin_user.get("wallet_address")
        session_id = admin_user.get("session_id") or str(uuid.uuid4())
        return admin_user, identifier, session_id
    
    # Create new admin user
    admin_id = str(uuid.uuid4())
    admin_username = f"admin_test_{uuid.uuid4().hex[:8]}"
    session_id = str(uuid.uuid4())
    
    admin_user = {
        "id": admin_id,
        "username": admin_username,
        "display_name": "Admin Test User",
        "email": f"{admin_username}@test.com",
        "wallet_address": None,
        "raw_address": None,
        "hashed_password": "dummy_hash",
        "avatar": {"type": "initials", "initials": "AD", "color": "#ef4444"},
        "balance_ton": 1000.0,
        "bonus_balance": 0.0,
        "language": "en",
        "level": 1,
        "xp": 0,
        "total_turnover": 0,
        "total_income": 0,
        "resources": {},
        "plots_owned": [],
        "businesses_owned": [],
        "is_admin": True,  # ADMIN FLAG
        "email_verified": True,
        "registration_method": "email",
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_login": datetime.now(timezone.utc).isoformat(),
    }
    
    await db.users.insert_one(admin_user)
    print(f"   ✅ Created admin user: {admin_username}")
    
    return admin_user, admin_username, session_id


async def test_admin_auth():
    """Test 1: Verify admin authentication is required."""
    print("=" * 80)
    print("TEST 1: Admin Authentication Required")
    print("=" * 80)
    print()
    
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client[DB_NAME]
    
    try:
        # Create a non-admin user
        print("📝 Creating non-admin user...")
        user_id = str(uuid.uuid4())
        username = f"user_test_{uuid.uuid4().hex[:8]}"
        session_id = str(uuid.uuid4())
        
        user = {
            "id": user_id,
            "username": username,
            "display_name": "Regular User",
            "email": f"{username}@test.com",
            "is_admin": False,  # NOT ADMIN
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(user)
        
        # Create token for non-admin user
        token = create_jwt_token(username, session_id)
        
        # Try to access admin endpoint without auth
        print("🔒 Test 1a: No token (should get 401)...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{BACKEND_URL}/api/admin/skins")
            print(f"   Status: {response.status_code}")
            if response.status_code == 401:
                print("   ✅ PASSED: Got 401 without token")
            else:
                print(f"   ❌ FAILED: Expected 401, got {response.status_code}")
                return False
        
        # Try with non-admin token
        print("🔒 Test 1b: Non-admin token (should get 403)...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{BACKEND_URL}/api/admin/skins",
                headers={"Authorization": f"Bearer {token}"}
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 403:
                print("   ✅ PASSED: Got 403 with non-admin token")
            else:
                print(f"   ❌ FAILED: Expected 403, got {response.status_code}")
                return False
        
        print()
        return True
        
    finally:
        await db.users.delete_one({"id": user_id})
        mongo_client.close()


async def test_get_skins_and_update_size():
    """Test 2-4: Get existing skin, update size, verify persistence."""
    print("=" * 80)
    print("TEST 2-4: Get Skin, Update Size, Verify Persistence")
    print("=" * 80)
    print()
    
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client[DB_NAME]
    
    try:
        # Setup admin user
        admin_user, admin_identifier, session_id = await setup_admin_user(db)
        admin_token = create_jwt_token(admin_identifier, session_id)
        
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json",
        }
        
        # Test 2: Get existing skins
        print("📋 Test 2: GET /api/admin/skins (get existing skin)...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{BACKEND_URL}/api/admin/skins",
                headers=headers
            )
            print(f"   Status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"   ❌ FAILED: Expected 200, got {response.status_code}")
                print(f"   Response: {response.text}")
                return False
            
            data = response.json()
            skins = data.get("skins", [])
            print(f"   ✅ Got {len(skins)} skins")
            
            if len(skins) == 0:
                print("   ⚠️  No skins found, creating one...")
                # Create a test skin
                create_response = await client.post(
                    f"{BACKEND_URL}/api/admin/skins",
                    headers=headers,
                    json={
                        "group_key": "test_group",
                        "group_name": "Test Group",
                        "business_type": "bio_farm",
                        "level": 0,
                        "image": "/sprites/test/test.webp",
                        "is_standard": False,
                    }
                )
                if create_response.status_code not in [200, 201]:
                    print(f"   ❌ Failed to create test skin: {create_response.status_code}")
                    return False
                
                skin = create_response.json().get("skin")
                print(f"   ✅ Created test skin: {skin.get('id')}")
            else:
                # Use first skin
                skin = skins[0]
                print(f"   ✅ Using skin: {skin.get('id')} ({skin.get('group_key')}/{skin.get('business_type')}/level {skin.get('level')})")
        
        skin_id = skin.get("id")
        print()
        
        # Test 3: Update skin size
        print(f"📐 Test 3: PATCH /api/admin/skins/{skin_id}/size...")
        print(f"   Setting height_pct=80, width_pct=120")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(
                f"{BACKEND_URL}/api/admin/skins/{skin_id}/size",
                headers=headers,
                json={
                    "height_pct": 80,
                    "width_pct": 120,
                }
            )
            print(f"   Status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"   ❌ FAILED: Expected 200, got {response.status_code}")
                print(f"   Response: {response.text}")
                return False
            
            data = response.json()
            updated_skin = data.get("skin")
            
            if updated_skin.get("height_pct") != 80 or updated_skin.get("width_pct") != 120:
                print(f"   ❌ FAILED: Size not updated correctly")
                print(f"   Got: height_pct={updated_skin.get('height_pct')}, width_pct={updated_skin.get('width_pct')}")
                return False
            
            print(f"   ✅ PASSED: Size updated successfully")
            print(f"   height_pct: {updated_skin.get('height_pct')}")
            print(f"   width_pct: {updated_skin.get('width_pct')}")
        print()
        
        # Test 4: Verify persistence
        print(f"💾 Test 4: Verify persistence (GET /api/admin/skins again)...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{BACKEND_URL}/api/admin/skins",
                headers=headers
            )
            
            if response.status_code != 200:
                print(f"   ❌ FAILED: Expected 200, got {response.status_code}")
                return False
            
            data = response.json()
            skins = data.get("skins", [])
            
            # Find our skin
            persisted_skin = next((s for s in skins if s.get("id") == skin_id), None)
            
            if not persisted_skin:
                print(f"   ❌ FAILED: Skin not found after update")
                return False
            
            if persisted_skin.get("height_pct") != 80 or persisted_skin.get("width_pct") != 120:
                print(f"   ❌ FAILED: Size not persisted correctly")
                print(f"   Got: height_pct={persisted_skin.get('height_pct')}, width_pct={persisted_skin.get('width_pct')}")
                return False
            
            print(f"   ✅ PASSED: Size persisted correctly")
            print(f"   height_pct: {persisted_skin.get('height_pct')}")
            print(f"   width_pct: {persisted_skin.get('width_pct')}")
        print()
        
        return True
        
    finally:
        mongo_client.close()


async def test_public_skins_index():
    """Test 5: GET /api/skins/index returns both index and sizes."""
    print("=" * 80)
    print("TEST 5: Public Skins Index with Sizes")
    print("=" * 80)
    print()
    
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client[DB_NAME]
    
    try:
        # Setup admin to update a skin first
        admin_user, admin_identifier, session_id = await setup_admin_user(db)
        admin_token = create_jwt_token(admin_identifier, session_id)
        
        admin_headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json",
        }
        
        # Get a skin and update its size
        print("📝 Setting up test data...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{BACKEND_URL}/api/admin/skins",
                headers=admin_headers
            )
            skins = response.json().get("skins", [])
            
            if len(skins) == 0:
                print("   ⚠️  No skins found, skipping test")
                return True
            
            # Update first skin with custom size
            skin = skins[0]
            skin_id = skin.get("id")
            
            await client.patch(
                f"{BACKEND_URL}/api/admin/skins/{skin_id}/size",
                headers=admin_headers,
                json={"height_pct": 80, "width_pct": 120}
            )
            print(f"   ✅ Updated skin {skin_id} with height_pct=80, width_pct=120")
        
        # Test public endpoint (no auth required)
        print("🌐 Test 5: GET /api/skins/index (public, no auth)...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{BACKEND_URL}/api/skins/index")
            print(f"   Status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"   ❌ FAILED: Expected 200, got {response.status_code}")
                print(f"   Response: {response.text}")
                return False
            
            data = response.json()
            
            # Check structure
            if "index" not in data:
                print(f"   ❌ FAILED: Missing 'index' in response")
                return False
            
            if "sizes" not in data:
                print(f"   ❌ FAILED: Missing 'sizes' in response")
                return False
            
            print(f"   ✅ PASSED: Response has both 'index' and 'sizes'")
            
            # Verify structure
            index = data.get("index", {})
            sizes = data.get("sizes", {})
            
            print(f"   Index groups: {list(index.keys())}")
            print(f"   Sizes groups: {list(sizes.keys())}")
            
            # Check that our updated skin is in the sizes map
            group_key = skin.get("group_key")
            business_type = skin.get("business_type")
            level = str(skin.get("level"))
            
            if group_key in sizes:
                if business_type in sizes[group_key]:
                    if level in sizes[group_key][business_type]:
                        size_data = sizes[group_key][business_type][level]
                        print(f"   ✅ Found updated skin in sizes map:")
                        print(f"      {group_key}/{business_type}/{level}: h={size_data.get('h')}, w={size_data.get('w')}")
                        
                        if size_data.get("h") == 80 and size_data.get("w") == 120:
                            print(f"   ✅ PASSED: Size values are correct")
                        else:
                            print(f"   ❌ FAILED: Size values incorrect (expected h=80, w=120)")
                            return False
            
            # Check default values (100, 100) for skins without custom size
            print(f"   Checking default values for skins without custom size...")
            found_default = False
            for gk in sizes:
                for bt in sizes[gk]:
                    for lvl in sizes[gk][bt]:
                        size_data = sizes[gk][bt][lvl]
                        if size_data.get("h") == 100 and size_data.get("w") == 100:
                            found_default = True
                            print(f"   ✅ Found default size (100, 100) for {gk}/{bt}/{lvl}")
                            break
                    if found_default:
                        break
                if found_default:
                    break
            
            if not found_default:
                print(f"   ⚠️  No skins with default size found (this is OK if all skins have custom sizes)")
        
        print()
        return True
        
    finally:
        mongo_client.close()


async def test_validation():
    """Test 6: Validation - values out of range should be rejected."""
    print("=" * 80)
    print("TEST 6: Validation (out of range values)")
    print("=" * 80)
    print()
    
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client[DB_NAME]
    
    try:
        # Setup admin user
        admin_user, admin_identifier, session_id = await setup_admin_user(db)
        admin_token = create_jwt_token(admin_identifier, session_id)
        
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json",
        }
        
        # Get a skin
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{BACKEND_URL}/api/admin/skins",
                headers=headers
            )
            skins = response.json().get("skins", [])
            
            if len(skins) == 0:
                print("   ⚠️  No skins found, skipping test")
                return True
            
            skin_id = skins[0].get("id")
        
        # Test 6a: height_pct below minimum (5 < 10)
        print("🚫 Test 6a: height_pct=5 (below min 10, should get 422)...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(
                f"{BACKEND_URL}/api/admin/skins/{skin_id}/size",
                headers=headers,
                json={"height_pct": 5, "width_pct": 100}
            )
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 422:
                print(f"   ✅ PASSED: Got 422 for value below minimum")
            else:
                print(f"   ❌ FAILED: Expected 422, got {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        
        # Test 6b: width_pct above maximum (500 > 400)
        print("🚫 Test 6b: width_pct=500 (above max 400, should get 422)...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(
                f"{BACKEND_URL}/api/admin/skins/{skin_id}/size",
                headers=headers,
                json={"height_pct": 100, "width_pct": 500}
            )
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 422:
                print(f"   ✅ PASSED: Got 422 for value above maximum")
            else:
                print(f"   ❌ FAILED: Expected 422, got {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        
        print()
        return True
        
    finally:
        mongo_client.close()


async def test_nonexistent_skin():
    """Test 7: Update non-existent skin should return 404."""
    print("=" * 80)
    print("TEST 7: Non-existent Skin (should get 404)")
    print("=" * 80)
    print()
    
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client[DB_NAME]
    
    try:
        # Setup admin user
        admin_user, admin_identifier, session_id = await setup_admin_user(db)
        admin_token = create_jwt_token(admin_identifier, session_id)
        
        headers = {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json",
        }
        
        # Use a non-existent skin ID
        fake_skin_id = str(uuid.uuid4())
        
        print(f"🔍 Test 7: PATCH non-existent skin {fake_skin_id}...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.patch(
                f"{BACKEND_URL}/api/admin/skins/{fake_skin_id}/size",
                headers=headers,
                json={"height_pct": 100, "width_pct": 100}
            )
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 404:
                data = response.json()
                detail = data.get("detail", "")
                print(f"   Detail: {detail}")
                
                if "Скин не найден" in detail:
                    print(f"   ✅ PASSED: Got 404 with correct error message")
                else:
                    print(f"   ⚠️  Got 404 but message is different: {detail}")
                    print(f"   (This is acceptable as long as it's 404)")
                return True
            else:
                print(f"   ❌ FAILED: Expected 404, got {response.status_code}")
                print(f"   Response: {response.text}")
                return False
        
    finally:
        mongo_client.close()


async def main():
    """Run all tests."""
    print()
    print("🚀 Starting Per-Skin Display SIZE Feature Tests")
    print()
    
    results = {}
    
    # Test 1: Admin auth required
    results["Admin Auth Required"] = await test_admin_auth()
    
    # Test 2-4: Get skin, update size, verify persistence
    results["Get/Update/Persist Size"] = await test_get_skins_and_update_size()
    
    # Test 5: Public skins index with sizes
    results["Public Index with Sizes"] = await test_public_skins_index()
    
    # Test 6: Validation
    results["Validation (out of range)"] = await test_validation()
    
    # Test 7: Non-existent skin
    results["Non-existent Skin 404"] = await test_nonexistent_skin()
    
    # Summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
    print()
    
    all_passed = all(results.values())
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("   The per-skin display SIZE feature is working correctly.")
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        print("   Please review the failed tests above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
