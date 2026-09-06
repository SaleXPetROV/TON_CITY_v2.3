#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: "Test the new REFERRAL-INCOME destination rule in the GRAM CITY backend."

backend:
  - task: "Referral Income Destination Rule (Level-Based)"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: |
          TESTED AND VERIFIED - All referral income destination rules working correctly.
          
          Feature: Referral income (5% of market sale) is now credited to the correct balance
          based on the SELLER's SOURCE business level:
            • level 0 (staked/not upgraded) OR no business → referrer's BONUS balance
            • level >= 1                                    → referrer's REAL balance
          
          The referrer's OWN business level is IRRELEVANT (correctly implemented).
          
          Test Results (4 test cases, all passed):
          ✅ Case A: Seller with level-0 business → Referrer BONUS balance
             - Referrer bonus_balance increased by 0.5 TON (5% of 10 TON sale)
             - Referrer balance_ton unchanged
             - Transaction record: to_balance="bonus"
             - totalReferralBonusEarned increased by 0.5 TON
          
          ✅ Case B: Seller with level-1 business → Referrer REAL balance
             - Referrer balance_ton increased by 0.5 TON
             - Referrer bonus_balance unchanged
             - Transaction record: to_balance="real"
             - totalEarnedFromReferrals increased by 0.5 TON
          
          ✅ Case C: Referrer's own business level is IRRELEVANT
             - Referrer has level-0 business, seller has level-1 business
             - Income correctly went to referrer's REAL balance (based on seller's level-1)
             - Proves referrer's own business level does NOT affect destination
          
          ✅ Case D: No source business → Referrer BONUS balance
             - Listing with business_id=None
             - Income correctly went to referrer's BONUS balance
          
          Implementation verified:
          - Function: apply_referral_tax_split() at line 7131
          - Helper: _resolve_referral_source_to_bonus() at line 7112
          - Market buy endpoint: POST /api/market/buy at line 4082 (line 4334)
          - Admin buyout path: line 13173
          - Transaction records include "to_balance" field ("bonus" or "real")
          
          Test script: /app/backend_test_referral_income.py
          
          All endpoints and logic working as specified. Feature is production-ready.

backend:
  - task: "Telegram User Buy Island Plot - User Resolution Fix"
    implemented: true
    working: true
    file: "backend/routes/ton_island.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: |
          TESTED AND VERIFIED - Bug fix is working correctly.
          
          The bug: POST /api/island/buy/{x}/{y} previously returned 404 "Пользователь не найден" 
          for Telegram Mini App users who have NO wallet_address and NO email (identified only by id).
          
          The fix: Endpoint now resolves users primarily by current_user.id, then falls back to 
          wallet_address/email (lines 375-383).
          
          Test Results:
          ✅ Telegram user (id-only): Got 423 presale_locked - USER WAS FOUND
          ✅ Email user (backward compat): Got 423 presale_locked - USER WAS FOUND
          ✅ Telegram admin (end-to-end): 200 OK - Purchase successful
          
          All tests passed. The "Пользователь не найден" error is completely resolved.

  - task: "Telegram User Build on Island Plot - User Resolution Fix"
    implemented: true
    working: true
    file: "backend/routes/ton_island.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: |
          TESTED AND VERIFIED - Bug fix is working correctly.
          
          The same fix was applied to POST /api/island/build/{x}/{y} endpoint (lines 707-714).
          
          Test Results:
          ✅ Telegram user build: Got 400 business type error - USER WAS FOUND
          
          The endpoint correctly resolves Telegram users by id before falling back to wallet/email.

  - task: "Per-Skin Display SIZE Feature"
    implemented: true
    working: true
    file: "backend/routes/skins.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "testing"
        comment: |
          TESTED AND VERIFIED - All features working correctly.
          
          New Features Tested:
          1. PATCH /api/admin/skins/{skin_id}/size - Admin-only endpoint to set height_pct and width_pct (10-400 range)
          2. GET /api/skins/index - Now returns both "index" and "sizes" maps
          
          Test Results (7 tests, all passed):
          ✅ Admin authentication required (401 without token, 403 with non-admin token)
          ✅ Get existing skin via GET /api/admin/skins
          ✅ Update skin size via PATCH with height_pct=80, width_pct=120
          ✅ Size values persisted correctly in database
          ✅ Public GET /api/skins/index returns both "index" and "sizes" maps
          ✅ Updated skin shows correct size values (h=80, w=120) in sizes map
          ✅ Unset skins default to h=100, w=100
          ✅ Validation: height_pct=5 (below min) returns 422
          ✅ Validation: width_pct=500 (above max) returns 422
          ✅ Non-existent skin ID returns 404 "Скин не найден"
          
          All endpoints working as specified. Test script: /app/backend_test_skin_size.py

metadata:
  created_by: "testing_agent"
  version: "1.0"
  test_sequence: 3
  run_ui: false
  last_updated: "2025-01-XX"

test_plan:
  current_focus:
    - "Referral Income Destination Rule (Level-Based)"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "testing"
    message: |
      ✅ TESTING COMPLETE - REFERRAL-INCOME destination rule fully working!
      
      Tested the new referral income destination logic that routes income to bonus vs real
      balance based on the SELLER's SOURCE business level.
      
      All 4 test cases passed:
      1. ✅ Level-0 business → Bonus balance (0.5 TON to bonus_balance, totalReferralBonusEarned)
      2. ✅ Level-1 business → Real balance (0.5 TON to balance_ton, totalEarnedFromReferrals)
      3. ✅ Referrer's own level-0 business did NOT affect destination (seller's level-1 → real)
      4. ✅ No business → Bonus balance (business_id=None → bonus_balance)
      
      Key findings:
      - apply_referral_tax_split() correctly calls _resolve_referral_source_to_bonus()
      - _resolve_referral_source_to_bonus() checks SOURCE business level (not referrer's)
      - Transaction records include "to_balance" field ("bonus" or "real")
      - Both market buy (line 4334) and admin buyout (line 13173) use the same logic
      - Referrer's own business level is correctly IRRELEVANT
      
      Test script: /app/backend_test_referral_income.py
      
      No issues found. Feature is production-ready.
