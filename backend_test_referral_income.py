#!/usr/bin/env python3
"""
Test script for GRAM CITY REFERRAL-INCOME destination rule.

Tests that referral income (5% of market sale) is credited to the correct balance
(bonus vs real) based on the SELLER's SOURCE business level:
  - level 0 (staked/not upgraded) OR no business → referrer's BONUS balance
  - level >= 1                                    → referrer's REAL balance

The referrer's OWN business level must be IRRELEVANT.
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

# Load backend URL from frontend .env
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
    """Create a JWT token for a user (mimics auth_handler.create_token)."""
    from datetime import timedelta
    payload = {
        "sub": identifier,  # email, username, or wallet_address
        "exp": (datetime.now(timezone.utc) + timedelta(days=30)).timestamp(),
    }
    if session_id:
        payload["sid"] = session_id
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def create_test_user(db, username, email=None, balance_ton=1000.0, bonus_balance=0.0, referrer_id=None, create_business=False):
    """Create a test user in the database."""
    user_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    
    user = {
        "id": user_id,
        "username": username,
        "display_name": username,
        "email": email,
        "wallet_address": None,
        "raw_address": None,
        "hashed_password": None,
        "avatar": {"type": "initials", "initials": username[:2].upper(), "color": "#6366f1"},
        "balance_ton": balance_ton,
        "bonus_balance": bonus_balance,
        "language": "en",
        "level": 1,
        "xp": 0,
        "total_turnover": 0,
        "total_income": 0,
        "totalEarnedFromReferrals": 0.0,
        "totalReferralBonusEarned": 0.0,
        "contributedToReferrer": 0.0,
        "referrerId": referrer_id,
        "resources": {},
        "plots_owned": [],
        "businesses_owned": [],
        "is_admin": False,
        "email_verified": True,
        "registration_method": "email",
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_login": datetime.now(timezone.utc).isoformat(),
    }
    
    await db.users.insert_one(user)
    
    # Create a business for the user if requested (needed for buyers to access market)
    if create_business:
        await create_test_business(db, user_id, level=1)
    
    return user_id, session_id


async def create_test_business(db, owner_id, level=0, business_type="data_center"):
    """Create a test business."""
    business_id = str(uuid.uuid4())
    
    business = {
        "id": business_id,
        "owner": owner_id,
        "business_type": business_type,
        "level": level,
        "is_zero_business": (level == 0),
        "x": 10,
        "y": 10,
        "island_id": "ton_island",
        "status": "active",
        "storage": {
            "capacity": 1000,  # Give sufficient warehouse capacity
            "used": 0,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    await db.businesses.insert_one(business)
    return business_id


async def create_market_listing(db, seller_id, seller_email, business_id, resource_type="chips", amount=100, price_per_unit=0.1):
    """Create a market listing."""
    listing_id = str(uuid.uuid4())
    
    listing = {
        "id": listing_id,
        "seller_id": seller_id,
        "seller_email": seller_email,
        "business_id": business_id,
        "resource_type": resource_type,
        "amount": amount,
        "price_per_unit": price_per_unit,
        "total_price": amount * price_per_unit,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    await db.market_listings.insert_one(listing)
    return listing_id


async def get_user_balances(db, user_id):
    """Get user's balance_ton, bonus_balance, totalEarnedFromReferrals, totalReferralBonusEarned."""
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "balance_ton": 1, "bonus_balance": 1, 
                                                       "totalEarnedFromReferrals": 1, "totalReferralBonusEarned": 1})
    if not user:
        return None
    return {
        "balance_ton": float(user.get("balance_ton", 0) or 0),
        "bonus_balance": float(user.get("bonus_balance", 0) or 0),
        "totalEarnedFromReferrals": float(user.get("totalEarnedFromReferrals", 0) or 0),
        "totalReferralBonusEarned": float(user.get("totalReferralBonusEarned", 0) or 0),
    }


async def test_case_a_level0_business():
    """
    Case A: Seller S0 has a level-0 business B0. Referrer R should receive income in BONUS balance.
    """
    print("=" * 80)
    print("TEST CASE A: Seller with Level-0 Business → Referrer BONUS Balance")
    print("=" * 80)
    print()
    
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client[DB_NAME]
    
    try:
        # Create users
        print("📝 Step 1: Creating test users...")
        referrer_id, _ = await create_test_user(db, f"referrer_a_{uuid.uuid4().hex[:6]}", f"referrer_a_{uuid.uuid4().hex[:6]}@test.com")
        seller_id, _ = await create_test_user(db, f"seller_a_{uuid.uuid4().hex[:6]}", f"seller_a_{uuid.uuid4().hex[:6]}@test.com", referrer_id=referrer_id)
        buyer_id, buyer_session = await create_test_user(db, f"buyer_a_{uuid.uuid4().hex[:6]}", f"buyer_a_{uuid.uuid4().hex[:6]}@test.com", balance_ton=1000.0, create_business=True)
        print(f"   ✅ Referrer: {referrer_id}")
        print(f"   ✅ Seller (referral): {seller_id}")
        print(f"   ✅ Buyer: {buyer_id}")
        print()
        
        # Create level-0 business for seller
        print("📝 Step 2: Creating level-0 business for seller...")
        business_id = await create_test_business(db, seller_id, level=0)
        print(f"   ✅ Business: {business_id} (level=0, is_zero_business=true)")
        print()
        
        # Give seller some resources
        print("📝 Step 3: Giving seller resources...")
        await db.users.update_one({"id": seller_id}, {"$set": {"resources.chips": 100}})
        print(f"   ✅ Seller has 100 chips")
        print()
        
        # Get initial balances
        print("📝 Step 4: Recording initial balances...")
        initial_ref = await get_user_balances(db, referrer_id)
        print(f"   Referrer initial: balance_ton={initial_ref['balance_ton']}, bonus_balance={initial_ref['bonus_balance']}")
        print(f"                     totalEarnedFromReferrals={initial_ref['totalEarnedFromReferrals']}, totalReferralBonusEarned={initial_ref['totalReferralBonusEarned']}")
        print()
        
        # Create market listing
        print("📝 Step 5: Creating market listing...")
        seller_user = await db.users.find_one({"id": seller_id}, {"_id": 0, "email": 1})
        listing_id = await create_market_listing(db, seller_id, seller_user["email"], business_id, "chips", 10, 1.0)
        print(f"   ✅ Listing: {listing_id} (10 chips @ 1.0 TON each = 10 TON total)")
        print()
        
        # Buyer purchases
        print("📝 Step 6: Buyer purchasing from market...")
        buyer_user = await db.users.find_one({"id": buyer_id}, {"_id": 0, "username": 1})
        token = create_jwt_token(buyer_user["username"], buyer_session)
        
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/api/market/buy",
                headers=headers,
                json={"listing_id": listing_id, "amount": 10}
            )
            
            print(f"   Response Status: {response.status_code}")
            if response.status_code not in [200, 201]:
                print(f"   ❌ Purchase failed: {response.text}")
                return False
            print(f"   ✅ Purchase successful")
        print()
        
        # Check final balances
        print("📝 Step 7: Checking final balances...")
        await asyncio.sleep(1)  # Give DB time to update
        final_ref = await get_user_balances(db, referrer_id)
        print(f"   Referrer final: balance_ton={final_ref['balance_ton']}, bonus_balance={final_ref['bonus_balance']}")
        print(f"                   totalEarnedFromReferrals={final_ref['totalEarnedFromReferrals']}, totalReferralBonusEarned={final_ref['totalReferralBonusEarned']}")
        print()
        
        # Calculate expected referral amount (5% of 10 TON = 0.5 TON, capped to seller tax)
        expected_referral = 0.5  # 5% of 10 TON
        
        # Verify
        print("📊 Verification:")
        bonus_increase = final_ref['bonus_balance'] - initial_ref['bonus_balance']
        real_increase = final_ref['balance_ton'] - initial_ref['balance_ton']
        bonus_earned_increase = final_ref['totalReferralBonusEarned'] - initial_ref['totalReferralBonusEarned']
        real_earned_increase = final_ref['totalEarnedFromReferrals'] - initial_ref['totalEarnedFromReferrals']
        
        print(f"   Bonus balance increase: {bonus_increase} TON")
        print(f"   Real balance increase: {real_increase} TON")
        print(f"   totalReferralBonusEarned increase: {bonus_earned_increase} TON")
        print(f"   totalEarnedFromReferrals increase: {real_earned_increase} TON")
        print()
        
        # Check transaction record
        print("📝 Step 8: Checking transaction record...")
        tx = await db.transactions.find_one(
            {"tx_type": "referral_income", "user_id": referrer_id},
            {"_id": 0, "to_balance": 1, "amount_ton": 1},
            sort=[("created_at", -1)]
        )
        if tx:
            print(f"   ✅ Transaction found: to_balance={tx.get('to_balance')}, amount_ton={tx.get('amount_ton')}")
        else:
            print(f"   ❌ No referral_income transaction found")
        print()
        
        # Assertions
        if bonus_increase > 0 and real_increase == 0 and tx and tx.get("to_balance") == "bonus":
            print("✅ CASE A PASSED: Referral income went to BONUS balance (level-0 business)")
            return True
        else:
            print("❌ CASE A FAILED:")
            if bonus_increase <= 0:
                print(f"   - Bonus balance did not increase (expected ~{expected_referral}, got {bonus_increase})")
            if real_increase != 0:
                print(f"   - Real balance increased (expected 0, got {real_increase})")
            if not tx or tx.get("to_balance") != "bonus":
                print(f"   - Transaction to_balance is not 'bonus' (got {tx.get('to_balance') if tx else 'N/A'})")
            return False
    
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        print()
        print("🧹 Cleanup...")
        try:
            await db.users.delete_many({"id": {"$in": [referrer_id, seller_id, buyer_id]}})
            await db.businesses.delete_many({"owner": {"$in": [referrer_id, seller_id, buyer_id]}})
            await db.market_listings.delete_many({"seller_id": {"$in": [referrer_id, seller_id, buyer_id]}})
            await db.transactions.delete_many({"user_id": {"$in": [referrer_id, seller_id, buyer_id]}})
            print("   ✅ Cleanup complete")
        except Exception as e:
            print(f"   ⚠️  Cleanup failed: {e}")
        finally:
            mongo_client.close()


async def test_case_b_level1_business():
    """
    Case B: Seller S1 has a level-1 business B1. Referrer R should receive income in REAL balance.
    """
    print()
    print("=" * 80)
    print("TEST CASE B: Seller with Level-1 Business → Referrer REAL Balance")
    print("=" * 80)
    print()
    
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client[DB_NAME]
    
    try:
        # Create users
        print("📝 Step 1: Creating test users...")
        referrer_id, _ = await create_test_user(db, f"referrer_b_{uuid.uuid4().hex[:6]}", f"referrer_b_{uuid.uuid4().hex[:6]}@test.com")
        seller_id, _ = await create_test_user(db, f"seller_b_{uuid.uuid4().hex[:6]}", f"seller_b_{uuid.uuid4().hex[:6]}@test.com", referrer_id=referrer_id)
        buyer_id, buyer_session = await create_test_user(db, f"buyer_b_{uuid.uuid4().hex[:6]}", f"buyer_b_{uuid.uuid4().hex[:6]}@test.com", balance_ton=1000.0, create_business=True)
        print(f"   ✅ Referrer: {referrer_id}")
        print(f"   ✅ Seller (referral): {seller_id}")
        print(f"   ✅ Buyer: {buyer_id}")
        print()
        
        # Create level-1 business for seller
        print("📝 Step 2: Creating level-1 business for seller...")
        business_id = await create_test_business(db, seller_id, level=1)
        print(f"   ✅ Business: {business_id} (level=1)")
        print()
        
        # Give seller some resources
        print("📝 Step 3: Giving seller resources...")
        await db.users.update_one({"id": seller_id}, {"$set": {"resources.chips": 100}})
        print(f"   ✅ Seller has 100 chips")
        print()
        
        # Get initial balances
        print("📝 Step 4: Recording initial balances...")
        initial_ref = await get_user_balances(db, referrer_id)
        print(f"   Referrer initial: balance_ton={initial_ref['balance_ton']}, bonus_balance={initial_ref['bonus_balance']}")
        print(f"                     totalEarnedFromReferrals={initial_ref['totalEarnedFromReferrals']}, totalReferralBonusEarned={initial_ref['totalReferralBonusEarned']}")
        print()
        
        # Create market listing
        print("📝 Step 5: Creating market listing...")
        seller_user = await db.users.find_one({"id": seller_id}, {"_id": 0, "email": 1})
        listing_id = await create_market_listing(db, seller_id, seller_user["email"], business_id, "chips", 10, 1.0)
        print(f"   ✅ Listing: {listing_id} (10 chips @ 1.0 TON each = 10 TON total)")
        print()
        
        # Buyer purchases
        print("📝 Step 6: Buyer purchasing from market...")
        buyer_user = await db.users.find_one({"id": buyer_id}, {"_id": 0, "username": 1})
        token = create_jwt_token(buyer_user["username"], buyer_session)
        
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/api/market/buy",
                headers=headers,
                json={"listing_id": listing_id, "amount": 10}
            )
            
            print(f"   Response Status: {response.status_code}")
            if response.status_code not in [200, 201]:
                print(f"   ❌ Purchase failed: {response.text}")
                return False
            print(f"   ✅ Purchase successful")
        print()
        
        # Check final balances
        print("📝 Step 7: Checking final balances...")
        await asyncio.sleep(1)  # Give DB time to update
        final_ref = await get_user_balances(db, referrer_id)
        print(f"   Referrer final: balance_ton={final_ref['balance_ton']}, bonus_balance={final_ref['bonus_balance']}")
        print(f"                   totalEarnedFromReferrals={final_ref['totalEarnedFromReferrals']}, totalReferralBonusEarned={final_ref['totalReferralBonusEarned']}")
        print()
        
        # Verify
        print("📊 Verification:")
        bonus_increase = final_ref['bonus_balance'] - initial_ref['bonus_balance']
        real_increase = final_ref['balance_ton'] - initial_ref['balance_ton']
        bonus_earned_increase = final_ref['totalReferralBonusEarned'] - initial_ref['totalReferralBonusEarned']
        real_earned_increase = final_ref['totalEarnedFromReferrals'] - initial_ref['totalEarnedFromReferrals']
        
        print(f"   Bonus balance increase: {bonus_increase} TON")
        print(f"   Real balance increase: {real_increase} TON")
        print(f"   totalReferralBonusEarned increase: {bonus_earned_increase} TON")
        print(f"   totalEarnedFromReferrals increase: {real_earned_increase} TON")
        print()
        
        # Check transaction record
        print("📝 Step 8: Checking transaction record...")
        tx = await db.transactions.find_one(
            {"tx_type": "referral_income", "user_id": referrer_id},
            {"_id": 0, "to_balance": 1, "amount_ton": 1},
            sort=[("created_at", -1)]
        )
        if tx:
            print(f"   ✅ Transaction found: to_balance={tx.get('to_balance')}, amount_ton={tx.get('amount_ton')}")
        else:
            print(f"   ❌ No referral_income transaction found")
        print()
        
        # Assertions
        if real_increase > 0 and bonus_increase == 0 and tx and tx.get("to_balance") == "real":
            print("✅ CASE B PASSED: Referral income went to REAL balance (level-1 business)")
            return True
        else:
            print("❌ CASE B FAILED:")
            if real_increase <= 0:
                print(f"   - Real balance did not increase (expected >0, got {real_increase})")
            if bonus_increase != 0:
                print(f"   - Bonus balance increased (expected 0, got {bonus_increase})")
            if not tx or tx.get("to_balance") != "real":
                print(f"   - Transaction to_balance is not 'real' (got {tx.get('to_balance') if tx else 'N/A'})")
            return False
    
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        print()
        print("🧹 Cleanup...")
        try:
            await db.users.delete_many({"id": {"$in": [referrer_id, seller_id, buyer_id]}})
            await db.businesses.delete_many({"owner": {"$in": [referrer_id, seller_id, buyer_id]}})
            await db.market_listings.delete_many({"seller_id": {"$in": [referrer_id, seller_id, buyer_id]}})
            await db.transactions.delete_many({"user_id": {"$in": [referrer_id, seller_id, buyer_id]}})
            print("   ✅ Cleanup complete")
        except Exception as e:
            print(f"   ⚠️  Cleanup failed: {e}")
        finally:
            mongo_client.close()


async def test_case_c_referrer_level_irrelevant():
    """
    Case C: Referrer R has a level-0 business, but seller S1 has level-1 business.
    Income should STILL go to R's REAL balance (referrer's own level is irrelevant).
    """
    print()
    print("=" * 80)
    print("TEST CASE C: Referrer's Own Business Level is IRRELEVANT")
    print("=" * 80)
    print()
    
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client[DB_NAME]
    
    try:
        # Create users
        print("📝 Step 1: Creating test users...")
        referrer_id, _ = await create_test_user(db, f"referrer_c_{uuid.uuid4().hex[:6]}", f"referrer_c_{uuid.uuid4().hex[:6]}@test.com")
        seller_id, _ = await create_test_user(db, f"seller_c_{uuid.uuid4().hex[:6]}", f"seller_c_{uuid.uuid4().hex[:6]}@test.com", referrer_id=referrer_id)
        buyer_id, buyer_session = await create_test_user(db, f"buyer_c_{uuid.uuid4().hex[:6]}", f"buyer_c_{uuid.uuid4().hex[:6]}@test.com", balance_ton=1000.0, create_business=True)
        print(f"   ✅ Referrer: {referrer_id}")
        print(f"   ✅ Seller (referral): {seller_id}")
        print(f"   ✅ Buyer: {buyer_id}")
        print()
        
        # Create level-0 business for REFERRER (should be irrelevant)
        print("📝 Step 2: Creating level-0 business for REFERRER...")
        referrer_business_id = await create_test_business(db, referrer_id, level=0)
        print(f"   ✅ Referrer's Business: {referrer_business_id} (level=0) - should be IRRELEVANT")
        print()
        
        # Create level-1 business for SELLER
        print("📝 Step 3: Creating level-1 business for SELLER...")
        seller_business_id = await create_test_business(db, seller_id, level=1)
        print(f"   ✅ Seller's Business: {seller_business_id} (level=1) - this determines destination")
        print()
        
        # Give seller some resources
        print("📝 Step 4: Giving seller resources...")
        await db.users.update_one({"id": seller_id}, {"$set": {"resources.chips": 100}})
        print(f"   ✅ Seller has 100 chips")
        print()
        
        # Get initial balances
        print("📝 Step 5: Recording initial balances...")
        initial_ref = await get_user_balances(db, referrer_id)
        print(f"   Referrer initial: balance_ton={initial_ref['balance_ton']}, bonus_balance={initial_ref['bonus_balance']}")
        print()
        
        # Create market listing
        print("📝 Step 6: Creating market listing...")
        seller_user = await db.users.find_one({"id": seller_id}, {"_id": 0, "email": 1})
        listing_id = await create_market_listing(db, seller_id, seller_user["email"], seller_business_id, "chips", 10, 1.0)
        print(f"   ✅ Listing: {listing_id} (from seller's level-1 business)")
        print()
        
        # Buyer purchases
        print("📝 Step 7: Buyer purchasing from market...")
        buyer_user = await db.users.find_one({"id": buyer_id}, {"_id": 0, "username": 1})
        token = create_jwt_token(buyer_user["username"], buyer_session)
        
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/api/market/buy",
                headers=headers,
                json={"listing_id": listing_id, "amount": 10}
            )
            
            print(f"   Response Status: {response.status_code}")
            if response.status_code not in [200, 201]:
                print(f"   ❌ Purchase failed: {response.text}")
                return False
            print(f"   ✅ Purchase successful")
        print()
        
        # Check final balances
        print("📝 Step 8: Checking final balances...")
        await asyncio.sleep(1)
        final_ref = await get_user_balances(db, referrer_id)
        print(f"   Referrer final: balance_ton={final_ref['balance_ton']}, bonus_balance={final_ref['bonus_balance']}")
        print()
        
        # Verify
        print("📊 Verification:")
        bonus_increase = final_ref['bonus_balance'] - initial_ref['bonus_balance']
        real_increase = final_ref['balance_ton'] - initial_ref['balance_ton']
        
        print(f"   Bonus balance increase: {bonus_increase} TON")
        print(f"   Real balance increase: {real_increase} TON")
        print()
        
        # Check transaction
        tx = await db.transactions.find_one(
            {"tx_type": "referral_income", "user_id": referrer_id},
            {"_id": 0, "to_balance": 1},
            sort=[("created_at", -1)]
        )
        if tx:
            print(f"   Transaction to_balance: {tx.get('to_balance')}")
        print()
        
        # Assertions: Should go to REAL balance (seller's level-1 business determines it)
        if real_increase > 0 and bonus_increase == 0 and tx and tx.get("to_balance") == "real":
            print("✅ CASE C PASSED: Referrer's own level-0 business did NOT affect destination")
            print("   Income correctly went to REAL balance based on SELLER's level-1 business")
            return True
        else:
            print("❌ CASE C FAILED:")
            print("   Referrer's own business level incorrectly affected the destination")
            return False
    
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        print()
        print("🧹 Cleanup...")
        try:
            await db.users.delete_many({"id": {"$in": [referrer_id, seller_id, buyer_id]}})
            await db.businesses.delete_many({"owner": {"$in": [referrer_id, seller_id, buyer_id]}})
            await db.market_listings.delete_many({"seller_id": {"$in": [referrer_id, seller_id, buyer_id]}})
            await db.transactions.delete_many({"user_id": {"$in": [referrer_id, seller_id, buyer_id]}})
            print("   ✅ Cleanup complete")
        except Exception as e:
            print(f"   ⚠️  Cleanup failed: {e}")
        finally:
            mongo_client.close()


async def test_case_d_no_business():
    """
    Case D: Seller has NO business (business_id is None/missing).
    Income should go to referrer's BONUS balance.
    """
    print()
    print("=" * 80)
    print("TEST CASE D: No Source Business → Referrer BONUS Balance")
    print("=" * 80)
    print()
    
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client[DB_NAME]
    
    try:
        # Create users
        print("📝 Step 1: Creating test users...")
        referrer_id, _ = await create_test_user(db, f"referrer_d_{uuid.uuid4().hex[:6]}", f"referrer_d_{uuid.uuid4().hex[:6]}@test.com")
        seller_id, _ = await create_test_user(db, f"seller_d_{uuid.uuid4().hex[:6]}", f"seller_d_{uuid.uuid4().hex[:6]}@test.com", referrer_id=referrer_id)
        buyer_id, buyer_session = await create_test_user(db, f"buyer_d_{uuid.uuid4().hex[:6]}", f"buyer_d_{uuid.uuid4().hex[:6]}@test.com", balance_ton=1000.0, create_business=True)
        print(f"   ✅ Referrer: {referrer_id}")
        print(f"   ✅ Seller (referral): {seller_id}")
        print(f"   ✅ Buyer: {buyer_id}")
        print()
        
        # Give seller some resources (no business)
        print("📝 Step 2: Giving seller resources (NO business)...")
        await db.users.update_one({"id": seller_id}, {"$set": {"resources.chips": 100}})
        print(f"   ✅ Seller has 100 chips, NO business")
        print()
        
        # Get initial balances
        print("📝 Step 3: Recording initial balances...")
        initial_ref = await get_user_balances(db, referrer_id)
        print(f"   Referrer initial: balance_ton={initial_ref['balance_ton']}, bonus_balance={initial_ref['bonus_balance']}")
        print()
        
        # Create market listing with NO business_id
        print("📝 Step 4: Creating market listing (business_id=None)...")
        seller_user = await db.users.find_one({"id": seller_id}, {"_id": 0, "email": 1})
        listing_id = await create_market_listing(db, seller_id, seller_user["email"], None, "chips", 10, 1.0)
        print(f"   ✅ Listing: {listing_id} (NO business_id)")
        print()
        
        # Buyer purchases
        print("📝 Step 5: Buyer purchasing from market...")
        buyer_user = await db.users.find_one({"id": buyer_id}, {"_id": 0, "username": 1})
        token = create_jwt_token(buyer_user["username"], buyer_session)
        
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BACKEND_URL}/api/market/buy",
                headers=headers,
                json={"listing_id": listing_id, "amount": 10}
            )
            
            print(f"   Response Status: {response.status_code}")
            if response.status_code not in [200, 201]:
                print(f"   ❌ Purchase failed: {response.text}")
                return False
            print(f"   ✅ Purchase successful")
        print()
        
        # Check final balances
        print("📝 Step 6: Checking final balances...")
        await asyncio.sleep(1)
        final_ref = await get_user_balances(db, referrer_id)
        print(f"   Referrer final: balance_ton={final_ref['balance_ton']}, bonus_balance={final_ref['bonus_balance']}")
        print()
        
        # Verify
        print("📊 Verification:")
        bonus_increase = final_ref['bonus_balance'] - initial_ref['bonus_balance']
        real_increase = final_ref['balance_ton'] - initial_ref['balance_ton']
        
        print(f"   Bonus balance increase: {bonus_increase} TON")
        print(f"   Real balance increase: {real_increase} TON")
        print()
        
        # Check transaction
        tx = await db.transactions.find_one(
            {"tx_type": "referral_income", "user_id": referrer_id},
            {"_id": 0, "to_balance": 1},
            sort=[("created_at", -1)]
        )
        if tx:
            print(f"   Transaction to_balance: {tx.get('to_balance')}")
        print()
        
        # Assertions
        if bonus_increase > 0 and real_increase == 0 and tx and tx.get("to_balance") == "bonus":
            print("✅ CASE D PASSED: No business → income went to BONUS balance")
            return True
        else:
            print("❌ CASE D FAILED:")
            return False
    
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        print()
        print("🧹 Cleanup...")
        try:
            await db.users.delete_many({"id": {"$in": [referrer_id, seller_id, buyer_id]}})
            await db.businesses.delete_many({"owner": {"$in": [referrer_id, seller_id, buyer_id]}})
            await db.market_listings.delete_many({"seller_id": {"$in": [referrer_id, seller_id, buyer_id]}})
            await db.transactions.delete_many({"user_id": {"$in": [referrer_id, seller_id, buyer_id]}})
            print("   ✅ Cleanup complete")
        except Exception as e:
            print(f"   ⚠️  Cleanup failed: {e}")
        finally:
            mongo_client.close()


async def main():
    """Run all test cases."""
    print()
    print("🚀 Starting REFERRAL-INCOME Destination Rule Tests")
    print()
    
    # Run all test cases
    test_a = await test_case_a_level0_business()
    test_b = await test_case_b_level1_business()
    test_c = await test_case_c_referrer_level_irrelevant()
    test_d = await test_case_d_no_business()
    
    # Summary
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Case A (Level-0 Business → Bonus): {'✅ PASSED' if test_a else '❌ FAILED'}")
    print(f"Case B (Level-1 Business → Real):  {'✅ PASSED' if test_b else '❌ FAILED'}")
    print(f"Case C (Referrer Level Irrelevant): {'✅ PASSED' if test_c else '❌ FAILED'}")
    print(f"Case D (No Business → Bonus):       {'✅ PASSED' if test_d else '❌ FAILED'}")
    print()
    
    if all([test_a, test_b, test_c, test_d]):
        print("🎉 ALL TESTS PASSED!")
        print("   The REFERRAL-INCOME destination rule is working correctly.")
        return 0
    else:
        print("❌ SOME TESTS FAILED!")
        print("   The referral income destination logic may have issues.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
