#!/bin/bash
# End-to-End Flow Test Script
#
# This script tests the complete outreach automation workflow:
# SmartLead Webhook → Contact → EmailReply → AI Categorization → Tasks → HubSpot → Teams
#
# Prerequisites:
# 1. docker-compose up -d (PostgreSQL, Redis)
# 2. celery -A app.workers.celery_app worker -l info -Q webhooks,categorization,hubspot,notifications
# 3. uvicorn app.main:app --reload
#
# Usage: ./scripts/test_e2e_flow.sh

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"
DELAY_BETWEEN_TESTS=2

echo "==================================="
echo "Outreach Automation E2E Test"
echo "==================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to make API call and check response
test_endpoint() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="$4"

    echo -e "${YELLOW}Testing: ${name}${NC}"
    echo "  Endpoint: ${method} ${endpoint}"

    if [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "${BASE_URL}${endpoint}" \
            -H "Content-Type: application/json" \
            -d "$data")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "${BASE_URL}${endpoint}")
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo -e "  ${GREEN}Status: ${http_code} OK${NC}"
        echo "  Response: ${body}"
    else
        echo -e "  ${RED}Status: ${http_code} FAILED${NC}"
        echo "  Response: ${body}"
        return 1
    fi
    echo ""
}

# Test 1: Health Check
echo "=== Step 1: Health Check ==="
test_endpoint "Health Check" "GET" "/health"
sleep $DELAY_BETWEEN_TESTS

# Test 2: SmartLead Webhook - Interested Lead (Schedule Call)
echo "=== Step 2: SmartLead Webhook - Interested Lead ==="
INTERESTED_PAYLOAD='{
    "event_type": "reply_received",
    "lead_id": "lead_'"$(date +%s)"'",
    "campaign_id": "campaign_001",
    "email": "interested_lead_'"$(date +%s)"'@example.com",
    "first_name": "John",
    "last_name": "Interested",
    "company_name": "Tech Corp",
    "reply_text": "Hi! I am very interested in your solution. Can we schedule a call for next week? My direct number is 555-1234.",
    "subject": "Re: Your Solution - Interested!"
}'
test_endpoint "SmartLead Webhook (Interested)" "POST" "/webhook/smartlead" "$INTERESTED_PAYLOAD"
sleep $DELAY_BETWEEN_TESTS

# Test 3: SmartLead Webhook - Referral
echo "=== Step 3: SmartLead Webhook - Referral ==="
REFERRAL_PAYLOAD='{
    "event_type": "reply_received",
    "lead_id": "lead_ref_'"$(date +%s)"'",
    "campaign_id": "campaign_002",
    "email": "referral_lead_'"$(date +%s)"'@example.com",
    "first_name": "Jane",
    "last_name": "Referrer",
    "company_name": "Innovation Inc",
    "reply_text": "Thanks for reaching out! I am not the right person but you should talk to Mike Johnson at mike@bigcorp.com - he handles this.",
    "subject": "Re: Introduction - Referral"
}'
test_endpoint "SmartLead Webhook (Referral)" "POST" "/webhook/smartlead" "$REFERRAL_PAYLOAD"
sleep $DELAY_BETWEEN_TESTS

# Test 4: SmartLead Webhook - Not Interested (Busy)
echo "=== Step 4: SmartLead Webhook - Not Now (Busy) ==="
BUSY_PAYLOAD='{
    "event_type": "reply_received",
    "lead_id": "lead_busy_'"$(date +%s)"'",
    "campaign_id": "campaign_003",
    "email": "busy_lead_'"$(date +%s)"'@example.com",
    "first_name": "Bob",
    "last_name": "Busy",
    "company_name": "Startup XYZ",
    "reply_text": "Thanks but we are in the middle of a big project right now. Maybe reach out again in Q2?",
    "subject": "Re: Your Service"
}'
test_endpoint "SmartLead Webhook (Not Now - Busy)" "POST" "/webhook/smartlead" "$BUSY_PAYLOAD"
sleep $DELAY_BETWEEN_TESTS

# Test 5: SmartLead Webhook - Out of Office
echo "=== Step 5: SmartLead Webhook - Out of Office ==="
OOO_PAYLOAD='{
    "event_type": "reply_received",
    "lead_id": "lead_ooo_'"$(date +%s)"'",
    "campaign_id": "campaign_004",
    "email": "ooo_lead_'"$(date +%s)"'@example.com",
    "first_name": "Sarah",
    "last_name": "Away",
    "company_name": "Travel Corp",
    "reply_text": "I am out of the office until January 30th with limited access to email. I will respond to your message when I return.",
    "subject": "Out of Office: Re: Your Solution"
}'
test_endpoint "SmartLead Webhook (Out of Office)" "POST" "/webhook/smartlead" "$OOO_PAYLOAD"
sleep $DELAY_BETWEEN_TESTS

# Test 6: ConnectSafely Webhook
echo "=== Step 6: ConnectSafely Webhook ==="
LINKEDIN_PAYLOAD='{
    "event_type": "connection_accepted",
    "profile_url": "https://linkedin.com/in/johndoe",
    "email": "interested_lead_'"$(date +%s)"'@example.com",
    "connection_status": "accepted"
}'
test_endpoint "ConnectSafely Webhook" "POST" "/webhook/connectsafely" "$LINKEDIN_PAYLOAD"

echo "==================================="
echo "E2E Tests Complete!"
echo "==================================="
echo ""
echo "Next steps to verify full flow:"
echo "1. Check Celery worker logs for task processing"
echo "2. Query database to verify Contact and EmailReply records"
echo "3. Check HubSpot for synced contacts and tasks"
echo "4. Check MS Teams channel for notifications"
echo ""
echo "Database queries (run in psql):"
echo "  SELECT * FROM contacts ORDER BY created_at DESC LIMIT 10;"
echo "  SELECT * FROM email_replies ORDER BY created_at DESC LIMIT 10;"
echo "  SELECT * FROM tasks ORDER BY created_at DESC LIMIT 10;"
echo ""
