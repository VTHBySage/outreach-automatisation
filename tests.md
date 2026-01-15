# Comprehensive Test Scenarios

This document contains hypothetical test scenarios for all functions mentioned in Requirements.md. Each test monitors inputs and outputs to validate system behavior.

---

## Table of Contents
1. [Campaign Setup & Lead Validation](#1-campaign-setup--lead-validation)
2. [Webhook Handlers](#2-webhook-handlers)
3. [AI Response Categorization](#3-ai-response-categorization-26-subcategories)
4. [HubSpot Task Generation](#4-hubspot-task-generation)
5. [MS Teams Notifications](#5-ms-teams-notifications)
6. [LinkedIn Integration](#6-linkedin-integration)
7. [HubSpot CRM Integration](#7-hubspot-crm-integration)
8. [Re-engagement Pipeline](#8-re-engagement-pipeline)
9. [Referral Auto-Campaign](#9-referral-auto-campaign)
10. [Performance Requirements](#10-performance-requirements)
11. [Monitoring & Metrics](#11-monitoring--metrics)
12. [Error Handling & Retry](#12-error-handling--retry)
13. [Compliance](#13-compliance)

---

## 1. Campaign Setup & Lead Validation

### CS-001: Apollo.io Contact Search
**Function:** `ApolloClient.search_people()`
**File:** `app/integrations/apollo/client.py`

**Hypothetical Input:**
```json
{
  "email": "john.smith@hiltonhotels.com",
  "first_name": "John",
  "last_name": "Smith",
  "organization_name": "Hilton Hotels"
}
```

**Expected Output:**
```json
{
  "people": [
    {
      "id": "apollo_123456",
      "first_name": "John",
      "last_name": "Smith",
      "email": "john.smith@hiltonhotels.com",
      "email_status": "valid",
      "title": "VP of Operations",
      "linkedin_url": "https://linkedin.com/in/johnsmith",
      "organization": {
        "name": "Hilton Hotels",
        "primary_domain": "hilton.com",
        "industry": "Hospitality"
      }
    }
  ]
}
```

**Validation:** Email accuracy >= 91% as per Requirements.md

---

### CS-002: Apollo.io Company Enrichment
**Function:** `ApolloClient.enrich_organization()`
**File:** `app/integrations/apollo/client.py`

**Hypothetical Input:**
```json
{
  "domain": "marriott.com"
}
```

**Expected Output:**
```json
{
  "organization": {
    "id": "org_789",
    "name": "Marriott International",
    "primary_domain": "marriott.com",
    "industry": "Hospitality",
    "estimated_num_employees": 121000,
    "founded_year": 1927,
    "phone": "+1-301-380-3000",
    "linkedin_url": "https://linkedin.com/company/marriott-international",
    "technologies": ["Salesforce", "Oracle", "SAP"]
  }
}
```

---

### CS-003: HeyReach LinkedIn Enrichment
**Function:** `HeyReachClient.enrich_contact()`
**File:** `app/integrations/heyreach/client.py`

**Hypothetical Input:**
```json
{
  "email": "sarah.jones@ihg.com"
}
```

**Expected Output:**
```json
{
  "profile": {
    "linkedin_url": "https://linkedin.com/in/sarahjones",
    "first_name": "Sarah",
    "last_name": "Jones",
    "headline": "Director of Risk Management at IHG",
    "location": "Atlanta, GA",
    "connections": 2500,
    "company": "InterContinental Hotels Group"
  },
  "enrichment_source": "heyreach"
}
```

---

### CS-004: Web Crawler Company Page
**Function:** `WebCrawlerClient.crawl()`
**File:** `app/integrations/webcrawler/client.py`

**Hypothetical Input:**
```json
{
  "url": "https://www.hyatt.com/about"
}
```

**Expected Output:**
```json
{
  "title": "About Hyatt Hotels",
  "description": "Hyatt Hotels Corporation, headquartered in Chicago, is a leading global hospitality company...",
  "content": "World of Hyatt is a global hospitality brand offering luxury accommodations, resorts, and all-inclusive properties...",
  "meta_keywords": ["hotels", "hospitality", "luxury", "resorts"],
  "industry_signals": ["hospitality", "hotels", "lodging"],
  "crawl_success": true
}
```

---

### CS-005: LLM Account Validation
**Function:** `ValidationService.validate_company()`
**File:** `app/services/validation/service.py`

**Hypothetical Input:**
```json
{
  "company_name": "Grand Hyatt Singapore",
  "website_content": "Grand Hyatt Singapore is a luxury hotel located in the heart of Singapore...",
  "campaign_criteria": "Hotel Chain (NOT Airbnb/vacation rental)"
}
```

**Expected Output:**
```json
{
  "is_valid": true,
  "company_type": "Hotel Chain",
  "confidence": 0.92,
  "reasoning": "Company operates as a luxury hotel brand under the Hyatt international chain, with corporate structure and multiple properties.",
  "validation_status": "validated"
}
```

**Validation:** Confidence >= 85% required for automatic inclusion

---

### CS-006: Manual Review Queue (75-85% Confidence)
**Function:** `ValidationService.validate_company()`
**File:** `app/services/validation/service.py`

**Hypothetical Input:**
```json
{
  "company_name": "Boutique Inn & Suites",
  "website_content": "Family-owned bed and breakfast offering cozy rooms...",
  "campaign_criteria": "Hotel Chain (NOT Airbnb/vacation rental)"
}
```

**Expected Output:**
```json
{
  "is_valid": null,
  "company_type": "Boutique Hotel / B&B",
  "confidence": 0.78,
  "reasoning": "Property appears to be an independent boutique hotel but could also be a B&B. Unclear if it meets chain hotel criteria.",
  "validation_status": "pending_review",
  "review_reason": "Confidence between 75-85%, manual review required"
}
```

---

### CS-007: Data Enrichment Combination
**Function:** `EnrichmentService.combine_sources()`
**File:** `app/services/enrichment/service.py`

**Hypothetical Input:**
```json
{
  "apollo_data": {
    "email": "mike.wilson@wyndham.com",
    "title": "Insurance Manager",
    "phone": "+1-555-0100"
  },
  "heyreach_data": {
    "linkedin_url": "https://linkedin.com/in/mikewilson",
    "headline": "Risk & Insurance Manager at Wyndham Hotels",
    "connections": 1500
  }
}
```

**Expected Output:**
```json
{
  "email": "mike.wilson@wyndham.com",
  "title": "Insurance Manager",
  "phone": "+1-555-0100",
  "linkedin_url": "https://linkedin.com/in/mikewilson",
  "linkedin_headline": "Risk & Insurance Manager at Wyndham Hotels",
  "linkedin_connections": 1500,
  "enrichment_sources": ["apollo", "heyreach"],
  "data_completeness": 0.95
}
```

---

## 2. Webhook Handlers

### WH-001: SmartLead EMAIL_REPLY
**Endpoint:** `POST /webhook/smartlead`
**File:** `app/api/webhooks/smartlead.py`

**Hypothetical Input:**
```json
{
  "event_type": "EMAIL_REPLY",
  "lead_email": "prospect@acmehotels.com",
  "campaign_id": "camp_123",
  "message_id": "msg_456",
  "reply_text": "Thanks for reaching out! I'd love to learn more about your insurance services. Can we schedule a call next week?",
  "reply_timestamp": "2024-01-15T10:30:00Z",
  "thread_history": [
    {"sender": "outreach@company.com", "text": "Hi, I wanted to discuss...", "timestamp": "2024-01-14T09:00:00Z"}
  ]
}
```

**Expected Output:**
```json
{
  "status": "accepted",
  "task_id": "celery_task_789",
  "actions_triggered": [
    "categorization_queued",
    "hubspot_contact_update",
    "metrics_recorded"
  ]
}
```

**Side Effects:**
- Celery task queued for AI categorization
- Contact status updated in database
- Email reply counter incremented

---

### WH-002: SmartLead EMAIL_OPENED
**Endpoint:** `POST /webhook/smartlead`
**File:** `app/api/webhooks/smartlead.py`

**Hypothetical Input:**
```json
{
  "event_type": "EMAIL_OPENED",
  "lead_email": "buyer@luxuryresorts.com",
  "campaign_id": "camp_456",
  "message_id": "msg_789",
  "open_timestamp": "2024-01-15T14:22:00Z",
  "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X)",
  "ip_address": "203.0.113.50"
}
```

**Expected Output:**
```json
{
  "status": "accepted",
  "metrics_updated": {
    "email_opens_total": "incremented",
    "campaign_id": "camp_456"
  }
}
```

---

### WH-003: SmartLead EMAIL_CLICKED
**Endpoint:** `POST /webhook/smartlead`
**File:** `app/api/webhooks/smartlead.py`

**Hypothetical Input:**
```json
{
  "event_type": "EMAIL_CLICKED",
  "lead_email": "manager@hotelchain.com",
  "campaign_id": "camp_123",
  "message_id": "msg_111",
  "clicked_url": "https://ourcompany.com/insurance-solutions",
  "click_timestamp": "2024-01-15T16:45:00Z"
}
```

**Expected Output:**
```json
{
  "status": "accepted",
  "metrics_updated": {
    "email_clicks_total": "incremented",
    "clicked_url": "https://ourcompany.com/insurance-solutions"
  }
}
```

---

### WH-004: SmartLead EMAIL_BOUNCED
**Endpoint:** `POST /webhook/smartlead`
**File:** `app/api/webhooks/smartlead.py`

**Hypothetical Input:**
```json
{
  "event_type": "EMAIL_BOUNCED",
  "lead_email": "oldemail@defunct-hotel.com",
  "campaign_id": "camp_789",
  "bounce_type": "hard",
  "bounce_reason": "550 5.1.1 User unknown",
  "bounce_timestamp": "2024-01-15T08:00:00Z"
}
```

**Expected Output:**
```json
{
  "status": "accepted",
  "contact_status": "bounced",
  "actions_triggered": [
    "contact_suppressed",
    "hubspot_updated",
    "task_created_permanent_suppression"
  ]
}
```

---

### WH-005: SmartLead EMAIL_UNSUBSCRIBED
**Endpoint:** `POST /webhook/smartlead`
**File:** `app/api/webhooks/smartlead.py`

**Hypothetical Input:**
```json
{
  "event_type": "EMAIL_UNSUBSCRIBED",
  "lead_email": "noemail@optout-hotel.com",
  "campaign_id": "camp_111",
  "unsubscribe_timestamp": "2024-01-15T12:00:00Z",
  "unsubscribe_reason": "clicked_unsubscribe_link"
}
```

**Expected Output:**
```json
{
  "status": "accepted",
  "contact_status": "unsubscribed",
  "actions_triggered": [
    "immediate_suppression",
    "all_campaigns_removed",
    "smartlead_blocklist_added",
    "hubspot_dnc_flagged"
  ],
  "compliance_timestamp": "2024-01-15T12:00:00Z"
}
```

---

### WH-006: SmartLead HMAC Signature Validation
**Endpoint:** `POST /webhook/smartlead`
**File:** `app/api/webhooks/smartlead.py`

**Hypothetical Input (Valid Signature):**
```
Headers:
  X-Smartlead-Signature: sha256=a1b2c3d4e5f6...
  Content-Type: application/json

Body:
{
  "event_type": "EMAIL_REPLY",
  "lead_email": "test@hotel.com"
}
```

**Expected Output (Valid):**
```json
{
  "status": "accepted"
}
```

**Hypothetical Input (Invalid Signature):**
```
Headers:
  X-Smartlead-Signature: sha256=invalid_signature
```

**Expected Output (Invalid):**
```json
{
  "status": 401,
  "error": "Invalid webhook signature"
}
```

---

### WH-007: ConnectSafely connection_accepted
**Endpoint:** `POST /webhook/connectsafely`
**File:** `app/api/webhooks/connectsafely.py`

**Hypothetical Input:**
```json
{
  "event_type": "connection_accepted",
  "profile_url": "https://linkedin.com/in/hotelexec",
  "contact_email": "exec@grandhotel.com",
  "accepted_timestamp": "2024-01-15T09:30:00Z"
}
```

**Expected Output:**
```json
{
  "status": "accepted",
  "contact_linkedin_status": "connected",
  "next_actions": [
    "dm_draft_created",
    "task_created_send_dm"
  ]
}
```

---

### WH-008: ConnectSafely connection_rejected
**Endpoint:** `POST /webhook/connectsafely`
**File:** `app/api/webhooks/connectsafely.py`

**Hypothetical Input:**
```json
{
  "event_type": "connection_rejected",
  "profile_url": "https://linkedin.com/in/busyexec",
  "contact_email": "busy@hotel.com",
  "rejected_timestamp": "2024-01-15T11:00:00Z"
}
```

**Expected Output:**
```json
{
  "status": "accepted",
  "contact_linkedin_status": "rejected",
  "actions_triggered": [
    "logged_rejection",
    "re_engagement_scheduled_90_days"
  ]
}
```

---

### WH-009: ConnectSafely message_received
**Endpoint:** `POST /webhook/connectsafely`
**File:** `app/api/webhooks/connectsafely.py`

**Hypothetical Input:**
```json
{
  "event_type": "message_received",
  "profile_url": "https://linkedin.com/in/hotelcfo",
  "contact_email": "cfo@luxurychain.com",
  "message_text": "Thanks for connecting! We're actually looking for new insurance providers. Let's talk.",
  "message_timestamp": "2024-01-15T14:00:00Z"
}
```

**Expected Output:**
```json
{
  "status": "accepted",
  "task_id": "celery_linkedin_cat_123",
  "actions_triggered": [
    "linkedin_categorization_queued",
    "source_marked_linkedin"
  ]
}
```

---

### WH-010: HeyReach connection_accepted
**Endpoint:** `POST /webhook/heyreach`
**File:** `app/api/webhooks/heyreach.py`

**Hypothetical Input:**
```json
{
  "event_type": "connection_accepted",
  "linkedin_url": "https://linkedin.com/in/hotelops",
  "contact_email": "ops@chainhotel.com",
  "campaign_id": "heyreach_camp_456",
  "timestamp": "2024-01-15T10:15:00Z"
}
```

**Expected Output:**
```json
{
  "status": "accepted",
  "contact_status": "linkedin_connected",
  "workflow_triggered": "dm_sequence_start"
}
```

---

### WH-011: HeyReach message_received
**Endpoint:** `POST /webhook/heyreach`
**File:** `app/api/webhooks/heyreach.py`

**Hypothetical Input:**
```json
{
  "event_type": "message_received",
  "linkedin_url": "https://linkedin.com/in/insurancemgr",
  "contact_email": "insurance@megahotel.com",
  "message_text": "Please reach out to our VP of Risk, Sarah at sarah@megahotel.com. She handles all insurance.",
  "timestamp": "2024-01-15T15:30:00Z"
}
```

**Expected Output:**
```json
{
  "status": "accepted",
  "categorization_result": {
    "main_category": "POSITIVE_SIGNALS",
    "subcategory": "REFERRAL"
  },
  "referral_detected": {
    "name": "Sarah",
    "email": "sarah@megahotel.com",
    "title": "VP of Risk"
  }
}
```

---

## 3. AI Response Categorization (26 Subcategories)

### Category 1: INTERESTED

#### CAT-101: Ready to Chat (Phone Number)
**Function:** `CategorizationService.categorize()`
**File:** `app/services/categorization/service.py`

**Hypothetical Input:**
```json
{
  "reply_text": "This sounds interesting! Feel free to give me a call at 555-123-4567 to discuss further.",
  "contact_email": "interested@hotel.com",
  "context": {
    "campaign_type": "insurance_outreach",
    "previous_emails": 2
  }
}
```

**Expected Output:**
```json
{
  "main_category": "INTERESTED",
  "subcategory": "READY_TO_CHAT_PHONE",
  "confidence": 0.95,
  "reasoning": "Prospect explicitly provided phone number and expressed interest in discussing.",
  "extracted_data": {
    "phone_number": "555-123-4567"
  },
  "suggested_followup_date": null,
  "referral_info": null
}
```

---

#### CAT-102: Intrigued
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "What kind of coverage options do you offer? And what are your pricing tiers for mid-size hotel chains?",
  "contact_email": "curious@resorts.com"
}
```

**Expected Output:**
```json
{
  "main_category": "INTERESTED",
  "subcategory": "INTRIGUED",
  "confidence": 0.91,
  "reasoning": "Prospect asking specific questions about coverage and pricing indicates genuine interest.",
  "extracted_data": {
    "questions_asked": ["coverage options", "pricing tiers"]
  }
}
```

---

#### CAT-103: Ready to Chat (Open)
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "Sure, let's set up a call to discuss. What times work for you next week?",
  "contact_email": "ready@luxurychain.com"
}
```

**Expected Output:**
```json
{
  "main_category": "INTERESTED",
  "subcategory": "READY_TO_CHAT_OPEN",
  "confidence": 0.97,
  "reasoning": "Prospect explicitly agrees to schedule a call and asks for availability."
}
```

---

#### CAT-104: Connect with Another Person
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "I'm not the right person for this. Please contact Sarah Johnson in our Dallas office - she handles all insurance matters.",
  "contact_email": "wrongperson@hotelcorp.com"
}
```

**Expected Output:**
```json
{
  "main_category": "INTERESTED",
  "subcategory": "CONNECT_ANOTHER",
  "confidence": 0.88,
  "reasoning": "Prospect redirecting to colleague indicates interest at company level.",
  "referral_info": {
    "name": "Sarah Johnson",
    "location": "Dallas office",
    "role": "insurance matters"
  }
}
```

---

#### CAT-105: Misunderstood Interested
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "Yes, we're interested! Although I thought you were offering property insurance, not liability coverage. Can you clarify?",
  "contact_email": "confused@hotel.com"
}
```

**Expected Output:**
```json
{
  "main_category": "INTERESTED",
  "subcategory": "MISUNDERSTOOD_INTERESTED",
  "confidence": 0.85,
  "reasoning": "Prospect shows interest but has misunderstanding about product/service."
}
```

---

#### CAT-106: Long-term Followup
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "This is interesting but our current policy renews in September. Reach back out to me in Q3 and we can discuss then.",
  "contact_email": "future@hotelgroup.com"
}
```

**Expected Output:**
```json
{
  "main_category": "INTERESTED",
  "subcategory": "LONG_TERM_FOLLOWUP",
  "confidence": 0.92,
  "reasoning": "Prospect interested but wants contact at specific future date.",
  "suggested_followup_date": "2024-07-01",
  "extracted_timing": "Q3"
}
```

---

#### CAT-107: Prospect Pitching Own Service
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "Interesting timing! We also offer insurance consulting services to hotels. Perhaps we could partner or refer business to each other?",
  "contact_email": "competitor@insuranceservices.com"
}
```

**Expected Output:**
```json
{
  "main_category": "INTERESTED",
  "subcategory": "PITCHING_SERVICE",
  "confidence": 0.89,
  "reasoning": "Prospect is in related industry and proposing partnership rather than buying."
}
```

---

### Category 2: POSITIVE_SIGNALS

#### CAT-201: Referral
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "You should contact John Smith at ABC Hotels - he's looking for exactly this kind of coverage. His email is john.smith@abchotels.com",
  "contact_email": "helpful@hotel.com"
}
```

**Expected Output:**
```json
{
  "main_category": "POSITIVE_SIGNALS",
  "subcategory": "REFERRAL",
  "confidence": 0.96,
  "reasoning": "Prospect providing specific contact information for potential buyer.",
  "referral_info": {
    "name": "John Smith",
    "email": "john.smith@abchotels.com",
    "company": "ABC Hotels"
  }
}
```

---

#### CAT-202: Competitor Mention
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "We're currently using Allstate for our coverage. What makes your offering different?",
  "contact_email": "comparing@resort.com"
}
```

**Expected Output:**
```json
{
  "main_category": "POSITIVE_SIGNALS",
  "subcategory": "COMPETITOR_MENTION",
  "confidence": 0.87,
  "reasoning": "Prospect revealing current provider and asking for differentiation.",
  "competitor_mentioned": "Allstate"
}
```

---

#### CAT-203: Budget Confirmed
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "We have about $50,000 allocated annually for insurance. Does your pricing fit within that range?",
  "contact_email": "budgeted@hotelchain.com"
}
```

**Expected Output:**
```json
{
  "main_category": "POSITIVE_SIGNALS",
  "subcategory": "BUDGET_CONFIRMED",
  "confidence": 0.93,
  "reasoning": "Prospect confirming specific budget allocation.",
  "budget_mentioned": "$50,000 annually"
}
```

---

#### CAT-204: Authority Confirmed
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "As the VP of Risk Management, I'm the one who makes the final decision on insurance providers. Send me more details.",
  "contact_email": "decisionmaker@megahotel.com"
}
```

**Expected Output:**
```json
{
  "main_category": "POSITIVE_SIGNALS",
  "subcategory": "AUTHORITY_CONFIRMED",
  "confidence": 0.94,
  "reasoning": "Prospect confirming decision-making authority for insurance.",
  "authority_title": "VP of Risk Management"
}
```

---

### Category 3: NOT_INTERESTED

#### CAT-301: Mistake / Wrong Company
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "I think there's been a mistake. We're a residential property management company, not a hotel chain.",
  "contact_email": "wrongfit@residential.com"
}
```

**Expected Output:**
```json
{
  "main_category": "NOT_INTERESTED",
  "subcategory": "WRONG_COMPANY",
  "confidence": 0.91,
  "reasoning": "Contact indicates company doesn't match target criteria."
}
```

---

#### CAT-302: Not Interested
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "No thanks, we're not interested at this time.",
  "contact_email": "notinterested@hotel.com"
}
```

**Expected Output:**
```json
{
  "main_category": "NOT_INTERESTED",
  "subcategory": "NOT_INTERESTED",
  "confidence": 0.95,
  "reasoning": "Clear rejection without specific reason given."
}
```

---

#### CAT-303: Self Disqualify
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "We're too small for this kind of coverage - we only have 3 rooms and handle everything ourselves.",
  "contact_email": "toosmall@boutique.com"
}
```

**Expected Output:**
```json
{
  "main_category": "NOT_INTERESTED",
  "subcategory": "SELF_DISQUALIFY",
  "confidence": 0.88,
  "reasoning": "Prospect indicating they don't meet size/criteria requirements.",
  "disqualification_reason": "too small (3 rooms)"
}
```

---

#### CAT-304: Misunderstood Not Interested
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "No, we don't need this. I thought you were asking about health insurance for employees, not property coverage.",
  "contact_email": "misunderstood@hotel.com"
}
```

**Expected Output:**
```json
{
  "main_category": "NOT_INTERESTED",
  "subcategory": "MISUNDERSTOOD_NOT_INTERESTED",
  "confidence": 0.82,
  "reasoning": "Prospect declining based on misunderstanding of offering."
}
```

---

#### CAT-305: Unsubscribe
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "Please remove me from your mailing list. Do not contact me again.",
  "contact_email": "unsubscribe@hotel.com"
}
```

**Expected Output:**
```json
{
  "main_category": "NOT_INTERESTED",
  "subcategory": "UNSUBSCRIBE",
  "confidence": 0.99,
  "reasoning": "Explicit unsubscribe/do not contact request.",
  "compliance_action": "immediate_suppression_required"
}
```

---

### Category 4: NEGATIVE_SIGNALS

#### CAT-401: Happy with Competitor
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "We're very satisfied with our current provider, StateFarm. They've been excellent for the past 10 years.",
  "contact_email": "satisfied@resort.com"
}
```

**Expected Output:**
```json
{
  "main_category": "NEGATIVE_SIGNALS",
  "subcategory": "HAPPY_WITH_COMPETITOR",
  "confidence": 0.92,
  "reasoning": "Prospect expressing satisfaction with existing provider.",
  "competitor_mentioned": "StateFarm",
  "relationship_duration": "10 years"
}
```

---

#### CAT-402: Recent Purchase
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "We just renewed our policy last month for the next 3 years. Try us again when it's up for renewal.",
  "contact_email": "justrenewed@hotelchain.com"
}
```

**Expected Output:**
```json
{
  "main_category": "NEGATIVE_SIGNALS",
  "subcategory": "RECENT_PURCHASE",
  "confidence": 0.94,
  "reasoning": "Prospect recently committed to competitor for extended period.",
  "re_engagement_date": "2027-01-15",
  "contract_length": "3 years"
}
```

---

#### CAT-403: Wrong Timing
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "This isn't a good time - we're in the middle of a merger. Contact me after Q2 when things settle down.",
  "contact_email": "busy@merging-hotel.com"
}
```

**Expected Output:**
```json
{
  "main_category": "NEGATIVE_SIGNALS",
  "subcategory": "WRONG_TIMING",
  "confidence": 0.90,
  "reasoning": "Prospect indicating temporary unavailability due to business circumstances.",
  "suggested_followup_date": "2024-07-01",
  "timing_reason": "merger"
}
```

---

### Category 5: AUTOMATE_REPLY

#### CAT-501: Out of Office
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "I am out of the office until March 15, 2024 with limited access to email. For urgent matters, please contact support@company.com.",
  "contact_email": "ooo@hotel.com"
}
```

**Expected Output:**
```json
{
  "main_category": "AUTOMATE_REPLY",
  "subcategory": "OUT_OF_OFFICE",
  "confidence": 0.99,
  "reasoning": "Standard out of office auto-reply detected.",
  "return_date": "2024-03-15",
  "alternate_contact": "support@company.com"
}
```

---

#### CAT-502: No Longer Works Here
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "John Smith no longer works at this company. He left 6 months ago. Please update your records.",
  "contact_email": "former@hotel.com"
}
```

**Expected Output:**
```json
{
  "main_category": "AUTOMATE_REPLY",
  "subcategory": "NO_LONGER_WORKS_HERE",
  "confidence": 0.97,
  "reasoning": "Contact no longer employed at target company.",
  "action_required": "research_new_contact"
}
```

---

#### CAT-503: Auto Acknowledge
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "[Auto-Reply] Thank you for your message. It has been received and will be reviewed shortly.",
  "contact_email": "autoreply@hotel.com"
}
```

**Expected Output:**
```json
{
  "main_category": "AUTOMATE_REPLY",
  "subcategory": "AUTO_ACKNOWLEDGE",
  "confidence": 0.98,
  "reasoning": "Automated acknowledgment system reply - no human action taken."
}
```

---

#### CAT-504: Auto Forward
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "Your message has been automatically forwarded to our procurement department for review.",
  "contact_email": "forwarded@hotel.com"
}
```

**Expected Output:**
```json
{
  "main_category": "AUTOMATE_REPLY",
  "subcategory": "AUTO_FORWARD",
  "confidence": 0.93,
  "reasoning": "Message forwarded to different department automatically."
}
```

---

#### CAT-505: Auto Reply Connect with Someone Else
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "[Automatic Response] For insurance inquiries, please contact our Risk Management team at risk@hotel.com",
  "contact_email": "redirect@hotel.com"
}
```

**Expected Output:**
```json
{
  "main_category": "AUTOMATE_REPLY",
  "subcategory": "AUTO_REPLY_CONNECT",
  "confidence": 0.91,
  "reasoning": "Automated redirect to appropriate department.",
  "redirect_contact": "risk@hotel.com"
}
```

---

#### CAT-506: Empty Reply
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "",
  "contact_email": "empty@hotel.com"
}
```

**Expected Output:**
```json
{
  "main_category": "AUTOMATE_REPLY",
  "subcategory": "EMPTY_REPLY",
  "confidence": 0.99,
  "reasoning": "Empty or blank reply received."
}
```

---

#### CAT-507: Hard Bounce
**Function:** `CategorizationService.categorize()`

**Hypothetical Input:**
```json
{
  "reply_text": "550 5.1.1 The email account that you tried to reach does not exist.",
  "contact_email": "nonexistent@hotel.com",
  "is_bounce": true
}
```

**Expected Output:**
```json
{
  "main_category": "AUTOMATE_REPLY",
  "subcategory": "HARD_BOUNCE",
  "confidence": 0.99,
  "reasoning": "Email address does not exist - permanent delivery failure.",
  "action_required": "permanent_suppression"
}
```

---

## 4. HubSpot Task Generation

### TASK-001: Interested Lead → Review Task
**Function:** `TaskService.create_tasks_for_category()`
**File:** `app/services/tasks/service.py`

**Hypothetical Input:**
```json
{
  "categorization": {
    "main_category": "INTERESTED",
    "subcategory": "READY_TO_CHAT_PHONE"
  },
  "contact": {
    "email": "interested@hotel.com",
    "hubspot_id": "hs_123",
    "name": "John Smith",
    "company": "Grand Hotel"
  }
}
```

**Expected Output:**
```json
{
  "tasks_created": [
    {
      "type": "Review Interested Reply",
      "priority": "HIGH",
      "due_date": "2024-01-15T23:59:59Z",
      "hubspot_task_id": "task_456",
      "assigned_to": "sales_team"
    }
  ]
}
```

---

### TASK-002: Interested → LinkedIn Task
**Function:** `TaskService.create_tasks_for_category()`

**Hypothetical Input:**
```json
{
  "categorization": {
    "main_category": "INTERESTED",
    "subcategory": "INTRIGUED"
  },
  "contact": {
    "email": "curious@resort.com",
    "linkedin_url": "https://linkedin.com/in/curious"
  }
}
```

**Expected Output:**
```json
{
  "tasks_created": [
    {
      "type": "LinkedIn Connection Request and DM",
      "priority": "HIGH",
      "due_date": "2024-01-15T23:59:59Z",
      "draft_message": "Hi [Name], thanks for your interest in our insurance solutions..."
    }
  ]
}
```

---

### TASK-003: Ready to Chat → Appointment Task
**Function:** `TaskService.create_tasks_for_category()`

**Hypothetical Input:**
```json
{
  "categorization": {
    "main_category": "INTERESTED",
    "subcategory": "READY_TO_CHAT_OPEN"
  },
  "contact": {
    "email": "ready@chain.com",
    "timezone": "America/New_York"
  }
}
```

**Expected Output:**
```json
{
  "tasks_created": [
    {
      "type": "Send appointment suggestion and HubSpot calendar link",
      "priority": "HIGH",
      "due_date": "2024-01-15T23:59:59Z",
      "meeting_link": "https://meetings.hubspot.com/company/discovery",
      "suggested_times": ["2024-01-17T10:00:00-05:00", "2024-01-17T14:00:00-05:00"]
    }
  ]
}
```

---

### TASK-004: Connect Another → Internal Assignment
**Function:** `TaskService.create_tasks_for_category()`

**Hypothetical Input:**
```json
{
  "categorization": {
    "main_category": "INTERESTED",
    "subcategory": "CONNECT_ANOTHER"
  },
  "referral_info": {
    "name": "Sarah Johnson",
    "location": "Dallas office"
  }
}
```

**Expected Output:**
```json
{
  "tasks_created": [
    {
      "type": "Internal Colleague Assignment",
      "priority": "HIGH",
      "description": "Route to appropriate team member for Sarah Johnson in Dallas office"
    }
  ]
}
```

---

### TASK-005: Long-term → Nurture
**Function:** `TaskService.create_tasks_for_category()`

**Hypothetical Input:**
```json
{
  "categorization": {
    "main_category": "INTERESTED",
    "subcategory": "LONG_TERM_FOLLOWUP"
  },
  "suggested_followup_date": "2024-09-01"
}
```

**Expected Output:**
```json
{
  "tasks_created": [
    {
      "type": "Prepare 90-Day Nurture Content",
      "priority": "LOW",
      "due_date": "2024-01-22T23:59:59Z"
    }
  ],
  "contact_updates": {
    "re_engagement_date": "2024-09-01"
  }
}
```

---

### TASK-006: Referral → Create Contact Record (HIGHEST)
**Function:** `TaskService.create_tasks_for_category()`

**Hypothetical Input:**
```json
{
  "categorization": {
    "main_category": "POSITIVE_SIGNALS",
    "subcategory": "REFERRAL"
  },
  "referral_info": {
    "name": "John Smith",
    "email": "john@abchotels.com",
    "company": "ABC Hotels"
  }
}
```

**Expected Output:**
```json
{
  "tasks_created": [
    {
      "type": "Create Referral Contact Record",
      "priority": "HIGHEST",
      "due_date": "2024-01-15T12:00:00Z",
      "referral_data": {
        "name": "John Smith",
        "email": "john@abchotels.com"
      }
    }
  ]
}
```

---

### TASK-007: Referral → Follow-up Immediately (HIGHEST)
**Function:** `TaskService.create_tasks_for_category()`

**Hypothetical Input:**
```json
{
  "categorization": {
    "main_category": "POSITIVE_SIGNALS",
    "subcategory": "REFERRAL"
  },
  "referral_contact_created": true,
  "referrer": {
    "name": "Original Contact",
    "company": "Referring Hotel"
  }
}
```

**Expected Output:**
```json
{
  "tasks_created": [
    {
      "type": "Follow-up Referral Immediately",
      "priority": "HIGHEST",
      "due_date": "2024-01-15T12:00:00Z",
      "message_template": "Hi John, [Original Contact] at Referring Hotel suggested I reach out..."
    }
  ]
}
```

---

### TASK-008: Not Interested → 90-Day Nurture
**Function:** `TaskService.create_tasks_for_category()`

**Hypothetical Input:**
```json
{
  "categorization": {
    "main_category": "NOT_INTERESTED",
    "subcategory": "NOT_INTERESTED"
  }
}
```

**Expected Output:**
```json
{
  "tasks_created": [
    {
      "type": "Schedule 90-Day Nurture Email",
      "priority": "LOW",
      "due_date": "2024-01-22T23:59:59Z"
    }
  ],
  "contact_updates": {
    "re_engagement_date": "2024-04-15"
  }
}
```

---

### TASK-009: Wrong Contact → Apollo Research
**Function:** `TaskService.create_tasks_for_category()`

**Hypothetical Input:**
```json
{
  "categorization": {
    "main_category": "NOT_INTERESTED",
    "subcategory": "WRONG_COMPANY"
  }
}
```

**Expected Output:**
```json
{
  "tasks_created": [
    {
      "type": "Apollo Research Correct Contact",
      "priority": "LOW",
      "due_date": "2024-01-22T23:59:59Z",
      "action": "Use Apollo to find correct contact at company"
    }
  ]
}
```

---

### TASK-010: Negative Signals → 180-Day Re-engagement
**Function:** `TaskService.create_tasks_for_category()`

**Hypothetical Input:**
```json
{
  "categorization": {
    "main_category": "NEGATIVE_SIGNALS",
    "subcategory": "HAPPY_WITH_COMPETITOR"
  }
}
```

**Expected Output:**
```json
{
  "tasks_created": [
    {
      "type": "Schedule 180-Day Re-engagement Review",
      "priority": "LOW"
    }
  ],
  "contact_updates": {
    "re_engagement_date": "2024-07-15"
  }
}
```

---

### TASK-011: Recent Purchase → Track Renewal
**Function:** `TaskService.create_tasks_for_category()`

**Hypothetical Input:**
```json
{
  "categorization": {
    "main_category": "NEGATIVE_SIGNALS",
    "subcategory": "RECENT_PURCHASE"
  },
  "contract_info": {
    "length": "3 years",
    "start_date": "2024-01-01"
  }
}
```

**Expected Output:**
```json
{
  "tasks_created": [
    {
      "type": "Track Contract Renewal Date",
      "priority": "LOW",
      "renewal_date": "2027-01-01"
    }
  ],
  "contact_updates": {
    "re_engagement_date": "2026-10-01"
  }
}
```

---

### TASK-012: Hard Bounce → Permanent Suppression
**Function:** `TaskService.create_tasks_for_category()`

**Hypothetical Input:**
```json
{
  "categorization": {
    "main_category": "AUTOMATE_REPLY",
    "subcategory": "HARD_BOUNCE"
  }
}
```

**Expected Output:**
```json
{
  "tasks_created": [
    {
      "type": "Permanent Email Suppression",
      "priority": "LOW",
      "auto_complete": true
    }
  ],
  "contact_updates": {
    "email_status": "bounced",
    "suppressed": true
  }
}
```

---

### TASK-013: Task Due Date Calculation
**Function:** `TaskService.calculate_due_date()`

**Hypothetical Input:**
```json
{
  "priority": "HIGHEST",
  "created_at": "2024-01-15T10:00:00Z"
}
```

**Expected Output:**
```json
{
  "HIGHEST": {
    "due_date": "2024-01-15T22:00:00Z",
    "description": "< 12 hours"
  },
  "HIGH": {
    "due_date": "2024-01-15T23:59:59Z",
    "description": "Same day"
  },
  "MEDIUM": {
    "due_date": "2024-01-17T23:59:59Z",
    "description": "Within 48 hours"
  },
  "LOW": {
    "due_date": "2024-01-22T23:59:59Z",
    "description": "Within 1 week"
  }
}
```

---

## 5. MS Teams Notifications

### TEAMS-001: High Priority Notification
**Function:** `TeamsNotificationService.send_notification()`
**File:** `app/services/notifications/teams.py`

**Hypothetical Input:**
```json
{
  "task": {
    "type": "Review Interested Reply",
    "priority": "HIGH"
  },
  "contact": {
    "name": "John Smith",
    "company": "Grand Hotel",
    "email": "john@grandhotel.com"
  },
  "categorization": {
    "main_category": "INTERESTED",
    "subcategory": "READY_TO_CHAT_PHONE"
  }
}
```

**Expected Output (Adaptive Card):**
```json
{
  "type": "AdaptiveCard",
  "body": [
    {
      "type": "TextBlock",
      "text": "[ACTION REQUIRED] INTERESTED: John Smith - Grand Hotel",
      "weight": "Bolder",
      "size": "Large"
    },
    {
      "type": "FactSet",
      "facts": [
        {"title": "Priority", "value": "HIGH"},
        {"title": "Category", "value": "Ready to Chat (Phone)"},
        {"title": "Contact", "value": "john@grandhotel.com"},
        {"title": "Required Action", "value": "Review interested reply and schedule call"}
      ]
    }
  ],
  "actions": [
    {
      "type": "Action.OpenUrl",
      "title": "Open HubSpot Task",
      "url": "https://app.hubspot.com/tasks/123456"
    }
  ]
}
```

---

### TEAMS-002: Highest Priority Notification (Referral)
**Function:** `TeamsNotificationService.send_notification()`

**Hypothetical Input:**
```json
{
  "task": {
    "type": "Follow-up Referral Immediately",
    "priority": "HIGHEST"
  },
  "contact": {
    "name": "Referred Contact",
    "company": "ABC Hotels"
  },
  "referrer": {
    "name": "Original Contact",
    "company": "XYZ Hotels"
  }
}
```

**Expected Output:**
```json
{
  "notification_text": "[ACTION REQUIRED] Referral: Referred Contact - ABC Hotels",
  "priority_badge": "HIGHEST - Immediate Action Required",
  "additional_context": "Referred by Original Contact at XYZ Hotels"
}
```

---

### TEAMS-003: Notification Format Verification
**Function:** `TeamsNotificationService.format_notification()`

**Expected Format:**
```
[ACTION REQUIRED] [Category]: [Lead Name] - [Company]
Priority: [Priority Level]
Required Action: [Task Description]
HubSpot Task URL: [Direct Link]
Contact: [Email] | [Phone if available]
Draft Message: [AI-generated draft for response]
Meeting Agenda: [Draft agenda for calls]
Available Times: [Suggested time slots]
```

---

### TEAMS-004: HubSpot Task URL Inclusion
**Function:** `TeamsNotificationService.generate_task_url()`

**Hypothetical Input:**
```json
{
  "hubspot_task_id": "12345678",
  "portal_id": "87654321"
}
```

**Expected Output:**
```json
{
  "task_url": "https://app.hubspot.com/contacts/87654321/task/12345678",
  "clickable": true
}
```

---

### TEAMS-005: Draft Message Inclusion
**Function:** `TeamsNotificationService.generate_draft_message()`

**Hypothetical Input:**
```json
{
  "contact_name": "John",
  "category": "INTRIGUED",
  "questions_asked": ["pricing", "coverage options"]
}
```

**Expected Output:**
```json
{
  "draft_message": "Hi John,\n\nThank you for your interest in our insurance solutions! I'd be happy to discuss our pricing tiers and coverage options.\n\nWould you have 15 minutes this week for a quick call?\n\nBest regards"
}
```

---

### TEAMS-006: Meeting Agenda Inclusion
**Function:** `TeamsNotificationService.generate_agenda()`

**Hypothetical Input:**
```json
{
  "contact": {
    "name": "John Smith",
    "company": "Grand Hotel",
    "company_size": "500 rooms"
  },
  "category": "READY_TO_CHAT_OPEN"
}
```

**Expected Output:**
```json
{
  "meeting_agenda": [
    "1. Introduction and company overview (5 min)",
    "2. Current insurance situation discussion (10 min)",
    "3. Our coverage options for 500-room properties (15 min)",
    "4. Pricing and next steps (10 min)",
    "5. Q&A (5 min)"
  ],
  "duration": "45 minutes"
}
```

---

### TEAMS-007: Time Zone Handling
**Function:** `TeamsNotificationService.suggest_meeting_times()`

**Hypothetical Input:**
```json
{
  "prospect_timezone": "America/Los_Angeles",
  "our_timezone": "America/New_York",
  "date": "2024-01-17"
}
```

**Expected Output:**
```json
{
  "suggested_times": [
    {
      "our_time": "2024-01-17T13:00:00-05:00",
      "prospect_time": "2024-01-17T10:00:00-08:00",
      "display": "10:00 AM PT / 1:00 PM ET"
    },
    {
      "our_time": "2024-01-17T15:00:00-05:00",
      "prospect_time": "2024-01-17T12:00:00-08:00",
      "display": "12:00 PM PT / 3:00 PM ET"
    }
  ]
}
```

---

## 6. LinkedIn Integration

### LI-001: ConnectSafely Profile Lookup
**Function:** `ConnectSafelyClient.find_profile_by_email()`
**File:** `app/integrations/connectsafely/client.py`

**Hypothetical Input:**
```json
{
  "email": "exec@luxuryhotel.com"
}
```

**Expected Output:**
```json
{
  "profile": {
    "linkedin_url": "https://linkedin.com/in/hotelexec",
    "first_name": "Michael",
    "last_name": "Johnson",
    "headline": "CEO at Luxury Hotel Group",
    "location": "Miami, FL"
  }
}
```

---

### LI-002: ConnectSafely Connection Request
**Function:** `ConnectSafelyClient.send_connection_request()`

**Hypothetical Input:**
```json
{
  "profile_url": "https://linkedin.com/in/hotelexec",
  "message": "Hi Michael, I noticed you lead Luxury Hotel Group. I'd love to connect and share how we're helping hotels optimize their insurance coverage."
}
```

**Expected Output:**
```json
{
  "status": "sent",
  "request_id": "conn_123",
  "rate_limit_remaining": 45,
  "message_sent": true
}
```

---

### LI-003: ConnectSafely DM Send
**Function:** `ConnectSafelyClient.send_direct_message()`

**Hypothetical Input:**
```json
{
  "profile_url": "https://linkedin.com/in/hotelexec",
  "message": "Thanks for connecting, Michael! I wanted to follow up on our insurance solutions for hotel chains..."
}
```

**Expected Output:**
```json
{
  "status": "sent",
  "message_id": "dm_456",
  "delivered_at": "2024-01-15T14:30:00Z"
}
```

---

### LI-004: ConnectSafely Connection Status
**Function:** `ConnectSafelyClient.get_connection_status()`

**Hypothetical Input:**
```json
{
  "profile_url": "https://linkedin.com/in/hotelexec"
}
```

**Expected Output:**
```json
{
  "status": "connected",
  "connected_since": "2024-01-14T10:00:00Z",
  "can_message": true
}
```

**Possible Status Values:**
- `not_connected`
- `pending`
- `connected`
- `rejected`

---

### LI-005: HeyReach Contact Enrichment
**Function:** `HeyReachClient.enrich_contact()`
**File:** `app/integrations/heyreach/client.py`

**Hypothetical Input:**
```json
{
  "email": "cfo@hotelchain.com"
}
```

**Expected Output:**
```json
{
  "profile": {
    "linkedin_url": "https://linkedin.com/in/hotelcfo",
    "first_name": "Sarah",
    "last_name": "Williams",
    "headline": "CFO at Hotel Chain Inc.",
    "industry": "Hospitality",
    "company_linkedin": "https://linkedin.com/company/hotelchain"
  },
  "enrichment_status": "success"
}
```

---

### LI-006: HeyReach Campaign Add
**Function:** `HeyReachClient.add_to_campaign()`

**Hypothetical Input:**
```json
{
  "linkedin_url": "https://linkedin.com/in/newlead",
  "campaign_id": "camp_insurance_2024",
  "personalization": {
    "referrer_name": "John Smith",
    "referrer_company": "Referring Hotel"
  }
}
```

**Expected Output:**
```json
{
  "status": "added",
  "lead_id": "lead_789",
  "campaign_id": "camp_insurance_2024",
  "sequence_position": 1,
  "personalized_message": "Hi, John Smith at Referring Hotel suggested I reach out..."
}
```

---

### LI-007: HeyReach Campaign Pause
**Function:** `HeyReachClient.pause_in_campaign()`

**Hypothetical Input:**
```json
{
  "lead_id": "lead_789",
  "campaign_id": "camp_insurance_2024",
  "reason": "prospect_requested_delay"
}
```

**Expected Output:**
```json
{
  "status": "paused",
  "lead_id": "lead_789",
  "paused_at": "2024-01-15T15:00:00Z",
  "can_resume": true
}
```

---

### LI-008: LinkedIn Flow (Email → LinkedIn)
**Function:** `WorkflowService.trigger_linkedin_flow()`

**Hypothetical Input:**
```json
{
  "trigger": "high_interest_email_reply",
  "contact": {
    "email": "interested@hotel.com",
    "linkedin_url": "https://linkedin.com/in/interested"
  },
  "categorization": {
    "main_category": "INTERESTED",
    "subcategory": "READY_TO_CHAT_OPEN"
  }
}
```

**Expected Output:**
```json
{
  "workflow_triggered": true,
  "steps": [
    {"step": 1, "action": "linkedin_profile_lookup", "status": "completed"},
    {"step": 2, "action": "connection_request_sent", "status": "completed"},
    {"step": 3, "action": "dm_draft_created", "status": "pending_approval"},
    {"step": 4, "action": "hubspot_task_created", "status": "completed"}
  ]
}
```

---

## 7. HubSpot CRM Integration

### HS-001: Contact Create
**Function:** `HubSpotClient.create_contact()`
**File:** `app/integrations/hubspot/client.py`

**Hypothetical Input:**
```json
{
  "email": "new@hotel.com",
  "firstname": "New",
  "lastname": "Contact",
  "company": "New Hotel",
  "phone": "+1-555-0100",
  "jobtitle": "General Manager"
}
```

**Expected Output:**
```json
{
  "id": "hs_contact_123",
  "properties": {
    "email": "new@hotel.com",
    "firstname": "New",
    "lastname": "Contact",
    "company": "New Hotel",
    "createdate": "2024-01-15T10:00:00Z"
  }
}
```

---

### HS-002: Contact Update After Categorization
**Function:** `HubSpotClient.update_contact()`

**Hypothetical Input:**
```json
{
  "contact_id": "hs_contact_123",
  "properties": {
    "outreach_category": "INTERESTED",
    "outreach_subcategory": "READY_TO_CHAT_PHONE",
    "last_categorization_date": "2024-01-15T10:30:00Z",
    "categorization_confidence": "0.95"
  }
}
```

**Expected Output:**
```json
{
  "id": "hs_contact_123",
  "properties": {
    "outreach_category": "INTERESTED",
    "outreach_subcategory": "READY_TO_CHAT_PHONE",
    "last_categorization_date": "2024-01-15T10:30:00Z"
  },
  "updated_at": "2024-01-15T10:30:05Z"
}
```

---

### HS-003: Contact Get by Email
**Function:** `HubSpotClient.get_contact_by_email()`

**Hypothetical Input:**
```json
{
  "email": "existing@hotel.com"
}
```

**Expected Output:**
```json
{
  "id": "hs_contact_456",
  "properties": {
    "email": "existing@hotel.com",
    "firstname": "Existing",
    "lastname": "Contact",
    "company": "Existing Hotel",
    "outreach_category": "INTERESTED",
    "re_engagement_date": "2024-04-15"
  }
}
```

---

### HS-004: Task Create
**Function:** `HubSpotClient.create_task()`

**Hypothetical Input:**
```json
{
  "subject": "Review Interested Reply - John Smith",
  "body": "Lead expressed interest in insurance services. Phone: 555-123-4567",
  "priority": "HIGH",
  "due_date": "2024-01-15T23:59:59Z",
  "associated_contact_id": "hs_contact_123"
}
```

**Expected Output:**
```json
{
  "id": "hs_task_789",
  "properties": {
    "subject": "Review Interested Reply - John Smith",
    "hs_task_priority": "HIGH",
    "hs_task_status": "NOT_STARTED",
    "hs_timestamp": "2024-01-15T23:59:59Z"
  },
  "associations": {
    "contacts": ["hs_contact_123"]
  }
}
```

---

### HS-005: Task Update
**Function:** `HubSpotClient.update_task()`

**Hypothetical Input:**
```json
{
  "task_id": "hs_task_789",
  "properties": {
    "hs_task_status": "COMPLETED",
    "hs_task_completion_date": "2024-01-15T14:00:00Z"
  }
}
```

**Expected Output:**
```json
{
  "id": "hs_task_789",
  "properties": {
    "hs_task_status": "COMPLETED",
    "hs_task_completion_date": "2024-01-15T14:00:00Z"
  }
}
```

---

### HS-006: Deal Create
**Function:** `HubSpotClient.create_deal()`

**Hypothetical Input:**
```json
{
  "dealname": "Grand Hotel - Insurance Coverage",
  "pipeline": "default",
  "dealstage": "qualifiedtobuy",
  "amount": 50000,
  "associated_contact_id": "hs_contact_123"
}
```

**Expected Output:**
```json
{
  "id": "hs_deal_111",
  "properties": {
    "dealname": "Grand Hotel - Insurance Coverage",
    "dealstage": "qualifiedtobuy",
    "amount": "50000"
  },
  "associations": {
    "contacts": ["hs_contact_123"]
  }
}
```

---

### HS-007: Deal Update Stage
**Function:** `HubSpotClient.update_deal()`

**Hypothetical Input:**
```json
{
  "deal_id": "hs_deal_111",
  "properties": {
    "dealstage": "presentationscheduled"
  }
}
```

**Expected Output:**
```json
{
  "id": "hs_deal_111",
  "properties": {
    "dealstage": "presentationscheduled"
  },
  "updated_at": "2024-01-16T10:00:00Z"
}
```

---

### HS-008: Meeting Create
**Function:** `HubSpotClient.create_meeting()`

**Hypothetical Input:**
```json
{
  "title": "Insurance Discovery Call - Grand Hotel",
  "start_time": "2024-01-17T14:00:00Z",
  "end_time": "2024-01-17T14:45:00Z",
  "associated_contact_id": "hs_contact_123",
  "meeting_link": "https://meetings.hubspot.com/rep/discovery"
}
```

**Expected Output:**
```json
{
  "id": "hs_meeting_222",
  "properties": {
    "title": "Insurance Discovery Call - Grand Hotel",
    "hs_meeting_start_time": "2024-01-17T14:00:00Z",
    "hs_meeting_end_time": "2024-01-17T14:45:00Z"
  },
  "associations": {
    "contacts": ["hs_contact_123"]
  }
}
```

---

### HS-009: Custom Field Update
**Function:** `HubSpotClient.update_contact()`

**Hypothetical Input:**
```json
{
  "contact_id": "hs_contact_123",
  "properties": {
    "validation_status": "validated",
    "validation_confidence": "0.92",
    "company_type": "Hotel Chain"
  }
}
```

**Expected Output:**
```json
{
  "id": "hs_contact_123",
  "properties": {
    "validation_status": "validated",
    "validation_confidence": "0.92",
    "company_type": "Hotel Chain"
  }
}
```

---

### HS-010: Re-engagement Date Setting
**Function:** `HubSpotClient.set_reengagement_date()`

**Hypothetical Input:**
```json
{
  "contact_id": "hs_contact_123",
  "category": "NEGATIVE_SIGNALS",
  "subcategory": "RECENT_PURCHASE",
  "contract_end": "2027-01-01"
}
```

**Expected Output:**
```json
{
  "id": "hs_contact_123",
  "properties": {
    "re_engagement_date": "2026-10-01",
    "re_engagement_reason": "Contract renewal approaching"
  }
}
```

---

## 8. Re-engagement Pipeline

### RE-001: 30-Day Re-engagement (Wrong Contact)
**Function:** `ReEngagementService.schedule()`
**File:** `app/services/reengagement/service.py`

**Hypothetical Input:**
```json
{
  "contact_id": "contact_123",
  "category": "NOT_INTERESTED",
  "subcategory": "WRONG_COMPANY",
  "categorization_date": "2024-01-15"
}
```

**Expected Output:**
```json
{
  "re_engagement_scheduled": true,
  "re_engagement_date": "2024-02-14",
  "days_until": 30,
  "action": "Research correct contact via Apollo"
}
```

---

### RE-002: 60-Day Re-engagement (Self-Disqualify)
**Function:** `ReEngagementService.schedule()`

**Hypothetical Input:**
```json
{
  "contact_id": "contact_456",
  "category": "NOT_INTERESTED",
  "subcategory": "SELF_DISQUALIFY",
  "categorization_date": "2024-01-15"
}
```

**Expected Output:**
```json
{
  "re_engagement_scheduled": true,
  "re_engagement_date": "2024-03-15",
  "days_until": 60,
  "action": "Send nurture content about smaller coverage options"
}
```

---

### RE-003: 90-Day Re-engagement (Long-term/Not Interested)
**Function:** `ReEngagementService.schedule()`

**Hypothetical Input:**
```json
{
  "contact_id": "contact_789",
  "category": "INTERESTED",
  "subcategory": "LONG_TERM_FOLLOWUP",
  "categorization_date": "2024-01-15"
}
```

**Expected Output:**
```json
{
  "re_engagement_scheduled": true,
  "re_engagement_date": "2024-04-15",
  "days_until": 90,
  "action": "Re-initiate outreach sequence"
}
```

---

### RE-004: 120-Day Re-engagement (Not Interested + NPS)
**Function:** `ReEngagementService.schedule()`

**Hypothetical Input:**
```json
{
  "contact_id": "contact_111",
  "category": "NOT_INTERESTED",
  "subcategory": "NOT_INTERESTED",
  "nps_requested": true,
  "categorization_date": "2024-01-15"
}
```

**Expected Output:**
```json
{
  "re_engagement_scheduled": true,
  "re_engagement_date": "2024-05-15",
  "days_until": 120,
  "action": "Send NPS survey and soft re-engagement"
}
```

---

### RE-005: 180-Day Re-engagement (Negative Signals)
**Function:** `ReEngagementService.schedule()`

**Hypothetical Input:**
```json
{
  "contact_id": "contact_222",
  "category": "NEGATIVE_SIGNALS",
  "subcategory": "HAPPY_WITH_COMPETITOR",
  "categorization_date": "2024-01-15"
}
```

**Expected Output:**
```json
{
  "re_engagement_scheduled": true,
  "re_engagement_date": "2024-07-15",
  "days_until": 180,
  "action": "Check if still satisfied with competitor"
}
```

---

### RE-006: 365-Day Re-engagement (Recent Purchase)
**Function:** `ReEngagementService.schedule()`

**Hypothetical Input:**
```json
{
  "contact_id": "contact_333",
  "category": "NEGATIVE_SIGNALS",
  "subcategory": "RECENT_PURCHASE",
  "categorization_date": "2024-01-15"
}
```

**Expected Output:**
```json
{
  "re_engagement_scheduled": true,
  "re_engagement_date": "2025-01-15",
  "days_until": 365,
  "action": "Pre-renewal outreach"
}
```

---

### RE-007: Prospect-Defined Timing
**Function:** `ReEngagementService.parse_prospect_timing()`

**Hypothetical Input:**
```json
{
  "contact_id": "contact_444",
  "category": "NEGATIVE_SIGNALS",
  "subcategory": "WRONG_TIMING",
  "reply_text": "Contact me after Q2 when our merger is complete",
  "current_date": "2024-01-15"
}
```

**Expected Output:**
```json
{
  "re_engagement_scheduled": true,
  "re_engagement_date": "2024-07-01",
  "parsed_timing": "after Q2",
  "calculated_date_reasoning": "Q2 ends June 30, scheduled July 1"
}
```

---

### RE-008: Monthly Job Scan
**Function:** `ReEngagementJob.scan_due_contacts()`
**File:** `app/workers/reengagement_tasks.py`

**Hypothetical Input:**
```json
{
  "scan_date": "2024-04-01",
  "batch_size": 1000
}
```

**Expected Output:**
```json
{
  "contacts_scanned": 5000,
  "contacts_due": 150,
  "contacts_by_channel": {
    "email": 100,
    "linkedin": 50
  },
  "processing_time_ms": 2500
}
```

---

### RE-009: SmartLead Re-sequence
**Function:** `ReEngagementService.add_to_smartlead_sequence()`

**Hypothetical Input:**
```json
{
  "contact": {
    "email": "reactivate@hotel.com",
    "name": "John Smith"
  },
  "original_category": "NOT_INTERESTED",
  "sequence_id": "reengagement_seq_1"
}
```

**Expected Output:**
```json
{
  "added_to_sequence": true,
  "smartlead_lead_id": "sl_lead_555",
  "sequence_id": "reengagement_seq_1",
  "first_email_scheduled": "2024-04-02T09:00:00Z"
}
```

---

### RE-010: ConnectSafely Re-sequence
**Function:** `ReEngagementService.add_to_linkedin_sequence()`

**Hypothetical Input:**
```json
{
  "contact": {
    "linkedin_url": "https://linkedin.com/in/reactivate",
    "name": "Jane Doe"
  },
  "original_category": "NEGATIVE_SIGNALS"
}
```

**Expected Output:**
```json
{
  "added_to_sequence": true,
  "connectsafely_id": "cs_666",
  "action": "connection_check",
  "message_scheduled": "Hi Jane, we connected a while back..."
}
```

---

### RE-011: Suppression Check
**Function:** `ReEngagementService.filter_suppressed()`

**Hypothetical Input:**
```json
{
  "contacts_due": [
    {"id": "1", "email": "active@hotel.com", "suppressed": false},
    {"id": "2", "email": "unsubscribed@hotel.com", "suppressed": true},
    {"id": "3", "email": "bounced@hotel.com", "suppressed": true},
    {"id": "4", "email": "another@hotel.com", "suppressed": false}
  ]
}
```

**Expected Output:**
```json
{
  "eligible_contacts": [
    {"id": "1", "email": "active@hotel.com"},
    {"id": "4", "email": "another@hotel.com"}
  ],
  "filtered_count": 2,
  "suppression_reasons": {
    "unsubscribed": 1,
    "bounced": 1
  }
}
```

---

## 9. Referral Auto-Campaign

### REF-001: Referral Extraction (Full Contact)
**Function:** `ReferralExtractor.extract()`
**File:** `app/services/referral/extractor.py`

**Hypothetical Input:**
```json
{
  "reply_text": "You should contact John Smith at ABC Hotels - he's the VP of Risk. His email is john.smith@abchotels.com and phone is 555-123-4567"
}
```

**Expected Output:**
```json
{
  "referral_detected": true,
  "referral": {
    "name": "John Smith",
    "email": "john.smith@abchotels.com",
    "phone": "555-123-4567",
    "company": "ABC Hotels",
    "title": "VP of Risk"
  },
  "confidence": 0.95
}
```

---

### REF-002: Referral Extraction (Name Only)
**Function:** `ReferralExtractor.extract()`

**Hypothetical Input:**
```json
{
  "reply_text": "Talk to Sarah in our accounting department, she handles vendor contracts"
}
```

**Expected Output:**
```json
{
  "referral_detected": true,
  "referral": {
    "name": "Sarah",
    "email": null,
    "department": "accounting",
    "role": "vendor contracts"
  },
  "confidence": 0.75,
  "requires_enrichment": true
}
```

---

### REF-003: HubSpot Referral Contact Create
**Function:** `ReferralEnrollment.create_in_hubspot()`
**File:** `app/services/referral/enrollment.py`

**Hypothetical Input:**
```json
{
  "referral": {
    "name": "John Smith",
    "email": "john.smith@abchotels.com",
    "company": "ABC Hotels"
  },
  "referrer": {
    "hubspot_id": "hs_123",
    "name": "Original Contact",
    "company": "Referring Hotel"
  }
}
```

**Expected Output:**
```json
{
  "hubspot_contact_created": true,
  "hubspot_id": "hs_new_456",
  "properties": {
    "email": "john.smith@abchotels.com",
    "firstname": "John",
    "lastname": "Smith",
    "company": "ABC Hotels",
    "lead_source": "Referral",
    "referred_by": "Original Contact at Referring Hotel"
  }
}
```

---

### REF-004: SmartLead Referral Add
**Function:** `ReferralEnrollment.add_to_smartlead()`

**Hypothetical Input:**
```json
{
  "referral": {
    "email": "john.smith@abchotels.com",
    "name": "John Smith"
  },
  "referrer_name": "Original Contact",
  "campaign_id": "camp_referral_2024"
}
```

**Expected Output:**
```json
{
  "smartlead_added": true,
  "lead_id": "sl_ref_789",
  "campaign_id": "camp_referral_2024",
  "personalized_first_email": "Hi John, Original Contact at Referring Hotel suggested I reach out to you about our insurance solutions for hotels..."
}
```

---

### REF-005: HeyReach Referral Add
**Function:** `ReferralEnrollment.add_to_heyreach()`

**Hypothetical Input:**
```json
{
  "referral": {
    "linkedin_url": "https://linkedin.com/in/johnsmith",
    "name": "John Smith"
  },
  "referrer_name": "Original Contact",
  "campaign_id": "heyreach_referral_2024"
}
```

**Expected Output:**
```json
{
  "heyreach_added": true,
  "lead_id": "hr_ref_111",
  "campaign_id": "heyreach_referral_2024",
  "connection_message": "Hi John, Original Contact mentioned you might be interested in discussing insurance options for ABC Hotels..."
}
```

---

### REF-006: Referral Link to Original Contact
**Function:** `ReferralEnrollment.link_referral()`

**Hypothetical Input:**
```json
{
  "referral_hubspot_id": "hs_new_456",
  "referrer_hubspot_id": "hs_123"
}
```

**Expected Output:**
```json
{
  "association_created": true,
  "association_type": "referral",
  "referral_contact": "hs_new_456",
  "referrer_contact": "hs_123",
  "notes_added": "Referred by hs_123 on 2024-01-15"
}
```

---

## 10. Performance Requirements

### PERF-001: Webhook Response Time
**Requirement:** < 200ms per Requirements.md

**Test Scenario:**
```json
{
  "endpoint": "POST /webhook/smartlead",
  "payload_size": "1KB",
  "concurrent_requests": 1,
  "iterations": 100
}
```

**Expected Result:**
```json
{
  "p50_latency_ms": 45,
  "p95_latency_ms": 120,
  "p99_latency_ms": 180,
  "max_latency_ms": 195,
  "all_under_200ms": true
}
```

---

### PERF-002: Categorization Processing Time
**Requirement:** < 2 seconds per Requirements.md

**Test Scenario:**
```json
{
  "function": "CategorizationService.categorize()",
  "reply_text_length": "500 characters",
  "context_included": true,
  "iterations": 50
}
```

**Expected Result:**
```json
{
  "p50_latency_ms": 800,
  "p95_latency_ms": 1500,
  "p99_latency_ms": 1800,
  "max_latency_ms": 1950,
  "all_under_2000ms": true
}
```

---

### PERF-003: Task Generation Time
**Requirement:** < 1 second after categorization

**Test Scenario:**
```json
{
  "function": "TaskService.create_tasks_for_category()",
  "tasks_to_create": 3,
  "hubspot_api_calls": 3,
  "iterations": 100
}
```

**Expected Result:**
```json
{
  "p50_latency_ms": 250,
  "p95_latency_ms": 600,
  "p99_latency_ms": 850,
  "max_latency_ms": 950,
  "all_under_1000ms": true
}
```

---

### PERF-004: Database Query Time
**Requirement:** < 100ms for 10,000 records

**Test Scenario:**
```json
{
  "query": "SELECT * FROM contacts WHERE company = ?",
  "total_records": 100000,
  "result_set_size": 50,
  "iterations": 100
}
```

**Expected Result:**
```json
{
  "p50_latency_ms": 25,
  "p95_latency_ms": 65,
  "p99_latency_ms": 85,
  "max_latency_ms": 95,
  "all_under_100ms": true
}
```

---

### PERF-005: Concurrent Webhooks
**Requirement:** 100+ concurrent webhooks, 99% success

**Test Scenario:**
```json
{
  "concurrent_requests": 100,
  "duration_seconds": 60,
  "request_type": "EMAIL_REPLY"
}
```

**Expected Result:**
```json
{
  "total_requests": 100,
  "successful_requests": 99,
  "failed_requests": 1,
  "success_rate": 0.99,
  "avg_latency_ms": 150,
  "meets_requirement": true
}
```

---

### PERF-006: Daily Email Volume
**Requirement:** 1,000+ emails daily

**Test Scenario:**
```json
{
  "simulation_duration_hours": 24,
  "emails_per_hour": 50,
  "total_emails": 1200
}
```

**Expected Result:**
```json
{
  "emails_processed": 1200,
  "emails_failed": 0,
  "categorizations_completed": 1200,
  "tasks_created": 3600,
  "system_stable": true
}
```

---

## 11. Monitoring & Metrics

### MON-001: Rate Limit Tracking
**Function:** `RateLimitMonitor.track()`
**File:** `app/core/metrics.py`

**Hypothetical Input:**
```json
{
  "integration": "hubspot",
  "rate_limit_header": "X-HubSpot-RateLimit-Daily-Remaining: 450000",
  "requests_made": 50000
}
```

**Expected Output:**
```json
{
  "integration": "hubspot",
  "daily_limit": 500000,
  "remaining": 450000,
  "used": 50000,
  "usage_percentage": 10.0,
  "prometheus_gauge": "rate_limit_usage_hubspot"
}
```

---

### MON-002: Rate Limit Alert (80% Threshold)
**Function:** `RateLimitMonitor.check_threshold()`

**Hypothetical Input:**
```json
{
  "integration": "hubspot",
  "daily_limit": 500000,
  "remaining": 50000,
  "usage_percentage": 90.0
}
```

**Expected Output:**
```json
{
  "alert_triggered": true,
  "alert_type": "rate_limit_warning",
  "message": "HubSpot API at 90% of daily limit (50000 remaining)",
  "sentry_event_id": "sentry_123",
  "teams_notification_sent": true
}
```

---

### MON-003: Slow Query Detection
**Function:** `DBMonitor.log_slow_query()`
**File:** `app/db/session.py`

**Hypothetical Input:**
```json
{
  "query": "SELECT * FROM contacts WHERE validation_status = 'pending'",
  "duration_ms": 150,
  "threshold_ms": 100
}
```

**Expected Output:**
```json
{
  "slow_query_logged": true,
  "log_entry": {
    "level": "WARNING",
    "message": "slow_query_detected",
    "query_hash": "abc123",
    "duration_ms": 150,
    "threshold_ms": 100
  },
  "prometheus_histogram": "db_query_duration_seconds"
}
```

---

### MON-004: Connection Pool Metrics
**Function:** `DBMonitor.get_pool_stats()`

**Hypothetical Input:**
```json
{
  "pool_name": "default"
}
```

**Expected Output:**
```json
{
  "pool_size": 20,
  "checked_out": 5,
  "checked_in": 15,
  "overflow": 0,
  "max_overflow": 10,
  "utilization_percentage": 25.0,
  "prometheus_gauges": {
    "db_pool_size": 20,
    "db_pool_checked_out": 5,
    "db_pool_overflow": 0
  }
}
```

---

### MON-005: Email Open Rate
**Function:** `MetricsService.calculate_open_rate()`
**File:** `app/core/metrics.py`

**Hypothetical Input:**
```json
{
  "campaign_id": "camp_123",
  "emails_sent": 1000,
  "emails_opened": 350
}
```

**Expected Output:**
```json
{
  "campaign_id": "camp_123",
  "open_rate": 0.35,
  "open_rate_percentage": "35%",
  "industry_benchmark": "20-25%",
  "performance": "above_average"
}
```

---

### MON-006: Email Click Rate
**Function:** `MetricsService.calculate_click_rate()`

**Hypothetical Input:**
```json
{
  "campaign_id": "camp_123",
  "emails_sent": 1000,
  "emails_clicked": 50
}
```

**Expected Output:**
```json
{
  "campaign_id": "camp_123",
  "click_rate": 0.05,
  "click_rate_percentage": "5%",
  "click_to_open_rate": 0.143
}
```

---

### MON-007: Reply Rate
**Function:** `MetricsService.calculate_reply_rate()`

**Hypothetical Input:**
```json
{
  "campaign_id": "camp_123",
  "emails_sent": 1000,
  "replies_received": 80
}
```

**Expected Output:**
```json
{
  "campaign_id": "camp_123",
  "reply_rate": 0.08,
  "reply_rate_percentage": "8%",
  "replies_by_category": {
    "INTERESTED": 30,
    "NOT_INTERESTED": 25,
    "POSITIVE_SIGNALS": 10,
    "NEGATIVE_SIGNALS": 10,
    "AUTOMATE_REPLY": 5
  }
}
```

---

### MON-008: Conversion Rate (Replies → Meetings)
**Function:** `MetricsService.calculate_conversion_rate()`

**Hypothetical Input:**
```json
{
  "campaign_id": "camp_123",
  "total_replies": 80,
  "meetings_booked": 12
}
```

**Expected Output:**
```json
{
  "campaign_id": "camp_123",
  "conversion_rate": 0.15,
  "conversion_rate_percentage": "15%",
  "funnel": {
    "emails_sent": 1000,
    "replies": 80,
    "interested": 30,
    "meetings": 12
  }
}
```

---

### MON-009: Categorization Accuracy
**Function:** `MetricsService.track_categorization_accuracy()`

**Hypothetical Input:**
```json
{
  "period": "2024-01",
  "total_categorizations": 500
}
```

**Expected Output:**
```json
{
  "period": "2024-01",
  "total_categorizations": 500,
  "avg_confidence": 0.89,
  "high_confidence_count": 450,
  "low_confidence_count": 50,
  "confidence_distribution": {
    "0.95-1.00": 200,
    "0.90-0.95": 150,
    "0.85-0.90": 100,
    "0.75-0.85": 40,
    "0.00-0.75": 10
  }
}
```

---

## 12. Error Handling & Retry

### ERR-001: API Timeout Retry
**Function:** `BaseClient._request()` with retry logic
**File:** `app/integrations/base.py`

**Hypothetical Input:**
```json
{
  "request": "POST /contacts",
  "attempt_1": {"status": "timeout", "duration_ms": 30000},
  "attempt_2": {"status": "timeout", "duration_ms": 30000},
  "attempt_3": {"status": "success", "duration_ms": 500}
}
```

**Expected Output:**
```json
{
  "final_status": "success",
  "total_attempts": 3,
  "total_duration_ms": 60500,
  "retry_delays": [1000, 2000],
  "exponential_backoff": true
}
```

---

### ERR-002: Rate Limit Retry (429)
**Function:** `BaseClient._handle_rate_limit()`

**Hypothetical Input:**
```json
{
  "response": {
    "status_code": 429,
    "headers": {
      "Retry-After": "60"
    }
  }
}
```

**Expected Output:**
```json
{
  "action": "retry_after_delay",
  "delay_seconds": 60,
  "retry_scheduled": true,
  "alert_sent": true
}
```

---

### ERR-003: Invalid Webhook (400)
**Function:** `SmartLeadWebhook.validate_payload()`

**Hypothetical Input:**
```json
{
  "event_type": "EMAIL_REPLY"
}
```

**Expected Output:**
```json
{
  "status_code": 400,
  "error": "Invalid webhook payload",
  "missing_fields": ["lead_email", "campaign_id"],
  "logged": true
}
```

---

### ERR-004: Invalid Signature (401)
**Function:** `verify_smartlead_signature()`

**Hypothetical Input:**
```json
{
  "provided_signature": "sha256=invalid",
  "expected_signature": "sha256=valid_hash"
}
```

**Expected Output:**
```json
{
  "status_code": 401,
  "error": "Invalid webhook signature",
  "logged": true,
  "security_alert": true
}
```

---

### ERR-005: LLM Failure Fallback
**Function:** `CategorizationService._categorize_with_retry()`

**Hypothetical Input:**
```json
{
  "attempt_1": {"status": "error", "error": "OpenAI rate limit"},
  "attempt_2": {"status": "error", "error": "OpenAI timeout"},
  "attempt_3": {"status": "success", "result": "INTERESTED"}
}
```

**Expected Output:**
```json
{
  "final_status": "success",
  "category": "INTERESTED",
  "attempts": 3,
  "retry_delays": [5000, 10000],
  "errors_logged": 2
}
```

---

### ERR-006: Celery Task Retry
**Function:** `@celery_task(bind=True, max_retries=3)`
**File:** `app/workers/categorization_tasks.py`

**Hypothetical Input:**
```json
{
  "task_id": "celery_task_123",
  "attempt_1": {"status": "failed", "error": "Database connection lost"},
  "attempt_2": {"status": "success"}
}
```

**Expected Output:**
```json
{
  "task_id": "celery_task_123",
  "final_status": "SUCCESS",
  "retries": 1,
  "total_execution_time_seconds": 5.2
}
```

---

### ERR-007: Sentry Error Capture
**Function:** `sentry_sdk.capture_exception()`

**Hypothetical Input:**
```json
{
  "exception": "HubSpotError",
  "message": "Failed to create contact: API error",
  "context": {
    "contact_email": "test@hotel.com",
    "endpoint": "/contacts"
  }
}
```

**Expected Output:**
```json
{
  "sentry_event_id": "sentry_event_456",
  "captured": true,
  "tags": {
    "integration": "hubspot",
    "error_type": "api_error"
  },
  "breadcrumbs_attached": 10
}
```

---

## 13. Compliance

### COMP-001: Immediate Unsubscribe Processing
**Function:** `ComplianceService.process_unsubscribe()`
**File:** `app/services/compliance/service.py`

**Hypothetical Input:**
```json
{
  "contact_email": "unsubscribe@hotel.com",
  "unsubscribe_source": "email_link",
  "timestamp": "2024-01-15T12:00:00Z"
}
```

**Expected Output:**
```json
{
  "processed": true,
  "processing_time_ms": 50,
  "actions_taken": [
    "smartlead_removed",
    "heyreach_removed",
    "hubspot_dnc_flagged",
    "database_suppressed"
  ],
  "compliance_timestamp": "2024-01-15T12:00:00Z"
}
```

---

### COMP-002: Do Not Contact (All Channels)
**Function:** `ComplianceService.add_to_blocklist()`

**Hypothetical Input:**
```json
{
  "contact_email": "block@hotel.com",
  "request_source": "explicit_request",
  "channels": ["email", "linkedin", "phone"]
}
```

**Expected Output:**
```json
{
  "blocklist_added": true,
  "channels_blocked": ["email", "linkedin", "phone"],
  "smartlead_blocklist": true,
  "connectsafely_blocklist": true,
  "heyreach_blocklist": true,
  "hubspot_dnc": true
}
```

---

### COMP-003: LinkedIn Rate Compliance
**Function:** `ConnectSafelyClient._check_rate_limits()`

**Hypothetical Input:**
```json
{
  "action": "connection_request",
  "daily_limit": 100,
  "used_today": 95
}
```

**Expected Output:**
```json
{
  "action_allowed": true,
  "remaining_today": 5,
  "warning": "Approaching daily limit (95/100)",
  "rate_limit_logged": true
}
```

---

### COMP-004: Export Functionality
**Function:** `ComplianceService.export_contact_data()`

**Hypothetical Input:**
```json
{
  "contact_email": "export@hotel.com",
  "format": "json",
  "include_history": true
}
```

**Expected Output:**
```json
{
  "export_generated": true,
  "format": "json",
  "data": {
    "contact": {
      "email": "export@hotel.com",
      "name": "John Smith",
      "company": "Export Hotel"
    },
    "communication_history": [
      {"date": "2024-01-10", "type": "email_sent"},
      {"date": "2024-01-12", "type": "email_opened"},
      {"date": "2024-01-14", "type": "email_reply"}
    ],
    "categorizations": [
      {"date": "2024-01-14", "category": "INTERESTED"}
    ]
  },
  "export_timestamp": "2024-01-15T10:00:00Z"
}
```

---

### COMP-005: Delete Functionality
**Function:** `ComplianceService.delete_contact_data()`

**Hypothetical Input:**
```json
{
  "contact_email": "delete@hotel.com",
  "deletion_reason": "GDPR_request",
  "retain_suppression": true
}
```

**Expected Output:**
```json
{
  "deletion_completed": true,
  "deleted_from": [
    "database_contacts",
    "database_communications",
    "database_categorizations",
    "smartlead",
    "heyreach"
  ],
  "retained": ["suppression_list"],
  "audit_log_entry": "contact_deleted_gdpr_2024-01-15"
}
```

---

### COMP-006: Audit Logging
**Function:** `AuditLogger.log_action()`
**File:** `app/core/logging.py`

**Hypothetical Input:**
```json
{
  "action": "contact_categorized",
  "actor": "system",
  "contact_id": "contact_123",
  "details": {
    "category": "INTERESTED",
    "subcategory": "READY_TO_CHAT_PHONE"
  }
}
```

**Expected Output:**
```json
{
  "audit_log_created": true,
  "log_entry": {
    "timestamp": "2024-01-15T10:30:00Z",
    "action": "contact_categorized",
    "actor": "system",
    "resource_type": "contact",
    "resource_id": "contact_123",
    "details": {
      "category": "INTERESTED",
      "subcategory": "READY_TO_CHAT_PHONE"
    },
    "ip_address": null,
    "retention_days": 365
  }
}
```

---

## 14. SmartLead Campaign Management

### SL-001: Create Campaign
**Function:** `SmartLeadClient.create_campaign()`
**File:** `app/integrations/smartlead/client.py`

**Hypothetical Input:**
```json
{
  "name": "Hotel Insurance Q1 2024",
  "sending_accounts": ["account1@company.com", "account2@company.com"],
  "daily_limit": 50,
  "timezone": "America/New_York"
}
```

**Expected Output:**
```json
{
  "campaign_id": "camp_new_123",
  "name": "Hotel Insurance Q1 2024",
  "status": "draft",
  "created_at": "2024-01-15T10:00:00Z"
}
```

---

### SL-002: Tag Management
**Function:** `SmartLeadClient.add_tag()`, `SmartLeadClient.remove_tag()`

**Hypothetical Input:**
```json
{
  "lead_email": "prospect@hotel.com",
  "tag": "interested"
}
```

**Expected Output:**
```json
{
  "lead_email": "prospect@hotel.com",
  "tags": ["interested", "hotel-chain"],
  "tag_added": true
}
```

---

### SL-003: Lead Category Update
**Function:** `SmartLeadClient.update_lead_category()`

**Hypothetical Input:**
```json
{
  "lead_email": "prospect@hotel.com",
  "category": "INTERESTED",
  "subcategory": "READY_TO_CHAT"
}
```

**Expected Output:**
```json
{
  "lead_email": "prospect@hotel.com",
  "category_updated": true,
  "smartlead_category": "interested"
}
```

---

### SL-004: Automated Reply
**Function:** `SmartLeadClient.send_reply()`

**Hypothetical Input:**
```json
{
  "lead_email": "prospect@hotel.com",
  "campaign_id": "camp_123",
  "message": "Thanks for your interest! I'd love to schedule a call...",
  "reply_to_message_id": "msg_456"
}
```

**Expected Output:**
```json
{
  "status": "sent",
  "message_id": "msg_789",
  "sent_at": "2024-01-15T10:30:00Z"
}
```

---

### SL-005: Sequence Management
**Function:** `SmartLeadClient.create_sequence()`

**Hypothetical Input:**
```json
{
  "campaign_id": "camp_123",
  "steps": [
    {"day": 0, "subject": "Insurance for {{company}}", "body": "Hi {{first_name}}..."},
    {"day": 3, "subject": "Following up", "body": "Just checking in..."},
    {"day": 7, "subject": "Quick question", "body": "Did you get a chance..."}
  ]
}
```

**Expected Output:**
```json
{
  "sequence_id": "seq_456",
  "steps_created": 3,
  "intervals": [0, 3, 7]
}
```

---

### SL-006: Mailbox Warmup Status
**Function:** `SmartLeadClient.get_warmup_status()`

**Hypothetical Input:**
```json
{
  "email_account": "sender@company.com"
}
```

**Expected Output:**
```json
{
  "email": "sender@company.com",
  "warmup_status": "active",
  "warmup_score": 85,
  "daily_send_limit": 50,
  "warmup_days_completed": 14
}
```

---

### SL-007: Mailbox Throttling
**Function:** `SmartLeadClient.check_throttle_status()`

**Hypothetical Input:**
```json
{
  "email_account": "sender@company.com",
  "campaign_id": "camp_123"
}
```

**Expected Output:**
```json
{
  "email": "sender@company.com",
  "daily_limit": 50,
  "sent_today": 45,
  "remaining": 5,
  "throttled": false,
  "reset_time": "2024-01-16T00:00:00Z"
}
```

---

### SL-008: Master Inbox Query
**Function:** `SmartLeadClient.get_master_inbox()`

**Hypothetical Input:**
```json
{
  "filter": "unread",
  "limit": 50
}
```

**Expected Output:**
```json
{
  "messages": [
    {
      "message_id": "msg_123",
      "lead_email": "prospect@hotel.com",
      "subject": "Re: Insurance Coverage",
      "preview": "Thanks for reaching out...",
      "received_at": "2024-01-15T09:00:00Z",
      "sending_account": "sender1@company.com"
    }
  ],
  "total_unread": 12
}
```

---

### SL-009: Add Lead to Campaign
**Function:** `SmartLeadClient.add_lead_to_campaign()`

**Hypothetical Input:**
```json
{
  "campaign_id": "camp_123",
  "lead": {
    "email": "new@hotel.com",
    "first_name": "John",
    "last_name": "Smith",
    "company": "New Hotel"
  },
  "personalization": {
    "referrer_name": "Sarah Jones"
  }
}
```

**Expected Output:**
```json
{
  "lead_id": "lead_new_789",
  "campaign_id": "camp_123",
  "status": "active",
  "sequence_position": 1,
  "first_email_scheduled": "2024-01-16T09:00:00Z"
}
```

---

### SL-010: Remove Lead from Campaign
**Function:** `SmartLeadClient.remove_lead_from_campaign()`

**Hypothetical Input:**
```json
{
  "lead_email": "unsubscribed@hotel.com",
  "campaign_id": "camp_123",
  "reason": "unsubscribe"
}
```

**Expected Output:**
```json
{
  "lead_email": "unsubscribed@hotel.com",
  "removed": true,
  "removal_reason": "unsubscribe",
  "removed_at": "2024-01-15T10:00:00Z"
}
```

---

### SL-011: Blocklist Management
**Function:** `SmartLeadClient.add_to_blocklist()`

**Hypothetical Input:**
```json
{
  "email": "blocked@hotel.com",
  "reason": "hard_bounce"
}
```

**Expected Output:**
```json
{
  "email": "blocked@hotel.com",
  "blocklisted": true,
  "blocklist_type": "global",
  "reason": "hard_bounce"
}
```

---

## 15. Lead Scoring System

### SCORE-001: Calculate Email Engagement Score
**Function:** `LeadScoringService.calculate_email_score()`
**File:** `app/services/scoring/service.py`

**Hypothetical Input:**
```json
{
  "contact_email": "engaged@hotel.com",
  "engagement": {
    "emails_sent": 3,
    "emails_opened": 3,
    "emails_clicked": 2,
    "emails_replied": 1
  }
}
```

**Expected Output:**
```json
{
  "email_score": 85,
  "scoring_breakdown": {
    "open_rate_points": 30,
    "click_rate_points": 25,
    "reply_points": 30
  }
}
```

---

### SCORE-002: Calculate LinkedIn Engagement Score
**Function:** `LeadScoringService.calculate_linkedin_score()`

**Hypothetical Input:**
```json
{
  "contact_email": "connected@hotel.com",
  "linkedin_engagement": {
    "connection_status": "connected",
    "messages_sent": 2,
    "messages_received": 1,
    "profile_views": 3
  }
}
```

**Expected Output:**
```json
{
  "linkedin_score": 70,
  "scoring_breakdown": {
    "connection_points": 20,
    "message_engagement_points": 30,
    "profile_interest_points": 20
  }
}
```

---

### SCORE-003: Combined Lead Score
**Function:** `LeadScoringService.calculate_combined_score()`

**Hypothetical Input:**
```json
{
  "contact_email": "hotlead@hotel.com",
  "email_score": 85,
  "linkedin_score": 70,
  "weights": {
    "email": 0.6,
    "linkedin": 0.4
  }
}
```

**Expected Output:**
```json
{
  "combined_score": 79,
  "weighted_email": 51,
  "weighted_linkedin": 28,
  "lead_grade": "A"
}
```

---

### SCORE-004: Score Threshold Actions
**Function:** `LeadScoringService.check_score_thresholds()`

**Hypothetical Input:**
```json
{
  "contact_email": "hotlead@hotel.com",
  "combined_score": 79,
  "thresholds": {
    "hot_lead": 75,
    "warm_lead": 50,
    "cold_lead": 25
  }
}
```

**Expected Output:**
```json
{
  "lead_status": "hot_lead",
  "actions_triggered": [
    "notify_sales_team",
    "add_to_priority_queue",
    "schedule_immediate_followup"
  ]
}
```

---

### SCORE-005: HubSpot Score Sync
**Function:** `LeadScoringService.sync_to_hubspot()`

**Hypothetical Input:**
```json
{
  "contact_email": "hotlead@hotel.com",
  "hubspot_contact_id": "hs_123",
  "combined_score": 79,
  "lead_grade": "A"
}
```

**Expected Output:**
```json
{
  "hubspot_updated": true,
  "properties_updated": {
    "lead_score": 79,
    "lead_grade": "A",
    "scoring_updated_at": "2024-01-15T10:00:00Z"
  }
}
```

---

## 16. Channel Switching Rules

### CHANNEL-001: Email → LinkedIn Trigger
**Function:** `ChannelOrchestrator.should_add_linkedin()`
**File:** `app/services/orchestration/channel.py`

**Hypothetical Input:**
```json
{
  "contact_email": "prospect@hotel.com",
  "email_engagement": {
    "emails_sent": 3,
    "emails_opened": 2,
    "emails_replied": 0
  },
  "has_linkedin_url": true
}
```

**Expected Output:**
```json
{
  "add_linkedin": true,
  "reason": "Email opens without reply - add LinkedIn touchpoint",
  "linkedin_action": "send_connection_request",
  "delay_days": 2
}
```

---

### CHANNEL-002: LinkedIn → Phone Trigger
**Function:** `ChannelOrchestrator.should_escalate_to_phone()`

**Hypothetical Input:**
```json
{
  "contact_email": "prospect@hotel.com",
  "email_status": "replied_interested",
  "linkedin_status": "connected_active",
  "has_phone": true
}
```

**Expected Output:**
```json
{
  "escalate_to_phone": true,
  "reason": "High engagement on email and LinkedIn - ready for call",
  "phone_action": "schedule_call",
  "priority": "high"
}
```

---

### CHANNEL-003: No Response Escalation
**Function:** `ChannelOrchestrator.handle_no_response()`

**Hypothetical Input:**
```json
{
  "contact_email": "silent@hotel.com",
  "days_since_last_touch": 14,
  "channels_attempted": ["email"],
  "available_channels": ["linkedin", "phone"]
}
```

**Expected Output:**
```json
{
  "next_channel": "linkedin",
  "action": "send_connection_request",
  "message": "Different approach - LinkedIn outreach",
  "escalation_level": 2
}
```

---

### CHANNEL-004: Multi-channel Sequence Orchestration
**Function:** `ChannelOrchestrator.execute_multi_channel_sequence()`

**Hypothetical Input:**
```json
{
  "contact_email": "target@hotel.com",
  "sequence": [
    {"day": 0, "channel": "email", "action": "send_intro"},
    {"day": 3, "channel": "email", "action": "followup_1"},
    {"day": 5, "channel": "linkedin", "action": "connection_request"},
    {"day": 7, "channel": "email", "action": "followup_2"},
    {"day": 10, "channel": "linkedin", "action": "dm_if_connected"}
  ]
}
```

**Expected Output:**
```json
{
  "sequence_started": true,
  "contact_email": "target@hotel.com",
  "total_steps": 5,
  "channels_involved": ["email", "linkedin"],
  "estimated_duration_days": 10
}
```

---

## 17. End-to-End Workflow Tests

### WF-001: Category 1.1 Full Flow (Ready to Chat with Phone)
**Workflow:** Email Reply → Categorization → Tasks → Teams → HubSpot → LinkedIn

**Hypothetical Input (Email Reply):**
```json
{
  "event_type": "EMAIL_REPLY",
  "lead_email": "interested@grandhotel.com",
  "reply_text": "This sounds great! Call me at 555-123-4567 to discuss further.",
  "campaign_id": "camp_123"
}
```

**Expected Full Flow Output:**
```json
{
  "workflow_steps": [
    {
      "step": 1,
      "action": "webhook_received",
      "status": "completed",
      "duration_ms": 50
    },
    {
      "step": 2,
      "action": "ai_categorization",
      "status": "completed",
      "result": {
        "main_category": "INTERESTED",
        "subcategory": "READY_TO_CHAT_PHONE",
        "confidence": 0.95,
        "phone_extracted": "555-123-4567"
      },
      "duration_ms": 1200
    },
    {
      "step": 3,
      "action": "hubspot_contact_update",
      "status": "completed",
      "fields_updated": ["category", "subcategory", "phone"]
    },
    {
      "step": 4,
      "action": "hubspot_tasks_created",
      "status": "completed",
      "tasks": [
        {"type": "Review Interested Reply", "priority": "HIGH"},
        {"type": "LinkedIn Connection Request", "priority": "HIGH"},
        {"type": "Send appointment suggestion", "priority": "HIGH"}
      ]
    },
    {
      "step": 5,
      "action": "teams_notification_sent",
      "status": "completed",
      "message_type": "Action required, lead ready to chat"
    },
    {
      "step": 6,
      "action": "linkedin_profile_lookup",
      "status": "completed",
      "profile_found": true
    }
  ],
  "total_duration_ms": 2500,
  "workflow_success": true
}
```

---

### WF-002: Category 1.4 Full Flow (Connect with Another Person)
**Workflow:** Reply → Categorization → Extract Referral → Create Contact → Add to Campaign

**Hypothetical Input:**
```json
{
  "reply_text": "I'm not the right person. Contact Sarah Johnson at sarah@grandhotel.com - she handles insurance.",
  "lead_email": "wrong@grandhotel.com"
}
```

**Expected Full Flow Output:**
```json
{
  "workflow_steps": [
    {
      "step": 1,
      "action": "categorization",
      "result": {"category": "INTERESTED", "subcategory": "CONNECT_ANOTHER"}
    },
    {
      "step": 2,
      "action": "referral_extraction",
      "referral": {"name": "Sarah Johnson", "email": "sarah@grandhotel.com", "role": "insurance"}
    },
    {
      "step": 3,
      "action": "hubspot_contact_created",
      "new_contact_id": "hs_new_456"
    },
    {
      "step": 4,
      "action": "smartlead_campaign_add",
      "campaign_id": "camp_123",
      "personalization": "Referred by colleague at Grand Hotel"
    },
    {
      "step": 5,
      "action": "original_contact_updated",
      "status": "referred"
    }
  ],
  "workflow_success": true
}
```

---

### WF-003: Category 2.1 Full Flow (Referral)
**Workflow:** Reply → Categorization → Extract → Create HubSpot Contact → Auto-Campaign → Immediate Followup

**Hypothetical Input:**
```json
{
  "reply_text": "You should contact John Smith at ABC Hotels - john@abchotels.com. He's looking for exactly this.",
  "lead_email": "referrer@hotel.com"
}
```

**Expected Full Flow Output:**
```json
{
  "workflow_steps": [
    {
      "step": 1,
      "action": "categorization",
      "result": {"category": "POSITIVE_SIGNALS", "subcategory": "REFERRAL", "confidence": 0.96}
    },
    {
      "step": 2,
      "action": "referral_parsed",
      "referral": {"name": "John Smith", "email": "john@abchotels.com", "company": "ABC Hotels"}
    },
    {
      "step": 3,
      "action": "hubspot_task_created",
      "task": {"type": "Create Referral Contact Record", "priority": "HIGHEST"}
    },
    {
      "step": 4,
      "action": "hubspot_contact_created",
      "contact": {"email": "john@abchotels.com", "lead_source": "Referral"}
    },
    {
      "step": 5,
      "action": "smartlead_campaign_add",
      "message": "Hi John, referrer@hotel.com suggested I reach out..."
    },
    {
      "step": 6,
      "action": "teams_notification",
      "message": "Action required, lead referred other contact"
    }
  ],
  "total_duration_ms": 3000,
  "workflow_success": true
}
```

---

### WF-004: Category 5.2 Full Flow (No Longer Works Here)
**Workflow:** Reply → Categorization → Research Task → Apollo Lookup → Update Contact

**Hypothetical Input:**
```json
{
  "reply_text": "John Smith no longer works here. He left 3 months ago.",
  "lead_email": "john@oldcompany.com"
}
```

**Expected Full Flow Output:**
```json
{
  "workflow_steps": [
    {
      "step": 1,
      "action": "categorization",
      "result": {"category": "AUTOMATE_REPLY", "subcategory": "NO_LONGER_WORKS_HERE"}
    },
    {
      "step": 2,
      "action": "hubspot_contact_update",
      "status": "no_longer_employed"
    },
    {
      "step": 3,
      "action": "task_created",
      "task": {"type": "Research Current Contact", "priority": "LOW"}
    },
    {
      "step": 4,
      "action": "apollo_company_lookup",
      "company": "oldcompany.com",
      "new_contacts_found": 3
    },
    {
      "step": 5,
      "action": "smartlead_pause",
      "lead_email": "john@oldcompany.com"
    }
  ],
  "workflow_success": true
}
```

---

### WF-005: Multi-step Email Sequence Execution
**Workflow:** Full 3-5 step email sequence with tracking

**Hypothetical Input:**
```json
{
  "contact_email": "prospect@hotel.com",
  "campaign_id": "camp_123",
  "sequence_id": "seq_456"
}
```

**Expected Full Flow Output:**
```json
{
  "sequence_execution": [
    {
      "step": 1,
      "day": 0,
      "email_sent": true,
      "subject": "Insurance for Grand Hotel",
      "status": "delivered"
    },
    {
      "step": 2,
      "day": 3,
      "email_sent": true,
      "subject": "Following up",
      "status": "opened",
      "opened_at": "2024-01-18T10:00:00Z"
    },
    {
      "step": 3,
      "day": 7,
      "email_sent": true,
      "subject": "Quick question",
      "status": "replied",
      "reply_received": "2024-01-22T14:00:00Z"
    }
  ],
  "sequence_completed": false,
  "sequence_interrupted_reason": "prospect_replied",
  "final_engagement_score": 85
}
```

---

## 18. Reliability & Uptime Tests

### REL-001: 99.5% Uptime Health Check
**Endpoint:** `GET /health`
**Requirement:** 99.5% availability

**Hypothetical Input:**
```json
{
  "test_duration_hours": 168,
  "check_interval_seconds": 30,
  "total_checks": 20160
}
```

**Expected Output:**
```json
{
  "total_checks": 20160,
  "successful_checks": 20059,
  "failed_checks": 101,
  "uptime_percentage": 99.5,
  "meets_sla": true,
  "average_response_time_ms": 25
}
```

---

### REL-002: Database Backup Verification
**Requirement:** Backup every 6 hours

**Hypothetical Input:**
```json
{
  "verify_period_hours": 24,
  "expected_backups": 4
}
```

**Expected Output:**
```json
{
  "backups_found": 4,
  "backup_times": [
    "2024-01-15T00:00:00Z",
    "2024-01-15T06:00:00Z",
    "2024-01-15T12:00:00Z",
    "2024-01-15T18:00:00Z"
  ],
  "all_backups_verified": true,
  "backup_sizes_mb": [250, 252, 251, 253],
  "restore_test_passed": true
}
```

---

### REL-003: System Failure Alerting
**Function:** `AlertingService.trigger_alert()`

**Hypothetical Input:**
```json
{
  "error_type": "database_connection_lost",
  "severity": "critical",
  "affected_component": "postgresql"
}
```

**Expected Output:**
```json
{
  "alert_triggered": true,
  "notification_channels": ["sentry", "teams", "pagerduty"],
  "alert_id": "alert_critical_123",
  "escalation_started": true,
  "time_to_alert_ms": 500
}
```

---

### REL-004: System Auto-Recovery
**Function:** `RecoveryService.attempt_recovery()`

**Hypothetical Input:**
```json
{
  "failure_type": "celery_worker_crash",
  "affected_workers": 2
}
```

**Expected Output:**
```json
{
  "recovery_attempted": true,
  "recovery_actions": [
    {"action": "restart_worker", "worker_id": "worker_1", "success": true},
    {"action": "restart_worker", "worker_id": "worker_2", "success": true}
  ],
  "recovery_time_seconds": 45,
  "within_sla": true,
  "sla_threshold_seconds": 300
}
```

---

## 19. Scalability Tests

### SCALE-001: 100K+ Contacts Query
**Requirement:** Support 100,000+ contacts with <100ms queries

**Hypothetical Input:**
```json
{
  "total_contacts": 150000,
  "query": "SELECT * FROM contacts WHERE company_type = 'Hotel Chain' AND validation_status = 'validated'",
  "expected_results": 5000
}
```

**Expected Output:**
```json
{
  "query_executed": true,
  "results_returned": 5000,
  "execution_time_ms": 85,
  "within_threshold": true,
  "threshold_ms": 100,
  "index_used": "idx_contacts_company_validation"
}
```

---

### SCALE-002: Horizontal Scaling Coordination
**Function:** `ScalingService.coordinate_instances()`

**Hypothetical Input:**
```json
{
  "instances": ["instance_1", "instance_2", "instance_3"],
  "task_type": "reengagement_scan",
  "total_contacts": 100000
}
```

**Expected Output:**
```json
{
  "coordination_success": true,
  "work_distribution": {
    "instance_1": {"start": 0, "end": 33333, "count": 33333},
    "instance_2": {"start": 33334, "end": 66666, "count": 33333},
    "instance_3": {"start": 66667, "end": 100000, "count": 33334}
  },
  "no_duplicates": true,
  "no_gaps": true
}
```

---

### SCALE-003: Queue Backpressure Handling
**Function:** `QueueService.handle_backpressure()`

**Hypothetical Input:**
```json
{
  "queue_name": "categorization",
  "current_depth": 5000,
  "max_depth": 1000,
  "incoming_rate_per_second": 50
}
```

**Expected Output:**
```json
{
  "backpressure_detected": true,
  "actions_taken": [
    "webhook_response_delayed",
    "new_workers_spawned",
    "alert_sent"
  ],
  "new_worker_count": 2,
  "estimated_drain_time_minutes": 15
}
```

---

## 20. Success Criteria Tests

### SUCCESS-001: 99% Webhook Delivery Rate
**Requirement:** 99% webhook delivery success

**Hypothetical Input:**
```json
{
  "test_period_days": 30,
  "webhooks_received": 10000
}
```

**Expected Output:**
```json
{
  "webhooks_received": 10000,
  "webhooks_processed_successfully": 9920,
  "webhooks_failed": 80,
  "delivery_success_rate": 0.992,
  "meets_criteria": true,
  "threshold": 0.99
}
```

---

### SUCCESS-002: <1% Categorization Error Rate
**Requirement:** Less than 1% categorization errors

**Hypothetical Input:**
```json
{
  "test_period_days": 30,
  "total_categorizations": 5000,
  "manual_review_sample": 500
}
```

**Expected Output:**
```json
{
  "total_categorizations": 5000,
  "sampled_for_review": 500,
  "correct_categorizations": 496,
  "incorrect_categorizations": 4,
  "error_rate": 0.008,
  "meets_criteria": true,
  "threshold": 0.01
}
```

---

### SUCCESS-003: <5 Minute System Recovery
**Requirement:** System recovery within 5 minutes

**Hypothetical Input:**
```json
{
  "simulated_failure": "full_system_crash",
  "components_affected": ["api", "workers", "scheduler"]
}
```

**Expected Output:**
```json
{
  "failure_detected_at": "2024-01-15T10:00:00Z",
  "recovery_completed_at": "2024-01-15T10:03:45Z",
  "recovery_time_seconds": 225,
  "recovery_time_minutes": 3.75,
  "meets_criteria": true,
  "threshold_minutes": 5
}
```

---

### SUCCESS-004: 100% Data Sync Consistency
**Requirement:** Perfect data consistency across systems

**Hypothetical Input:**
```json
{
  "sync_operation": "hubspot_contact_sync",
  "contacts_synced": 1000,
  "systems": ["database", "hubspot", "smartlead"]
}
```

**Expected Output:**
```json
{
  "contacts_checked": 1000,
  "database_records": 1000,
  "hubspot_records": 1000,
  "smartlead_records": 1000,
  "mismatches": 0,
  "consistency_rate": 1.0,
  "meets_criteria": true
}
```

---

## 21. Maintenance Task Tests

### MAINT-001: Weekly Database Optimization
**Function:** `MaintenanceService.optimize_database()`

**Hypothetical Input:**
```json
{
  "optimization_type": "weekly",
  "tables": ["contacts", "tasks", "communications"]
}
```

**Expected Output:**
```json
{
  "optimization_completed": true,
  "tables_optimized": ["contacts", "tasks", "communications"],
  "actions_performed": [
    {"table": "contacts", "action": "VACUUM ANALYZE", "duration_ms": 5000},
    {"table": "tasks", "action": "REINDEX", "duration_ms": 2000},
    {"table": "communications", "action": "VACUUM ANALYZE", "duration_ms": 8000}
  ],
  "space_reclaimed_mb": 150,
  "query_performance_improvement": "15%"
}
```

---

### MAINT-002: Daily Log Rotation Verification
**Function:** `MaintenanceService.verify_log_rotation()`

**Hypothetical Input:**
```json
{
  "log_directory": "/var/log/outreach",
  "expected_rotation": "daily"
}
```

**Expected Output:**
```json
{
  "rotation_verified": true,
  "current_log_file": "app.log",
  "rotated_files": [
    "app.log.2024-01-14.gz",
    "app.log.2024-01-13.gz",
    "app.log.2024-01-12.gz"
  ],
  "compression_applied": true,
  "retention_days": 30,
  "oldest_file_age_days": 28
}
```

---

### MAINT-003: Monthly API Key Rotation
**Function:** `MaintenanceService.rotate_api_keys()`

**Hypothetical Input:**
```json
{
  "keys_to_rotate": ["hubspot", "apollo", "smartlead"],
  "rotation_reason": "monthly_schedule"
}
```

**Expected Output:**
```json
{
  "rotation_completed": true,
  "keys_rotated": [
    {"service": "hubspot", "old_key_revoked": true, "new_key_active": true},
    {"service": "apollo", "old_key_revoked": true, "new_key_active": true},
    {"service": "smartlead", "old_key_revoked": true, "new_key_active": true}
  ],
  "connectivity_verified": true,
  "rotation_logged": true
}
```

---

### MAINT-004: Weekly Backup Verification
**Function:** `MaintenanceService.verify_backups()`

**Hypothetical Input:**
```json
{
  "verification_period_days": 7,
  "backup_location": "s3://backups/outreach/"
}
```

**Expected Output:**
```json
{
  "verification_completed": true,
  "backups_checked": 28,
  "backups_valid": 28,
  "backups_corrupted": 0,
  "restore_test_performed": true,
  "restore_test_success": true,
  "data_integrity_verified": true
}
```

---

## 22. Database Schema Validation Tests

### DB-001: validation_status ENUM Test
**Function:** Database constraint validation

**Hypothetical Input:**
```json
{
  "table": "contacts",
  "column": "validation_status",
  "test_values": ["pending", "validated", "rejected", "invalid_value"]
}
```

**Expected Output:**
```json
{
  "valid_values_accepted": ["pending", "validated", "rejected"],
  "invalid_values_rejected": ["invalid_value"],
  "constraint_enforced": true,
  "default_value": "pending"
}
```

---

### DB-002: validation_confidence Range Test
**Function:** Database constraint validation

**Hypothetical Input:**
```json
{
  "table": "contacts",
  "column": "validation_confidence",
  "test_values": [0.0, 0.5, 0.85, 1.0, 1.5, -0.1]
}
```

**Expected Output:**
```json
{
  "valid_values_accepted": [0.0, 0.5, 0.85, 1.0],
  "invalid_values_rejected": [1.5, -0.1],
  "range_enforced": true,
  "min_value": 0.0,
  "max_value": 1.0,
  "precision": 2
}
```

---

### DB-003: priority ENUM Test
**Function:** Database constraint validation

**Hypothetical Input:**
```json
{
  "table": "tasks",
  "column": "priority",
  "test_values": ["highest", "high", "medium", "low", "urgent"]
}
```

**Expected Output:**
```json
{
  "valid_values_accepted": ["highest", "high", "medium", "low"],
  "invalid_values_rejected": ["urgent"],
  "constraint_enforced": true
}
```

---

### DB-004: ms_teams_message_id Storage Test
**Function:** Database field validation

**Hypothetical Input:**
```json
{
  "table": "tasks",
  "column": "ms_teams_message_id",
  "test_value": "1234567890abcdef1234567890abcdef1234567890abcdef"
}
```

**Expected Output:**
```json
{
  "value_stored": true,
  "value_retrieved": "1234567890abcdef1234567890abcdef1234567890abcdef",
  "max_length": 100,
  "nullable": true,
  "index_exists": true
}
```

---

## 23. Additional Missing Task Types

### TASK-014: Clarify Product Misunderstanding
**Function:** `TaskService.create_tasks_for_category()`

**Hypothetical Input:**
```json
{
  "categorization": {
    "main_category": "INTERESTED",
    "subcategory": "MISUNDERSTOOD_INTERESTED"
  },
  "contact": {
    "email": "confused@hotel.com",
    "name": "Jane Doe"
  },
  "misunderstanding": "Thought we offered health insurance"
}
```

**Expected Output:**
```json
{
  "tasks_created": [
    {
      "type": "Clarify Product Misunderstanding",
      "priority": "HIGH",
      "due_date": "2024-01-15T23:59:59Z",
      "description": "Clarify that we offer property/liability insurance, not health insurance"
    }
  ]
}
```

---

### TASK-015: Send Competitor Battle Card
**Function:** `TaskService.create_tasks_for_category()`

**Hypothetical Input:**
```json
{
  "categorization": {
    "main_category": "POSITIVE_SIGNALS",
    "subcategory": "COMPETITOR_MENTION"
  },
  "competitor_mentioned": "Allstate"
}
```

**Expected Output:**
```json
{
  "tasks_created": [
    {
      "type": "Send Competitor Battle Card",
      "priority": "HIGH",
      "competitor": "Allstate",
      "battle_card_url": "https://internal.com/battlecards/allstate"
    }
  ]
}
```

---

### TASK-016: Book Discovery Call
**Function:** `TaskService.create_tasks_for_category()`

**Hypothetical Input:**
```json
{
  "categorization": {
    "main_category": "POSITIVE_SIGNALS",
    "subcategory": "BUDGET_CONFIRMED"
  },
  "budget_mentioned": "$50,000"
}
```

**Expected Output:**
```json
{
  "tasks_created": [
    {
      "type": "Book Discovery Call",
      "priority": "HIGH",
      "meeting_link": "https://meetings.hubspot.com/company/discovery",
      "suggested_agenda": ["Budget discussion", "Coverage options", "Timeline"]
    }
  ]
}
```

---

### TASK-017: Send NPS Feedback Survey
**Function:** `TaskService.create_tasks_for_category()`

**Hypothetical Input:**
```json
{
  "categorization": {
    "main_category": "NOT_INTERESTED",
    "subcategory": "NOT_INTERESTED"
  },
  "contact_interacted": true
}
```

**Expected Output:**
```json
{
  "tasks_created": [
    {
      "type": "Send NPS Feedback Survey",
      "priority": "LOW",
      "due_date": "2024-01-22T23:59:59Z",
      "survey_link": "https://survey.company.com/nps"
    }
  ]
}
```

---

### TASK-018: Research Current Contact
**Function:** `TaskService.create_tasks_for_category()`

**Hypothetical Input:**
```json
{
  "categorization": {
    "main_category": "AUTOMATE_REPLY",
    "subcategory": "NO_LONGER_WORKS_HERE"
  },
  "company_domain": "grandhotel.com"
}
```

**Expected Output:**
```json
{
  "tasks_created": [
    {
      "type": "Research Current Contact",
      "priority": "LOW",
      "action": "Use Apollo to find replacement contact at grandhotel.com"
    }
  ]
}
```

---

### TASK-019: Document Forward Recipient
**Function:** `TaskService.create_tasks_for_category()`

**Hypothetical Input:**
```json
{
  "categorization": {
    "main_category": "AUTOMATE_REPLY",
    "subcategory": "AUTO_FORWARD"
  },
  "forward_recipient": "procurement@hotel.com"
}
```

**Expected Output:**
```json
{
  "tasks_created": [
    {
      "type": "Document Forward Recipient",
      "priority": "LOW",
      "forward_to": "procurement@hotel.com",
      "action": "Create new contact and link to original"
    }
  ]
}
```

---

## 24. Additional MS Teams Notification Messages

### TEAMS-008: "Action required, interested lead"
**Function:** `TeamsNotificationService.send_notification()`

**Hypothetical Input:**
```json
{
  "category": "INTERESTED",
  "contact": {"name": "John Smith", "company": "Grand Hotel"}
}
```

**Expected Output:**
```json
{
  "message_sent": true,
  "title": "[ACTION REQUIRED] Interested: John Smith - Grand Hotel",
  "body": "Action required, interested lead",
  "priority_badge": "HIGH"
}
```

---

### TEAMS-009: "Action required, lead ready to chat"
**Function:** `TeamsNotificationService.send_notification()`

**Hypothetical Input:**
```json
{
  "subcategory": "READY_TO_CHAT_PHONE",
  "phone_extracted": "555-123-4567"
}
```

**Expected Output:**
```json
{
  "message_sent": true,
  "body": "Action required, lead ready to chat",
  "phone_displayed": "555-123-4567",
  "call_button_included": true
}
```

---

### TEAMS-010: "Action required, intrigued lead"
**Function:** `TeamsNotificationService.send_notification()`

**Hypothetical Input:**
```json
{
  "subcategory": "INTRIGUED",
  "questions_asked": ["pricing", "coverage options"]
}
```

**Expected Output:**
```json
{
  "message_sent": true,
  "body": "Action required, intrigued lead",
  "questions_highlighted": ["pricing", "coverage options"]
}
```

---

### TEAMS-011: "Action required, internal handoff"
**Function:** `TeamsNotificationService.send_notification()`

**Hypothetical Input:**
```json
{
  "subcategory": "CONNECT_ANOTHER",
  "referral_info": {"name": "Sarah", "department": "Insurance"}
}
```

**Expected Output:**
```json
{
  "message_sent": true,
  "body": "Action required, internal handoff",
  "handoff_to": "Sarah in Insurance department"
}
```

---

### TEAMS-012: "Urgent positive signal"
**Function:** `TeamsNotificationService.send_notification()`

**Hypothetical Input:**
```json
{
  "category": "POSITIVE_SIGNALS",
  "subcategory": "BUDGET_CONFIRMED",
  "budget": "$50,000"
}
```

**Expected Output:**
```json
{
  "message_sent": true,
  "body": "Urgent positive signal",
  "priority_badge": "HIGHEST",
  "signal_details": "Budget confirmed: $50,000"
}
```

---

### TEAMS-013: "Action required, lead referred other contact"
**Function:** `TeamsNotificationService.send_notification()`

**Hypothetical Input:**
```json
{
  "subcategory": "REFERRAL",
  "referral": {"name": "John Smith", "email": "john@abc.com"}
}
```

**Expected Output:**
```json
{
  "message_sent": true,
  "body": "Action required, lead referred other contact",
  "priority_badge": "HIGHEST",
  "referral_details": "John Smith (john@abc.com)"
}
```

---

### TEAMS-014: "Clarify misunderstanding"
**Function:** `TeamsNotificationService.send_notification()`

**Hypothetical Input:**
```json
{
  "subcategory": "MISUNDERSTOOD_INTERESTED",
  "misunderstanding": "Thought we offered health insurance"
}
```

**Expected Output:**
```json
{
  "message_sent": true,
  "body": "Clarify misunderstanding",
  "clarification_needed": "Thought we offered health insurance"
}
```

---

## 25. Additional Apollo.io Tests

### APOLLO-001: Email Validation
**Function:** `ApolloClient.validate_email()`

**Hypothetical Input:**
```json
{
  "email": "prospect@hotel.com"
}
```

**Expected Output:**
```json
{
  "email": "prospect@hotel.com",
  "is_valid": true,
  "deliverability": "deliverable",
  "confidence": 0.95,
  "mx_records_found": true
}
```

---

### APOLLO-002: Bulk Email Validation
**Function:** `ApolloClient.validate_emails_bulk()`

**Hypothetical Input:**
```json
{
  "emails": [
    "valid@hotel.com",
    "invalid@nonexistent.com",
    "risky@catchall.com"
  ]
}
```

**Expected Output:**
```json
{
  "results": [
    {"email": "valid@hotel.com", "status": "valid", "confidence": 0.95},
    {"email": "invalid@nonexistent.com", "status": "invalid", "confidence": 0.99},
    {"email": "risky@catchall.com", "status": "risky", "confidence": 0.60}
  ],
  "valid_count": 1,
  "invalid_count": 1,
  "risky_count": 1
}
```

---

### APOLLO-003: Company Data Retrieval
**Function:** `ApolloClient.get_company_data()`

**Hypothetical Input:**
```json
{
  "domain": "marriott.com"
}
```

**Expected Output:**
```json
{
  "company": {
    "name": "Marriott International",
    "domain": "marriott.com",
    "industry": "Hospitality",
    "employee_count": 121000,
    "revenue_range": "$10B+",
    "founded_year": 1927,
    "headquarters": "Bethesda, MD",
    "linkedin_url": "https://linkedin.com/company/marriott-international",
    "technologies": ["Salesforce", "Oracle", "SAP"],
    "description": "Marriott International is a leading global lodging company..."
  }
}
```

---

## 26. Additional HubSpot Tests

### HS-011: Deal Pipeline Management
**Function:** `HubSpotClient.move_deal_stage()`

**Hypothetical Input:**
```json
{
  "deal_id": "hs_deal_123",
  "from_stage": "qualifiedtobuy",
  "to_stage": "presentationscheduled"
}
```

**Expected Output:**
```json
{
  "deal_id": "hs_deal_123",
  "stage_updated": true,
  "previous_stage": "qualifiedtobuy",
  "new_stage": "presentationscheduled",
  "stage_history_logged": true
}
```

---

### HS-012: Custom Field Management
**Function:** `HubSpotClient.create_custom_property()`

**Hypothetical Input:**
```json
{
  "object_type": "contacts",
  "property": {
    "name": "outreach_category",
    "label": "Outreach Category",
    "type": "enumeration",
    "options": ["INTERESTED", "POSITIVE_SIGNALS", "NOT_INTERESTED", "NEGATIVE_SIGNALS", "AUTOMATE_REPLY"]
  }
}
```

**Expected Output:**
```json
{
  "property_created": true,
  "property_name": "outreach_category",
  "options_count": 5
}
```

---

### HS-013: Notes Creation
**Function:** `HubSpotClient.create_note()`

**Hypothetical Input:**
```json
{
  "contact_id": "hs_contact_123",
  "note_body": "Prospect expressed interest in Q2. Follow up after their fiscal year ends.",
  "associated_objects": ["contact", "deal"]
}
```

**Expected Output:**
```json
{
  "note_id": "note_456",
  "note_created": true,
  "associations": {
    "contact": "hs_contact_123",
    "deal": "hs_deal_789"
  }
}
```

---

### HS-014: Lead Score Property Update
**Function:** `HubSpotClient.update_lead_score()`

**Hypothetical Input:**
```json
{
  "contact_id": "hs_contact_123",
  "lead_score": 85,
  "score_components": {
    "email_engagement": 50,
    "linkedin_engagement": 35
  }
}
```

**Expected Output:**
```json
{
  "contact_id": "hs_contact_123",
  "lead_score_updated": true,
  "new_score": 85,
  "score_history_logged": true
}
```

---

### HS-015: Association Management
**Function:** `HubSpotClient.create_association()`

**Hypothetical Input:**
```json
{
  "from_object_type": "contacts",
  "from_object_id": "hs_contact_123",
  "to_object_type": "companies",
  "to_object_id": "hs_company_456",
  "association_type": "primary"
}
```

**Expected Output:**
```json
{
  "association_created": true,
  "from": {"type": "contacts", "id": "hs_contact_123"},
  "to": {"type": "companies", "id": "hs_company_456"},
  "association_type": "primary"
}
```

---

## Summary

| Category | Test Count |
|----------|------------|
| Campaign Setup & Lead Validation | 7 |
| Webhook Handlers | 11 |
| AI Response Categorization | 26 |
| HubSpot Task Generation | 19 |
| MS Teams Notifications | 14 |
| LinkedIn Integration | 8 |
| HubSpot CRM Integration | 15 |
| Re-engagement Pipeline | 11 |
| Referral Auto-Campaign | 6 |
| Performance Requirements | 6 |
| Monitoring & Metrics | 9 |
| Error Handling & Retry | 7 |
| Compliance | 6 |
| SmartLead Campaign Management | 11 |
| Lead Scoring System | 5 |
| Channel Switching Rules | 4 |
| End-to-End Workflows | 5 |
| Reliability & Uptime | 4 |
| Scalability | 3 |
| Success Criteria | 4 |
| Maintenance Tasks | 4 |
| Database Schema Validation | 4 |
| Apollo.io Functions | 3 |
| **Total** | **192** |

---

## Related Files

| Component | Primary Files |
|-----------|--------------|
| Webhooks | `app/api/webhooks/smartlead.py`, `app/api/webhooks/connectsafely.py`, `app/api/webhooks/heyreach.py` |
| Categorization | `app/services/categorization/service.py`, `app/services/categorization/prompts.py` |
| Integrations | `app/integrations/hubspot/client.py`, `app/integrations/apollo/client.py`, `app/integrations/smartlead/client.py`, `app/integrations/connectsafely/client.py`, `app/integrations/heyreach/client.py` |
| Tasks | `app/services/tasks/service.py`, `app/workers/categorization_tasks.py` |
| Notifications | `app/services/notifications/teams.py` |
| Re-engagement | `app/services/reengagement/service.py`, `app/workers/reengagement_tasks.py` |
| Referral | `app/services/referral/extractor.py`, `app/services/referral/enrollment.py` |
| Metrics | `app/core/metrics.py` |
| Logging | `app/core/logging.py` |
| Database | `app/db/session.py` |
| Compliance | `app/services/compliance/service.py` |
