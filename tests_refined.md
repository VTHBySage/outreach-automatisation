# Test Scenarios - Human Readable Version

This document contains 192 hypothetical test scenarios organized by functional area. Each test describes what to send, what should happen, and how to verify success.

---

## Quick Navigation

1. [Campaign Setup & Lead Validation](#1-campaign-setup--lead-validation) (7 tests)
2. [Webhook Handlers](#2-webhook-handlers) (11 tests)
3. [AI Response Categorization](#3-ai-response-categorization) (26 tests)
4. [HubSpot Task Generation](#4-hubspot-task-generation) (19 tests)
5. [MS Teams Notifications](#5-ms-teams-notifications) (14 tests)
6. [LinkedIn Integration](#6-linkedin-integration) (8 tests)
7. [HubSpot CRM](#7-hubspot-crm) (15 tests)
8. [Re-engagement Pipeline](#8-re-engagement-pipeline) (11 tests)
9. [Referral Auto-Campaign](#9-referral-auto-campaign) (6 tests)
10. [Performance](#10-performance) (6 tests)
11. [Monitoring & Metrics](#11-monitoring--metrics) (9 tests)
12. [Error Handling](#12-error-handling) (7 tests)
13. [Compliance](#13-compliance) (6 tests)
14. [SmartLead Management](#14-smartlead-management) (11 tests)
15. [Lead Scoring](#15-lead-scoring) (5 tests)
16. [Channel Switching](#16-channel-switching) (4 tests)
17. [End-to-End Workflows](#17-end-to-end-workflows) (5 tests)
18. [Reliability & Uptime](#18-reliability--uptime) (4 tests)
19. [Scalability](#19-scalability) (3 tests)
20. [Success Criteria](#20-success-criteria) (4 tests)
21. [Maintenance Tasks](#21-maintenance-tasks) (4 tests)
22. [Database Validation](#22-database-validation) (4 tests)
23. [Apollo.io Functions](#23-apolloio-additional-functions) (3 tests)

**Total: 192 tests**

---

## 1. Campaign Setup & Lead Validation

### CS-001: Search for a person in Apollo
**What to test:** Apollo contact search by email
**Send:** Email "john.smith@hiltonhotels.com" with name "John Smith"
**Expect:** Returns person data with email, title, LinkedIn URL, and company info
**Verify:** Email accuracy should be 91%+ per requirements

### CS-002: Enrich a company from Apollo
**What to test:** Apollo company/organization enrichment
**Send:** Domain "marriott.com"
**Expect:** Returns company name, industry (Hospitality), employee count, phone, LinkedIn URL
**Verify:** All key company fields populated

### CS-003: Get LinkedIn profile from HeyReach
**What to test:** HeyReach contact enrichment
**Send:** Email "sarah.jones@ihg.com"
**Expect:** Returns LinkedIn URL, name, headline, location, connection count
**Verify:** LinkedIn URL is valid and matches the contact

### CS-004: Crawl a company website
**What to test:** Web crawler extracts company info
**Send:** URL "https://www.hyatt.com/about"
**Expect:** Returns page title, description, content text, industry signals
**Verify:** Content is sufficient for LLM validation

### CS-005: Validate company matches campaign criteria (PASS)
**What to test:** LLM validates "Hotel Chain" vs "Airbnb"
**Send:** Company "Grand Hyatt Singapore" with website content about luxury hotel
**Expect:** Returns is_valid=true, company_type="Hotel Chain", confidence=0.92
**Verify:** Confidence >= 85% triggers automatic inclusion

### CS-006: Validate company with borderline confidence (REVIEW)
**What to test:** LLM flags borderline cases for manual review
**Send:** Company "Boutique Inn & Suites" - unclear if hotel chain or B&B
**Expect:** Returns is_valid=null, confidence=0.78, status="pending_review"
**Verify:** Confidence 75-85% triggers manual review queue

### CS-007: Combine Apollo and HeyReach data
**What to test:** Data enrichment merges multiple sources
**Send:** Apollo data (email, title, phone) + HeyReach data (LinkedIn URL, headline)
**Expect:** Returns unified profile with all fields from both sources
**Verify:** No data loss, completeness score calculated

---

## 2. Webhook Handlers

### WH-001: SmartLead email reply webhook
**What to test:** Receiving and processing an email reply
**Send:** POST to /webhook/smartlead with event_type="EMAIL_REPLY", lead_email, reply_text
**Expect:** Returns status="accepted", queues Celery task for categorization
**Verify:** Contact updated in database, categorization task created

### WH-002: SmartLead email opened webhook
**What to test:** Tracking email opens
**Send:** POST to /webhook/smartlead with event_type="EMAIL_OPENED"
**Expect:** Returns status="accepted", increments open metrics
**Verify:** Prometheus counter incremented, campaign stats updated

### WH-003: SmartLead email clicked webhook
**What to test:** Tracking link clicks
**Send:** POST to /webhook/smartlead with event_type="EMAIL_CLICKED", clicked_url
**Expect:** Returns status="accepted", increments click metrics
**Verify:** Click URL logged, engagement score updated

### WH-004: SmartLead email bounced webhook
**What to test:** Handling hard bounces
**Send:** POST to /webhook/smartlead with event_type="EMAIL_BOUNCED", bounce_type="hard"
**Expect:** Returns contact_status="bounced", triggers suppression
**Verify:** Contact suppressed, HubSpot updated, task created for permanent suppression

### WH-005: SmartLead unsubscribe webhook
**What to test:** Immediate compliance with unsubscribe
**Send:** POST to /webhook/smartlead with event_type="EMAIL_UNSUBSCRIBED"
**Expect:** Contact immediately suppressed across all campaigns
**Verify:** Removed from SmartLead, HubSpot DNC flagged, blocklist added

### WH-006: SmartLead signature validation
**What to test:** HMAC signature verification
**Send (valid):** Webhook with correct X-Smartlead-Signature header
**Expect (valid):** Returns status="accepted"
**Send (invalid):** Webhook with wrong signature
**Expect (invalid):** Returns 401 "Invalid webhook signature"

### WH-007: ConnectSafely connection accepted
**What to test:** LinkedIn connection acceptance handling
**Send:** POST to /webhook/connectsafely with event_type="connection_accepted"
**Expect:** Contact LinkedIn status updated to "connected", DM draft created
**Verify:** Task created to send DM

### WH-008: ConnectSafely connection rejected
**What to test:** LinkedIn connection rejection handling
**Send:** POST to /webhook/connectsafely with event_type="connection_rejected"
**Expect:** Contact status updated to "rejected", re-engagement scheduled
**Verify:** Logged for analytics, 90-day re-engagement set

### WH-009: ConnectSafely message received
**What to test:** LinkedIn DM reply processing
**Send:** POST to /webhook/connectsafely with event_type="message_received", message_text
**Expect:** Queues categorization task for LinkedIn reply
**Verify:** Source marked as "linkedin", same categorization flow as email

### WH-010: HeyReach connection accepted
**What to test:** HeyReach LinkedIn connection handling
**Send:** POST to /webhook/heyreach with event_type="connection_accepted"
**Expect:** Contact status updated, next workflow step triggered
**Verify:** DM sequence can proceed

### WH-011: HeyReach message received
**What to test:** HeyReach LinkedIn DM processing
**Send:** POST to /webhook/heyreach with event_type="message_received"
**Expect:** Categorization triggered, referral detection if applicable
**Verify:** Same processing as ConnectSafely messages

---

## 3. AI Response Categorization

### Category 1: INTERESTED (7 subcategories)

| Test ID | Subcategory | Sample Reply | Expected Result |
|---------|-------------|--------------|-----------------|
| CAT-101 | Ready to chat (phone) | "Call me at 555-123-4567" | INTERESTED > READY_TO_CHAT_PHONE, extracts phone |
| CAT-102 | Intrigued | "What pricing tiers do you offer?" | INTERESTED > INTRIGUED, notes questions asked |
| CAT-103 | Ready to chat (open) | "Sure, let's schedule a call" | INTERESTED > READY_TO_CHAT_OPEN |
| CAT-104 | Connect with another | "Talk to Sarah in our Dallas office" | INTERESTED > CONNECT_ANOTHER, extracts referral |
| CAT-105 | Misunderstood interested | "Yes, but I thought you meant X" | INTERESTED > MISUNDERSTOOD_INTERESTED |
| CAT-106 | Long-term followup | "Reach back in Q3 next year" | INTERESTED > LONG_TERM_FOLLOWUP, extracts date |
| CAT-107 | Pitching own service | "We also offer insurance services" | INTERESTED > PITCHING_SERVICE |

### Category 2: POSITIVE SIGNALS (4 subcategories)

| Test ID | Subcategory | Sample Reply | Expected Result |
|---------|-------------|--------------|-----------------|
| CAT-201 | Referral | "Contact John Smith at ABC Corp" | POSITIVE_SIGNALS > REFERRAL, extracts contact info |
| CAT-202 | Competitor mention | "We're using Allstate currently" | POSITIVE_SIGNALS > COMPETITOR_MENTION |
| CAT-203 | Budget confirmed | "We have $50K budgeted for this" | POSITIVE_SIGNALS > BUDGET_CONFIRMED |
| CAT-204 | Authority confirmed | "I'm the VP in charge of this" | POSITIVE_SIGNALS > AUTHORITY_CONFIRMED |

### Category 3: NOT INTERESTED (5 subcategories)

| Test ID | Subcategory | Sample Reply | Expected Result |
|---------|-------------|--------------|-----------------|
| CAT-301 | Wrong company | "We're a residential property" | NOT_INTERESTED > WRONG_COMPANY |
| CAT-302 | Not interested | "No thanks, not interested" | NOT_INTERESTED > NOT_INTERESTED |
| CAT-303 | Self disqualify | "We're too small for this" | NOT_INTERESTED > SELF_DISQUALIFY |
| CAT-304 | Misunderstood not interested | "No, I thought you meant Y" | NOT_INTERESTED > MISUNDERSTOOD_NOT_INTERESTED |
| CAT-305 | Unsubscribe | "Remove me from your list" | NOT_INTERESTED > UNSUBSCRIBE, immediate suppression |

### Category 4: NEGATIVE SIGNALS (3 subcategories)

| Test ID | Subcategory | Sample Reply | Expected Result |
|---------|-------------|--------------|-----------------|
| CAT-401 | Happy with competitor | "We're very happy with StateFarm" | NEGATIVE_SIGNALS > HAPPY_WITH_COMPETITOR |
| CAT-402 | Recent purchase | "Just renewed our policy last month" | NEGATIVE_SIGNALS > RECENT_PURCHASE, 365-day re-engage |
| CAT-403 | Wrong timing | "Contact me after Q2" | NEGATIVE_SIGNALS > WRONG_TIMING, extracts date |

### Category 5: AUTOMATE REPLY (7 subcategories)

| Test ID | Subcategory | Sample Reply | Expected Result |
|---------|-------------|--------------|-----------------|
| CAT-501 | Out of Office | "I'm OOO until March 15" | AUTOMATE_REPLY > OUT_OF_OFFICE, extracts return date |
| CAT-502 | No longer works here | "John left the company 6 months ago" | AUTOMATE_REPLY > NO_LONGER_WORKS_HERE |
| CAT-503 | Auto acknowledge | "[Auto-Reply] Message received" | AUTOMATE_REPLY > AUTO_ACKNOWLEDGE |
| CAT-504 | Auto forward | "Your message was forwarded to..." | AUTOMATE_REPLY > AUTO_FORWARD |
| CAT-505 | Auto reply connect | "[Auto] Contact support@company.com" | AUTOMATE_REPLY > AUTO_REPLY_CONNECT |
| CAT-506 | Empty reply | (blank response) | AUTOMATE_REPLY > EMPTY_REPLY |
| CAT-507 | Hard bounce | "550 User not found" | AUTOMATE_REPLY > HARD_BOUNCE |

---

## 4. HubSpot Task Generation

### Standard Tasks by Category

| Test ID | Trigger Category | Task Created | Priority | Due Date |
|---------|-----------------|--------------|----------|----------|
| TASK-001 | INTERESTED | "Review Interested Reply" | HIGH | Same day |
| TASK-002 | INTERESTED | "LinkedIn Connection Request and DM" | HIGH | Same day |
| TASK-003 | INTERESTED | "Send appointment suggestion" | HIGH | Same day |
| TASK-004 | CONNECT_ANOTHER | "Internal Colleague Assignment" | HIGH | Same day |
| TASK-005 | LONG_TERM_FOLLOWUP | "Prepare 90-Day Nurture Content" | LOW | 1 week |
| TASK-006 | REFERRAL | "Create Referral Contact Record" | HIGHEST | < 12 hours |
| TASK-007 | REFERRAL | "Follow-up Referral Immediately" | HIGHEST | < 12 hours |
| TASK-008 | NOT_INTERESTED | "Schedule 90-Day Nurture Email" | LOW | 1 week |
| TASK-009 | WRONG_COMPANY | "Apollo Research Correct Contact" | LOW | 1 week |
| TASK-010 | NEGATIVE_SIGNALS | "Schedule 180-Day Re-engagement Review" | LOW | 1 week |
| TASK-011 | RECENT_PURCHASE | "Track Contract Renewal Date" | LOW | 1 week |
| TASK-012 | HARD_BOUNCE | "Permanent Email Suppression" | LOW | Auto-complete |
| TASK-013 | All | Verify due date calculation by priority | - | - |

### Additional Task Types (Missing from Original)

| Test ID | Trigger | Task Created | Priority |
|---------|---------|--------------|----------|
| TASK-014 | MISUNDERSTOOD_INTERESTED | "Clarify Product Misunderstanding" | HIGH |
| TASK-015 | COMPETITOR_MENTION | "Send Competitor Battle Card" | HIGH |
| TASK-016 | BUDGET_CONFIRMED | "Book Discovery Call" | HIGH |
| TASK-017 | NOT_INTERESTED | "Send NPS Feedback Survey" | LOW |
| TASK-018 | NO_LONGER_WORKS_HERE | "Research Current Contact" | LOW |
| TASK-019 | AUTO_FORWARD | "Document Forward Recipient" | LOW |

---

## 5. MS Teams Notifications

### Standard Notifications

| Test ID | What to Test | Expected Message |
|---------|--------------|------------------|
| TEAMS-001 | High priority interested lead | Adaptive Card with lead details, draft response |
| TEAMS-002 | Highest priority referral | Adaptive Card with HIGHEST badge, immediate action |
| TEAMS-003 | Notification format | "[ACTION REQUIRED] [Category]: [Name] - [Company]" |
| TEAMS-004 | HubSpot task URL | Direct clickable link to HubSpot task |
| TEAMS-005 | Draft message | AI-generated response draft included |
| TEAMS-006 | Meeting agenda | Draft agenda for call-ready leads |
| TEAMS-007 | Time zone handling | Suggested times in prospect's timezone |

### Specific Notification Messages (from Requirements 3.3.2)

| Test ID | Trigger | Expected Message Title |
|---------|---------|----------------------|
| TEAMS-008 | INTERESTED category | "Action required, interested lead" |
| TEAMS-009 | READY_TO_CHAT | "Action required, lead ready to chat" |
| TEAMS-010 | INTRIGUED | "Action required, intrigued lead" |
| TEAMS-011 | CONNECT_ANOTHER | "Action required, internal handoff" |
| TEAMS-012 | POSITIVE_SIGNALS | "Urgent positive signal" |
| TEAMS-013 | REFERRAL | "Action required, lead referred other contact" |
| TEAMS-014 | MISUNDERSTOOD | "Clarify misunderstanding" |

---

## 6. LinkedIn Integration

### ConnectSafely Tests

| Test ID | What to Test | Input | Expected Result |
|---------|--------------|-------|-----------------|
| LI-001 | Profile lookup by email | email="exec@hotel.com" | Returns LinkedIn URL, name, headline |
| LI-002 | Send connection request | profile_url + message | Returns status="sent", request_id |
| LI-003 | Send direct message | profile_url + message | Returns status="sent", delivered_at |
| LI-004 | Check connection status | profile_url | Returns "not_connected", "pending", "connected", or "rejected" |

### HeyReach Tests

| Test ID | What to Test | Input | Expected Result |
|---------|--------------|-------|-----------------|
| LI-005 | Contact enrichment | email | Returns LinkedIn profile data |
| LI-006 | Add to campaign | linkedin_url + campaign_id | Returns lead_id, sequence position |
| LI-007 | Pause in campaign | lead_id + campaign_id | Returns status="paused" |
| LI-008 | Full LinkedIn flow | High interest email reply | Profile lookup → Connection → DM draft → Task |

---

## 7. HubSpot CRM

### Contact Operations

| Test ID | What to Test | Expected Result |
|---------|--------------|-----------------|
| HS-001 | Create contact | New contact created with all fields |
| HS-002 | Update contact after categorization | Category, subcategory, confidence updated |
| HS-003 | Get contact by email | Returns contact with all properties |
| HS-009 | Update custom fields | validation_status, company_type updated |
| HS-010 | Set re-engagement date | Date set based on category rules |

### Task & Deal Operations

| Test ID | What to Test | Expected Result |
|---------|--------------|-----------------|
| HS-004 | Create task | Task with priority, due date, association |
| HS-005 | Update task status | Status changed to COMPLETED |
| HS-006 | Create deal | Deal created for interested lead |
| HS-007 | Update deal stage | Stage moved in pipeline |
| HS-008 | Create meeting | Meeting with HubSpot link |
| HS-011 | Move deal through pipeline | Stage history logged |

### Additional HubSpot Tests

| Test ID | What to Test | Expected Result |
|---------|--------------|-----------------|
| HS-012 | Create custom property | New property with options created |
| HS-013 | Add note to contact | Note created with associations |
| HS-014 | Update lead score | Score property updated, history logged |
| HS-015 | Create association | Contact linked to company/deal |

---

## 8. Re-engagement Pipeline

### Timeline by Category

| Test ID | Category | Days Until Re-engagement | Action |
|---------|----------|-------------------------|--------|
| RE-001 | Wrong contact | 30 days | Research correct contact |
| RE-002 | Self-disqualify | 60 days | Nurture content |
| RE-003 | Long-term / Not interested | 90 days | Re-initiate sequence |
| RE-004 | Not interested + NPS | 120 days | Survey + soft re-engage |
| RE-005 | Negative signals | 180 days | Check if still happy |
| RE-006 | Recent purchase | 365 days | Pre-renewal outreach |
| RE-007 | Wrong timing | Prospect-defined | "After Q2" → July 1 |

### Pipeline Operations

| Test ID | What to Test | Expected Result |
|---------|--------------|-----------------|
| RE-008 | Monthly scan job | Identifies all contacts due for re-engagement |
| RE-009 | SmartLead re-sequence | Contact added to re-engagement campaign |
| RE-010 | ConnectSafely re-sequence | LinkedIn re-engagement triggered |
| RE-011 | Suppression check | Suppressed contacts skipped |

---

## 9. Referral Auto-Campaign

| Test ID | What to Test | Input | Expected Result |
|---------|--------------|-------|-----------------|
| REF-001 | Extract full referral | "Contact John at john@abc.com" | Name, email, company extracted |
| REF-002 | Extract name-only referral | "Talk to Sarah in accounting" | Name, department extracted, needs enrichment |
| REF-003 | Create HubSpot contact | Extracted referral data | New contact with lead_source="Referral" |
| REF-004 | Add to SmartLead | Referral + referrer name | "Referred by [name]" personalization |
| REF-005 | Add to HeyReach | Referral + referrer name | LinkedIn campaign with referral context |
| REF-006 | Link referral | New contact + referrer | Association created between contacts |

---

## 10. Performance

| Test ID | Metric | Requirement | How to Test |
|---------|--------|-------------|-------------|
| PERF-001 | Webhook response time | < 200ms | Time from POST to response |
| PERF-002 | Categorization time | < 2 seconds | Time for AI to categorize reply |
| PERF-003 | Task generation time | < 1 second | Time after categorization to task creation |
| PERF-004 | Database query time | < 100ms | Query contacts table with 10K records |
| PERF-005 | Concurrent webhooks | 99% success with 100 concurrent | Load test webhooks endpoint |
| PERF-006 | Daily email volume | 1,000+ emails/day | Process full day's volume without failure |

---

## 11. Monitoring & Metrics

| Test ID | What to Monitor | Expected Behavior |
|---------|-----------------|-------------------|
| MON-001 | Rate limit tracking | Track HubSpot API usage percentage |
| MON-002 | Rate limit alert | Alert at 80% consumption |
| MON-003 | Slow query detection | Log queries > 100ms |
| MON-004 | Connection pool | Track checked out/available connections |
| MON-005 | Email open rate | Calculate from webhook events |
| MON-006 | Email click rate | Calculate from webhook events |
| MON-007 | Reply rate | Calculate replies per campaign |
| MON-008 | Conversion rate | Calculate replies → meetings |
| MON-009 | Categorization accuracy | Track confidence score distribution |

---

## 12. Error Handling

| Test ID | Error Type | Expected Behavior |
|---------|------------|-------------------|
| ERR-001 | API timeout | Retry with exponential backoff |
| ERR-002 | Rate limit (429) | Wait for Retry-After header, then retry |
| ERR-003 | Invalid webhook payload | Return 400, log error |
| ERR-004 | Invalid signature | Return 401, log security alert |
| ERR-005 | LLM failure | Retry up to 3 times with backoff |
| ERR-006 | Celery task failure | Auto-retry with max_retries=3 |
| ERR-007 | Uncaught exception | Capture to Sentry, alert team |

---

## 13. Compliance

| Test ID | Requirement | Expected Behavior |
|---------|-------------|-------------------|
| COMP-001 | Unsubscribe handling | Immediate suppression (< 1 second) |
| COMP-002 | Do Not Contact | Block across all channels |
| COMP-003 | LinkedIn rate limits | Respect ConnectSafely limits |
| COMP-004 | Data export | Export all contact data on request |
| COMP-005 | Data deletion | Delete from all systems on request |
| COMP-006 | Audit logging | Log all actions with timestamp |

---

## 14. SmartLead Management

| Test ID | What to Test | Input | Expected Result |
|---------|--------------|-------|-----------------|
| SL-001 | Create campaign | Name, sending accounts, limits | Campaign created in draft status |
| SL-002 | Add/remove tags | Lead email + tag name | Tag added/removed from lead |
| SL-003 | Update lead category | Lead email + category | Category synced to SmartLead |
| SL-004 | Send automated reply | Lead email + message | Reply sent in thread |
| SL-005 | Create email sequence | 3-5 steps with intervals | Sequence created with timing |
| SL-006 | Check warmup status | Email account | Returns warmup score, daily limit |
| SL-007 | Check throttle status | Email account | Returns sent today, remaining |
| SL-008 | Query master inbox | Filter options | Returns unified inbox messages |
| SL-009 | Add lead to campaign | Lead data + campaign ID | Lead added, first email scheduled |
| SL-010 | Remove from campaign | Lead email + reason | Lead removed, reason logged |
| SL-011 | Add to blocklist | Email + reason | Globally blocked |

---

## 15. Lead Scoring

| Test ID | What to Test | Input | Expected Result |
|---------|--------------|-------|-----------------|
| SCORE-001 | Email engagement score | Opens, clicks, replies | Score 0-100 based on engagement |
| SCORE-002 | LinkedIn engagement score | Connection, messages, views | Score 0-100 based on activity |
| SCORE-003 | Combined score | Email score + LinkedIn score | Weighted average, letter grade A-F |
| SCORE-004 | Score threshold actions | Score reaches 75+ | Trigger "hot lead" notifications |
| SCORE-005 | Sync to HubSpot | Lead score + contact ID | lead_score property updated |

---

## 16. Channel Switching

| Test ID | Scenario | Decision | Action |
|---------|----------|----------|--------|
| CHANNEL-001 | Email opens, no reply | Add LinkedIn | Send connection request after 2 days |
| CHANNEL-002 | Email + LinkedIn engaged | Escalate to phone | Create call task |
| CHANNEL-003 | No response 14 days | Switch channel | Try next available channel |
| CHANNEL-004 | Multi-channel orchestration | Sequence execution | Day 0 email → Day 3 email → Day 5 LinkedIn → Day 7 email |

---

## 17. End-to-End Workflows

### WF-001: "Ready to Chat" Full Flow
**Trigger:** Email reply "Call me at 555-123-4567"
**Steps:**
1. Webhook received → Categorization queued
2. AI categorizes as INTERESTED > READY_TO_CHAT_PHONE
3. Phone number extracted
4. HubSpot contact updated
5. 3 HubSpot tasks created (all HIGH priority)
6. MS Teams notification sent
7. LinkedIn profile lookup initiated

**Success:** All steps complete in < 3 seconds

### WF-002: "Connect with Another" Full Flow
**Trigger:** Email reply "Contact Sarah at sarah@hotel.com"
**Steps:**
1. Categorize as INTERESTED > CONNECT_ANOTHER
2. Extract referral (Sarah, sarah@hotel.com)
3. Create new HubSpot contact for Sarah
4. Add Sarah to SmartLead with "Referred by [original]" message
5. Update original contact status

**Success:** New contact created and added to campaign

### WF-003: "Referral" Full Flow
**Trigger:** Email reply "Contact John Smith at ABC Hotels"
**Steps:**
1. Categorize as POSITIVE_SIGNALS > REFERRAL
2. Parse referral (John Smith, ABC Hotels)
3. Create HIGHEST priority task
4. Create HubSpot contact for John
5. Add to SmartLead with referral personalization
6. Send MS Teams notification

**Success:** Referral processed in < 3 seconds

### WF-004: "No Longer Works Here" Full Flow
**Trigger:** Email reply "John left 3 months ago"
**Steps:**
1. Categorize as AUTOMATE_REPLY > NO_LONGER_WORKS_HERE
2. Update contact status
3. Create task "Research Current Contact"
4. Trigger Apollo company lookup
5. Pause SmartLead sequence

**Success:** Contact paused, research task created

### WF-005: Multi-step Email Sequence
**Trigger:** New lead added to campaign
**Steps:**
1. Day 0: First email sent
2. Day 3: Second email sent (if no reply)
3. Day 7: Third email sent (if no reply)
4. Track opens/clicks throughout
5. Sequence stops if reply received

**Success:** All emails sent on schedule, stops on engagement

---

## 18. Reliability & Uptime

| Test ID | Requirement | Test Method | Pass Criteria |
|---------|-------------|-------------|---------------|
| REL-001 | 99.5% uptime | Monitor /health for 1 week | < 0.5% downtime |
| REL-002 | 6-hour backups | Check backup timestamps | 4 backups per day |
| REL-003 | Failure alerting | Trigger test failure | Alert in < 1 minute |
| REL-004 | Auto-recovery | Kill worker process | Restarts within 5 minutes |

---

## 19. Scalability

| Test ID | Requirement | Test Method | Pass Criteria |
|---------|-------------|-------------|---------------|
| SCALE-001 | 100K+ contacts | Query with 100K records | < 100ms response |
| SCALE-002 | Horizontal scaling | Run 3 instances | Work distributed evenly |
| SCALE-003 | Queue backpressure | Overflow queue | Graceful handling, alerts sent |

---

## 20. Success Criteria

| Test ID | Metric | Threshold | How to Measure |
|---------|--------|-----------|----------------|
| SUCCESS-001 | Webhook delivery | 99% | Successful / Total over 30 days |
| SUCCESS-002 | Categorization accuracy | < 1% error | Manual review sample |
| SUCCESS-003 | Recovery time | < 5 minutes | Time from failure to recovery |
| SUCCESS-004 | Data consistency | 100% | Compare DB vs HubSpot vs SmartLead |

---

## 21. Maintenance Tasks

| Test ID | Task | Frequency | Verification |
|---------|------|-----------|--------------|
| MAINT-001 | Database optimization | Weekly | VACUUM ANALYZE runs, space reclaimed |
| MAINT-002 | Log rotation | Daily | Old logs compressed, 30-day retention |
| MAINT-003 | API key rotation | Monthly | Old keys revoked, new keys work |
| MAINT-004 | Backup verification | Weekly | Test restore succeeds |

---

## 22. Database Validation

| Test ID | Field | Valid Values | Test |
|---------|-------|--------------|------|
| DB-001 | validation_status | pending, validated, rejected | Invalid values rejected |
| DB-002 | validation_confidence | 0.00 to 1.00 | Out-of-range rejected |
| DB-003 | priority | highest, high, medium, low | Invalid values rejected |
| DB-004 | ms_teams_message_id | Up to 100 chars | Store and retrieve works |

---

## 23. Apollo.io Additional Functions

| Test ID | What to Test | Input | Expected Result |
|---------|--------------|-------|-----------------|
| APOLLO-001 | Email validation | Single email address | Returns is_valid, deliverability status, confidence |
| APOLLO-002 | Bulk email validation | List of 3 emails | Returns valid/invalid/risky status for each |
| APOLLO-003 | Company data retrieval | Domain "marriott.com" | Returns full company profile with revenue, employees, tech stack |

---

## Summary Table

| Section | Tests | Status |
|---------|-------|--------|
| Campaign Setup & Lead Validation | 7 | Ready |
| Webhook Handlers | 11 | Ready |
| AI Response Categorization | 26 | Ready |
| HubSpot Task Generation | 19 | Ready |
| MS Teams Notifications | 14 | Ready |
| LinkedIn Integration | 8 | Ready |
| HubSpot CRM | 15 | Ready |
| Re-engagement Pipeline | 11 | Ready |
| Referral Auto-Campaign | 6 | Ready |
| Performance | 6 | Ready |
| Monitoring & Metrics | 9 | Ready |
| Error Handling | 7 | Ready |
| Compliance | 6 | Ready |
| SmartLead Management | 11 | Ready |
| Lead Scoring | 5 | Ready |
| Channel Switching | 4 | Ready |
| End-to-End Workflows | 5 | Ready |
| Reliability & Uptime | 4 | Ready |
| Scalability | 3 | Ready |
| Success Criteria | 4 | Ready |
| Maintenance Tasks | 4 | Ready |
| Database Validation | 4 | Ready |
| Apollo.io Functions | 3 | Ready |
| **TOTAL** | **192** | **Ready** |

---

## Key Files for Testing

| Component | Files |
|-----------|-------|
| Webhooks | `app/api/webhooks/smartlead.py`, `connectsafely.py`, `heyreach.py` |
| Categorization | `app/services/categorization/service.py`, `prompts.py` |
| Integrations | `app/integrations/hubspot/`, `apollo/`, `smartlead/`, `connectsafely/`, `heyreach/` |
| Tasks | `app/services/tasks/service.py` |
| Notifications | `app/services/notifications/teams.py` |
| Re-engagement | `app/services/reengagement/service.py` |
| Referral | `app/services/referral/extractor.py`, `enrollment.py` |
| Scoring | `app/services/scoring/service.py` |
| Metrics | `app/core/metrics.py` |
| Database | `app/db/session.py` |
