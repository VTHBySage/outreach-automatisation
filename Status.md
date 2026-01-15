# Outreach Automation System - Implementation Details

## Platform Architecture

Built the backend in Python 3.11 using FastAPI as the web framework. PostgreSQL handles all data storage through SQLAlchemy ORM. For background processing, set up Celery workers with Redis as the message broker - this allows the system to handle heavy tasks like AI categorization and HubSpot syncing without blocking the main application. Scheduled jobs run through Celery Beat for daily, hourly, and weekly maintenance tasks.

---

## SmartLead Integration

### Webhook Receiver
Created the `/webhook/smartlead` endpoint that receives email reply notifications. The handler parses SmartLead's payload format including their field names (`sl_lead_email`, `sl_email_lead_id`, `preview_text`, `time_replied`, etc.) with backward compatibility for older field names.

When a reply comes in, the system:
1. Finds the existing contact by email or creates a new one
2. Checks for duplicate replies using the external ID to avoid processing the same email twice
3. Stores the reply with subject, body text, and any HTML content
4. Updates the contact's last response timestamp
5. Logs the webhook for audit purposes
6. Queues the categorization task for background processing

The webhook responds immediately (under 200ms) while processing happens in the background.

### Outbound API Client
Built a full SmartLead API client for managing leads and campaigns:
- **Lead management**: Create leads, get lead by ID or email, update lead tags and categories
- **Campaign management**: Get campaigns (with status filter), get campaign details, get leads in a campaign
- **Lead assignment**: Add leads to campaigns with custom fields, remove leads from campaigns
- Used by the re-engagement pipeline to add contacts to nurture campaigns automatically

### SmartLead Mailbox Management
Added API methods for monitoring SmartLead mailbox health:
- **Warmup status**: `get_warmup_status(email_account_id)` - Check mailbox warmup progress, reputation score, daily limits, warmup days completed
- **Throttle status**: `get_throttle_status(email_account_id)` - Monitor send rates, daily limits, sent today count, remaining quota, throttle percentage
- **Master inbox**: `get_master_inbox(limit, offset, status, campaign_id)` - Query unified inbox across all mailboxes with filtering

These methods provide programmatic access to SmartLead's platform metrics for monitoring and alerting.

### SmartLead Platform Features (Native)
The following capabilities are handled by SmartLead's platform directly:
- **Automatic warmup**: Email warmup execution managed by SmartLead (we monitor via API)
- **Automatic throttling**: Send rate throttling managed by SmartLead (we monitor via API)
- **Sequence management**: Email sequences (3-5 steps, 3-5 day intervals) configured in SmartLead UI
- **Deliverability monitoring**: Sender reputation and bounce tracking managed by SmartLead

Our system integrates with SmartLead via webhooks (receiving replies) and API (managing leads/campaigns + monitoring mailbox health).

---

## ConnectSafely LinkedIn Integration

### Webhook Receiver
Created the `/webhook/connectsafely` endpoint for LinkedIn events. Handles connection accepted/rejected events, LinkedIn DM replies, and profile engagement. When a connection is accepted, the system updates the contact's LinkedIn URL. All events are logged for tracking.

### Outbound API Client
Built a ConnectSafely API client for LinkedIn outreach:
- **Profile lookup**: Find LinkedIn profiles by email address
- **Connection requests**: Send connection requests with optional personalized message
- **Direct messaging**: Send DMs to connected profiles
- **Status checking**: Check connection status with a profile
- **Message queue**: Retrieve pending messages awaiting approval
- Used by the re-engagement pipeline as an alternative channel for contacts with LinkedIn profiles

### LinkedIn DM Categorization
LinkedIn DM replies are categorized using the same AI taxonomy and prompts as email replies:
- When a `message_received` event arrives via webhook, the system creates a reply record with source "connectsafely"
- The same GPT-4o categorization service processes the DM content
- All 5 main categories and 26 subcategories apply equally to LinkedIn messages
- Tasks are generated with the same priority rules as email-based categorizations
- Re-engagement scheduling follows identical timelines

This ensures consistent lead handling regardless of whether the prospect replies via email or LinkedIn.

---

## Apollo.io Integration

Built an Apollo.io API client for lead data enrichment:
- **People search**: Search for contacts by email, name, company, or domain
- **Person enrichment**: Enrich contact data by email - returns name, phone, LinkedIn URL, title, company details
- **Organization enrichment**: Enrich company data by domain - returns industry, size, description
- **Contact info helper**: Combined method that fetches and formats all available contact data
- **Email validation**: Validate single email deliverability - returns is_valid, deliverability status (deliverable/undeliverable/risky), confidence score
- **Bulk email validation**: Batch validate up to 100 emails per request with automatic batching for larger lists

Used by lead validation to fetch company information before AI validation, for enriching contact records with missing data, and for validating email quality before campaign enrollment.

---

## AI Response Categorization

Implemented the complete categorization system using OpenAI's GPT-4o model with structured JSON output. The system prompt defines all 5 main categories and 26 subcategories with clear descriptions and examples.

### Interested (Category 1)
- **1.1 Ready to chat (phone)** - Lead provided phone number or requested a call
- **1.2 Intrigued** - Asking questions about the offering
- **1.3 Ready to chat (open)** - Open to conversation without specific details
- **1.4 Connect with another** - Suggests talking to a colleague
- **1.5 Misunderstood interested** - Confused about offering but still interested
- **1.6 Long-term followup** - Interested but not ready now
- **1.7 Prospect pitching** - Trying to sell their own service back

### Positive Signals (Category 2)
- **2.1 Referral** - Refers another company or contact
- **2.2 Competitor mention** - Mentions competitors showing market awareness
- **2.3 Budget confirmed** - Confirms budget availability
- **2.4 Authority confirmed** - Confirms decision-making power

### Not Interested (Category 3)
- **3.1 Mistake (wrong company)** - Wrong company or division
- **3.2 Not interested** - Direct rejection
- **3.3 Self disqualify** - Explains why they're not a fit
- **3.4 Misunderstood not interested** - Confused and not interested
- **3.5 Unsubscribe** - Explicit opt-out request

### Negative Signals (Category 4)
- **4.1 Happy with competitor** - Satisfied with current solution
- **4.2 Recent purchase** - Recently bought competing solution
- **4.3 Wrong timing** - Bad timing but might revisit later

### Automate Reply (Category 5)
- **5.1 Out of Office** - Away from office auto-reply
- **5.2 No longer works here** - Person left company
- **5.3 Auto acknowledge** - Automated receipt confirmation
- **5.4 Auto forward** - Email forwarded automatically
- **5.5 Auto reply connect** - Auto-reply suggesting another contact
- **5.6 Empty reply** - No meaningful content
- **5.7 Hard bounce** - Delivery failure

Each categorization returns the main category, subcategory, confidence score (0-1), and reasoning explaining the classification. Processing targets under 2 seconds per reply.

### Immediate Unsubscribe Enforcement
When a reply is categorized as **Unsubscribe (3.5)** or **Hard Bounce (5.7)**, the system automatically suppresses the lead:
1. Categorization task detects unsubscribe/bounce subcategory
2. System extracts the contact's SmartLead lead ID and campaign ID from the reply record
3. Calls SmartLead API to immediately remove the lead from the campaign
4. Logs suppression action with contact ID, lead ID, campaign ID, and reason
5. Creates the "Permanent Email Suppression" task for audit trail

This ensures GDPR/CAN-SPAM compliance by honoring opt-out requests immediately rather than waiting for manual task processing. The suppression is best-effort - if the API call fails, the task is still created for manual follow-up.

---

## Task Generation

Built a task factory that automatically creates HubSpot tasks based on categorization results. Each subcategory has defined task templates with appropriate priorities.

### High-Value Lead Tasks (Highest/High Priority)
- Ready to chat leads get: Review Interested Reply, LinkedIn Connection Request and DM, Send appointment suggestion
- Referrals get: Create Referral Contact Record, Follow-up Referral Immediately (both Highest priority)
- Competitor mentions get: Send Competitor Battle Card
- Budget/Authority confirmed get: Book Discovery Call
- Internal handoffs get: Internal Colleague Assignment

### Follow-up Tasks (Medium/Low Priority)
- Wrong timing: Set Prospect-Defined Follow-up Date
- Not interested: Schedule 90-Day Nurture Email
- Wrong company: Apollo Research Correct Contact
- Misunderstood (interested or not): Clarify Product Misunderstanding (High priority)
- Happy with competitor: Schedule 180-Day Re-engagement Review
- Recent purchase: Track Contract Renewal Date
- No longer works here: Research Current Contact
- Hard bounce: Permanent Email Suppression

### Due Date Calculation
| Priority | Due In |
|----------|--------|
| Highest | 12 hours |
| High | 24 hours (same day) |
| Medium | 48 hours |
| Low | 168 hours (1 week) |

---

## HubSpot Integration

Built full HubSpot CRM integration with separate modules for contacts, tasks, deals, and meetings.

### Contact Sync
- Creates new contacts in HubSpot or finds existing ones by email
- Syncs name, company, phone, and custom properties
- Stores HubSpot contact ID locally for future reference

### Task Sync
- Creates tasks in HubSpot with proper priority mapping (HIGHEST/HIGH map to HIGH, MEDIUM stays MEDIUM, LOW stays LOW)
- Associates tasks with the related contact
- Sets due dates and descriptions
- Tracks sync status (pending, synced, failed) with error messages for failures
- Provides direct HubSpot task URLs in notifications

### Rate Limiting
- Respects HubSpot API limits (10 requests/minute for task operations)
- Failed syncs retry up to 3 times with exponential backoff
- Hourly batch job catches any tasks that weren't synced

### Notes/Engagements
Built a HubSpot Notes module for adding notes to contact records:
- **Create note**: `create_note(contact_id, body, timestamp, owner_id)` - Creates note and associates with contact
- **Get contact notes**: `get_contact_notes(contact_id, limit)` - Retrieves all notes for a contact via associations API
- **Delete note**: `delete_note(note_id)` - Removes a note

Uses HubSpot's CRM v3 notes API with v4 associations for linking notes to contacts. Useful for audit trails and manual annotations.

### Custom Property Management (Requirements.md 4.2.2)
Added methods for managing custom contact properties in HubSpot:
- **Get property**: `get_property(property_name)` - Get property definition, returns None if not found
- **Create property**: `create_property(name, label, property_type, field_type, group_name, description, options)` - Create new custom property
- **Update property**: `update_property(property_name, label, description, options)` - Update existing property
- **Get all properties**: `get_all_properties()` - List all contact properties
- **Ensure property exists**: `ensure_property_exists(name, label, ...)` - Idempotent property setup (creates if missing)

Supports property types: `string`, `number`, `date`, `datetime`, `enumeration`
Supports field types: `text`, `textarea`, `date`, `file`, `number`, `select`, `radio`, `checkbox`

Used for programmatic setup of custom fields like `validation_status`, `current_channel`, etc.

### Meeting Scheduling
Built meeting scheduling integration for booking calls with interested leads:
- **Get meeting link**: Retrieves personalized meeting links for HubSpot owners
- **Schedule with link**: Generates booking URLs with contact info pre-filled (email, name) via query parameters
- **Create meeting**: Creates meeting engagements with start/end times and descriptions
- **Timezone handling**: Uses ISO format timestamps with UTC for consistent scheduling across time zones
- **Owner assignment**: Assigns meetings to HubSpot owner with fallback to configured default

Used by task generation to include meeting links in high-priority task notifications.

---

## MS Teams Notifications

Built notification system that alerts the team about high-priority tasks. Only Highest and High priority tasks trigger notifications - Medium and Low are handled through HubSpot task queue.

### Category-Specific Notification Messages
Per Requirements.md 3.3.2, notifications now include category-specific banner messages:

| Subcategory | Notification Message |
|-------------|---------------------|
| Ready to Chat (1.1, 1.3) | "ACTION REQUIRED, LEAD READY TO CHAT" |
| Intrigued (1.2) | "ACTION REQUIRED, INTRIGUED LEAD" |
| Connect with Another (1.4) | "ACTION REQUIRED, INTERNAL HANDOFF" |
| Misunderstood (1.5, 3.4) | "CLARIFY MISUNDERSTANDING" |
| Long-term/Pitching (1.6, 1.7) | "ACTION REQUIRED, INTERESTED LEAD" |
| Referral (2.1) | "ACTION REQUIRED, LEAD REFERRED OTHER CONTACT" |
| Budget/Authority/Competitor (2.2-2.4) | "URGENT POSITIVE SIGNAL" |

Notifications are sent as Adaptive Cards containing:
- **Category message banner** (prominent, color-coded by priority)
- Action required header with category
- Lead name, company, email, and phone number
- Task description and priority level
- Direct link to the HubSpot task
- AI-generated draft response message tailored to the category
- Meeting agenda with talking points (for call-related tasks)

The system tracks which notifications were sent using the MS Teams message ID to avoid duplicates. There's also a batch summary feature for situations where many tasks are created at once.

---

## Re-engagement Pipeline

Implemented automatic re-engagement scheduling based on categorization. When a contact is categorized, the system calculates their re-engagement date:

| Timeline | Trigger | Reason |
|----------|---------|--------|
| 30 days | Wrong contact details | Time to find correct contact |
| 60 days | Self-disqualification | Situation may change |
| 90 days | Long-term followup, Not interested | Standard nurture |
| 120 days | Not interested after NPS survey | Extended nurture |
| 180 days | Happy with competitor, Prospect pitching | Longer cooling period |
| 365 days | Recent purchase | Wait for contract renewal cycle |
| No automatic date | Wrong timing | Prospect specifies their own timeline |

A daily background job runs that:
1. Finds all contacts where re-engagement date has passed
2. Determines the appropriate channel (LinkedIn if they have a profile and came from LinkedIn, otherwise email)
3. Adds them to a SmartLead re-engagement campaign or queues ConnectSafely connection request
4. Updates HubSpot with re-engagement status
5. Clears the re-engagement date so they're not processed again

### Human-in-the-Loop Controls
While re-engagement scheduling is automated, outbound actions have human oversight:

**Automated (no approval required):**
- Scheduling re-engagement dates based on categorization
- Adding contacts to SmartLead campaigns (SmartLead handles actual sending with its own warmup/throttling)
- Creating HubSpot tasks for follow-up

**Requires human action:**
- High-priority task responses (Teams notifications prompt immediate review)
- ConnectSafely messages can be configured to require approval before sending
- Manual task completion triggers in HubSpot

**Safety mechanisms:**
- Unsubscribe/bounce contacts are automatically suppressed and never re-engaged
- Re-engagement timelines are conservative (30-365 days based on category)
- Daily processing limits prevent bulk spam (100 contacts/run)
- All outbound actions logged for audit

---

## Channel Switching (Multi-Channel Orchestration)

Implemented automatic channel switching for the Email → LinkedIn → Phone flow when contacts don't respond.

### Service Architecture
Built `ChannelSwitchingService` that orchestrates outreach across channels:
- **Email to LinkedIn**: After 3 days without response on email, automatically triggers LinkedIn outreach
- **LinkedIn to Phone**: After 5 more days without LinkedIn response, escalates to phone call task

### Channel Switch Process

**Email → LinkedIn Transition:**
1. System detects contact has been emailed but no response for 3+ days
2. Looks up LinkedIn profile via ConnectSafely (by email if not already stored)
3. Queues LinkedIn connection request for human approval
4. Updates contact's `current_channel` to "linkedin"
5. Records `channel_switched_at` timestamp

**LinkedIn → Phone Transition:**
1. System detects LinkedIn channel active but no response for 5+ days
2. Creates high-priority phone call task with contact details
3. Updates contact's `current_channel` to "phone"
4. Phone is the terminal state (no further automatic escalation)

### Database Fields Added
New fields on Contact model:
- `current_channel` - Current outreach channel (email/linkedin/phone), defaults to "email"
- `channel_switched_at` - Timestamp of last channel switch
- `last_engagement_at` - Timestamp of last engagement activity

### Background Job
Daily Celery task `process_channel_switches` runs at 10 AM:
1. Finds all contacts eligible for channel switching
2. Processes email contacts with 3+ days no response
3. Processes LinkedIn contacts with 5+ days no response
4. Logs results: contacts switched to LinkedIn, switched to phone, skipped, errors

### Human-in-the-Loop
All channel switches respect the human approval requirement:
- LinkedIn connection requests are queued for approval (not auto-sent)
- Phone tasks require manual action
- System handles orchestration, humans handle execution

---

## Lead State Decision Matrix

### State Transitions
```
┌─────────────┐
│   NEW       │ Contact created from webhook or import
└──────┬──────┘
       │ Reply received
       ▼
┌─────────────┐
│ CATEGORIZED │ AI assigns category + subcategory
└──────┬──────┘
       │ Based on category:
       ▼
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  INTERESTED (1.x)  ──────► HIGH-PRIORITY TASK              │
│  │                         Teams notification               │
│  │                         HubSpot task (12-24hr due)       │
│  │                                                          │
│  POSITIVE SIGNALS (2.x) ──► HIGH-PRIORITY TASK             │
│  │                          Follow referral/confirm budget  │
│  │                                                          │
│  NOT INTERESTED (3.x) ────► SCHEDULE RE-ENGAGEMENT         │
│  │                          60-90 day nurture cycle         │
│  │                          Low priority task               │
│  │                                                          │
│  NEGATIVE SIGNALS (4.x) ──► LONG RE-ENGAGEMENT             │
│  │                          180-365 day wait                │
│  │                          Track competitor/renewal        │
│  │                                                          │
│  AUTOMATE REPLY (5.x) ────► SYSTEM HANDLING                │
│                             OOO: retry later                │
│                             Bounce: suppress + task         │
│                             No longer here: research task   │
└─────────────────────────────────────────────────────────────┘
```

### Channel Selection Criteria
| Condition | Primary Channel | Fallback |
|-----------|-----------------|----------|
| Has LinkedIn profile + LinkedIn source | ConnectSafely DM | Email via SmartLead |
| Has LinkedIn profile + Email source | Email via SmartLead | ConnectSafely if bounced |
| No LinkedIn profile | Email via SmartLead | Create research task |
| Previous channel bounced/failed | Switch to alternate | Manual review task |

### Suppression Rules (Never Re-engage)
- Subcategory 3.5 (Unsubscribe) → Permanent suppression
- Subcategory 5.7 (Hard Bounce) → Permanent suppression
- Contact marked as deleted → Excluded from all processing

---

## Lead Validation (LLM Company Validation)

Built comprehensive AI-powered company validation with configurable campaign targeting criteria.

### Campaign Model
Created `Campaign` model for storing target criteria per campaign:
- **Target types**: Array of company types to include (e.g., `["hotel_chain", "resort", "boutique_hotel"]`)
- **Target industries**: Array of industries to target (e.g., `["hospitality", "travel"]`)
- **Exclude types**: Company types to exclude (e.g., `["airbnb", "vacation_rental"]`)
- **Employee size filters**: `min_employees` and `max_employees`
- **Confidence thresholds**:
  - `min_confidence` (default 0.85) - Auto-approve threshold
  - `review_threshold` (default 0.75) - Manual review range

### Validation Flow
```
Lead → Homepage Crawl → Apollo Enrichment → LLM Analysis → Classification → Campaign Eligibility
```

1. **Homepage Crawling** (fast mode): Fetches homepage only for speed
   - Extracts title, meta description, keywords
   - Extracts services, social links, contact info
   - Uses homepage text as about content

2. **Apollo Enrichment** (optional): Fetches company data from Apollo API
   - Industry, employee count, description
   - Keywords, founding year, revenue

3. **LLM Classification**: GPT-4o analyzes combined data against campaign criteria
   - Returns: `is_match`, `confidence`, `company_type`, `reasoning`

### Validation Service
`CompanyValidationService` in `app/services/validation/`:
- `validate_company(company_name, company_domain, campaign)` - Single company validation
- `validate_contact(contact_id, campaign_id)` - Validates and updates contact record
- `batch_validate_contacts(campaign_id, limit)` - Batch validation for campaign

### Validation Tasks
Celery tasks in `app/workers/validation_tasks.py`:
- `validate_contact_company` - Single contact validation
- `batch_validate_campaign` - Batch validation for campaign
- `validate_all_campaigns` - Hourly job processing all active campaigns

| Confidence | Action |
|------------|--------|
| 85%+ | Automatically validated (`VALIDATED`) |
| 75-85% | Flagged for manual review (`PENDING`) |
| Below 75% | Rejected (`REJECTED`) |

### Database
New `campaigns` table with FK from `contacts.campaign_id`. Migration: `003_add_campaigns_table.py`

---

## Lead Scoring

Built a lead scoring service that calculates engagement scores for contacts on a 0-100 scale with four grades:

| Grade | Score Range | Meaning |
|-------|-------------|---------|
| HOT | 80-100 | Ready to buy, high engagement |
| WARM | 60-79 | Engaged, needs nurturing |
| COOL | 40-59 | Some interest shown |
| COLD | 0-39 | Low engagement |

### Scoring Factors

**Email Engagement (max 40 points)**
- Points per reply received
- Bonus points for positive replies (Interested, Positive Signals categories)
- Extra points for explicitly interested responses

**LinkedIn Engagement (max 20 points)**
- Has LinkedIn profile on record
- Connected status via ConnectSafely

**Company Fit (max 20 points)**
- Company validation status
- Validation confidence score

**Recency (max 20 points)**
- Activity within last 14 days
- Task completion rate above 50%
- Time since last reply (decays over 30 days)

### API Methods
- Calculate score for individual contact with full breakdown
- Update and store score on contact record
- Get all HOT leads for prioritized follow-up
- Get scoring summary across all contacts (grade distribution, average score)

---

## API Endpoints

### Contact Management
- List contacts with search (email, name, company), category filter, validation status filter, pagination
- Get single contact with all details
- Create new contact with duplicate email check
- Update contact fields
- Soft delete contact
- Get all tasks for a contact
- Get all email replies for a contact

### Task Management
- List tasks with filters for priority, sync status, assigned user, due date range, completion status
- Get pending tasks with contact details (name, email, company) for easy review
- Get tasks due today
- Create manual tasks
- Update task fields
- Mark task complete or reopen
- Trigger manual HubSpot sync
- Delete task

### Dashboard
- Overall statistics: total contacts, tasks, replies, pending/synced/failed task counts
- Contacts grouped by category
- Tasks grouped by priority
- Today's reply count and tasks due today
- Recent activity feed showing latest contacts, tasks, and replies
- HubSpot sync status overview with recent failure details
- Re-engagement calendar showing contacts due in the next 7 days

### GDPR Compliance
- Export all data for a contact (contact info, all replies, all tasks, webhook logs) as JSON
- Delete contact with option for soft delete (anonymize) or hard delete (permanent removal)
- Data retention policy endpoint explaining retention periods

---

## Background Jobs

### Daily - Re-engagement Processing (9 AM)
- Runs at configurable time (recommended 9 AM)
- Processes up to 100 contacts per run
- Adds to appropriate outreach channel

### Daily - Channel Switching (10 AM)
- Checks contacts for channel escalation
- Email → LinkedIn after 3 days no response
- LinkedIn → Phone after 5 more days no response
- Creates approval tasks for LinkedIn, phone call tasks for phone

### Hourly - Pending Task Sync
- Catches tasks that failed initial sync or were created manually
- Queues up to 200 tasks for HubSpot sync

### Weekly - Webhook Log Cleanup
- Deletes webhook logs older than 30 days
- Keeps database size manageable

---

## Database Structure

### contacts table
- **Basic info**: email (unique), first_name, last_name, phone, linkedin_url
- **Company info**: company_name, company_domain, company_type
- **Validation**: validation_status (pending/validated/rejected/manual_review), validation_confidence, validation_notes
- **Campaign tracking**: campaign_id, source (apollo/linkedin/manual)
- **Re-engagement**: re_engagement_date, re_engagement_category
- **Status**: last_contacted_at, last_response_at, current_category, current_subcategory
- **Channel switching**: current_channel (email/linkedin/phone), channel_switched_at, last_engagement_at
- **External IDs**: hubspot_contact_id, apollo_id, smartlead_lead_id
- **Soft delete support** with deleted_at timestamp

### email_replies table
- Links to contact
- **Source tracking**: source (smartlead/connectsafely), external_id, campaign_external_id
- **Content**: subject, body_text, body_html, received_at
- **Threading**: thread_id, in_reply_to
- **Categorization**: main_category, subcategory, categorization_confidence, categorization_reasoning, categorized_at
- **Processing status**: processed, tasks_created, notification_sent, processing_error

### tasks table
- Links to contact and optionally to triggering email reply
- **Task definition**: title, description, priority, category, subcategory, task_type
- **Assignment**: assigned_to, due_date
- **HubSpot sync**: hubspot_task_id, sync_status, synced_at, sync_error
- **Notifications**: ms_teams_message_id, notification_sent_at
- **Completion**: completed_at

### webhook_logs table
- **Request info**: source, endpoint, method, headers, payload
- **Processing**: processed flag, processing_time_ms, error message
- **Response**: response_status, response_body
- **Timestamp**: received_at

Indexes added for common query patterns - email lookup, re-engagement date queries, pending task queries, webhook cleanup.

---

## Audit and Logging

### Request Logging
Added middleware that logs every API request to the database including endpoint, method, headers, and response status.

### Structured Logging
Using structlog for consistent, contextual logging throughout the application:
- JSON format in production (ELK-compatible for centralized log aggregation)
- Console format with colors in development for readability
- Automatic context injection (contact IDs, task IDs, request IDs)
- ISO timestamps on all log entries
- All Celery tasks log their progress and any errors encountered

---

## Error Handling

- Webhook processing retries up to 3 times on failure
- HubSpot sync retries with exponential backoff
- Categorization failures are logged and can be reprocessed
- Task sync failures are tracked with error messages and included in dashboard
- Invalid data is rejected with clear error messages

---

## Monitoring

### Sentry Error Tracking
Integrated Sentry for centralized error monitoring:
- Initialized at application startup (before FastAPI app creation)
- Captures unhandled exceptions with full stack traces
- FastAPI integration for automatic request context
- Celery integration for background task error tracking
- Configurable via environment variables: `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE`
- PII protection enabled by default (send_default_pii=False)

### Prometheus Metrics
Exposed Prometheus-compatible metrics at `/metrics` endpoint:

**HTTP Request Metrics**
- `http_requests_total` - Counter by method, endpoint, status code
- `http_request_duration_seconds` - Histogram of request latency

**Webhook Metrics**
- `webhooks_total` - Counter by source (smartlead, connectsafely)
- `webhook_processing_seconds` - Processing time histogram

**AI Categorization Metrics**
- `categorizations_total` - Counter by category and subcategory
- `categorization_confidence` - Histogram of confidence scores
- `categorization_duration_seconds` - AI processing time

**Task Metrics**
- `tasks_created_total` - Counter by priority and category
- `tasks_synced_total` - Counter by sync status (success/failed)

**Suppression Metrics**
- `leads_suppressed_total` - Counter by reason (unsubscribe, hard_bounce)

**Email Engagement Metrics**
- `email_opens_total` - Counter by campaign_id
- `email_clicks_total` - Counter by campaign_id
- `email_replies_total` - Counter by campaign_id
- `email_bounces_total` - Counter by campaign_id and bounce_type (hard/soft)
- `email_unsubscribes_total` - Counter by campaign_id

**Rate Limit Monitoring Metrics**
- `rate_limit_hits_total` - Counter of 429 responses by integration (hubspot, smartlead, apollo, connectsafely, heyreach)
- `rate_limit_retries_total` - Counter of retry attempts by integration
- `api_requests_per_minute` - Gauge of current request rate by integration
- `rate_limit_threshold_alerts_total` - Counter of 80% threshold crossings

**Database Performance Metrics**
- `db_query_duration_seconds` - Histogram of query execution time by type (select/insert/update/delete)
- `db_slow_queries_total` - Counter of queries exceeding 100ms threshold
- `db_connection_pool_size` - Gauge of current pool size
- `db_connection_pool_checked_out` - Gauge of connections currently in use

Metrics are recorded via middleware (request timing) and inline in task processing code.

---

## HeyReach LinkedIn Integration

### Webhook Receiver
Created the `/webhook/heyreach` endpoint for LinkedIn automation events. Handles connection accepted/rejected events, LinkedIn DM replies, and campaign events. Uses HMAC signature verification for security.

When a message is received:
1. Validates webhook signature
2. Finds contact by LinkedIn URL or email, creates if needed
3. Creates reply record with source "heyreach"
4. Queues categorization task for AI processing
5. Updates contact's LinkedIn URL and last response timestamp

### Outbound API Client
Built a comprehensive HeyReach API client for LinkedIn automation:

**Campaign Management**
- `get_campaigns()` - List all LinkedIn campaigns with optional status filter
- `get_campaign()` - Get campaign details by ID
- `add_lead_to_campaign()` - Add lead with LinkedIn URL, name, company, email, custom fields
- `remove_lead_from_campaign()` - Remove lead from campaign
- `pause_lead_in_campaign()` / `resume_lead_in_campaign()` - Control lead status

**Messaging**
- `get_conversation_messages()` - Retrieve LinkedIn conversation history
- `send_message()` - Send message in existing conversation

**Lead Lookup**
- `get_lead_by_linkedin_url()` - Find lead by LinkedIn profile URL

### LinkedIn Data Enrichment (Sales Navigator Replacement)
Extended HeyReach client to provide LinkedIn data enrichment, replacing the need for LinkedIn Sales Navigator:

**Data Classes**
- `LinkedInProfile` - Person profile data (name, headline, company, job title, industry, location, connections)
- `LinkedInCompany` - Company page data (name, industry, size, headquarters, website, description, specialties)

**Enrichment Methods**
- `enrich_profile(linkedin_url)` - Get full profile data from LinkedIn URL
- `enrich_company(linkedin_url)` - Get company page data from LinkedIn company URL
- `find_profile_by_email(email)` - Email to LinkedIn profile lookup
- `search_people(...)` - Search profiles by keywords, name, company, title, location, industry
- `search_companies(...)` - Search companies by keywords, name, industry, size, location

**Validation Integration**
- `get_lead_enrichment_for_validation()` - Combined enrichment for LLM validation
- `to_llm_validation_context()` - Format enrichment data for LLM context

Used by the company validation service to enrich leads with LinkedIn data before AI validation.

---

## Web Crawling for Company Validation

Built a web crawler for extracting company information from websites to enhance LLM validation.

### WebCrawlerClient
- Uses `httpx` for async HTTP requests with 15-second timeout
- Uses `BeautifulSoup` for HTML parsing
- Respects 1MB content length limit
- User-agent identifies as "OutreachBot/1.0"

### Crawling Strategy
1. **Homepage** - Extracts title, meta description, meta keywords, social links, contact info
2. **About Page** - Tries `/about`, `/about-us`, `/company`, `/who-we-are`, `/our-story`
3. **Services Page** - Tries `/services`, `/solutions`, `/products`, `/what-we-do`

### Data Extraction
- **Meta tags**: Title, description, keywords
- **About text**: Main content from about page (up to 3000 chars)
- **Services**: Extracted from headings and lists mentioning services/solutions
- **Social links**: LinkedIn, Twitter, Facebook, Instagram, YouTube
- **Contact info**: Email and phone number patterns

### Integration with Validation
The `validate_company()` method in categorization service now:
1. Crawls company website if domain provided
2. Fetches LinkedIn data via HeyReach if LinkedIn URL or email provided
3. Combines all data sources (Apollo, website, LinkedIn) in LLM prompt
4. Returns validation result with higher confidence due to richer context

Validation flow matches requirements:
```
Lead Source → Website Crawling + LinkedIn Crawling → LLM Analysis → Classification → Campaign Eligibility
```

---

## Prospect-Defined Timing Extraction

Enhanced AI categorization to extract follow-up timing from "Wrong Timing" (4.3) replies.

### LLM Schema Updates
Added `suggested_followup_date` field to categorization response schema:
- Type: ISO date string (YYYY-MM-DD) or null
- Only populated for Wrong Timing (4.3) category
- LLM converts relative terms to dates:
  - "Q1" → March 31
  - "Q2" → June 30
  - "Q3" → September 30
  - "Q4" → December 31
  - "next month" → 1st of next month
  - "in X months" → X months from today

### Categorization Task Updates
When a reply is categorized as WRONG_TIMING:
1. System checks for `suggested_followup_date` in LLM response
2. Parses ISO date and validates it
3. Sets `contact.re_engagement_date` to the extracted date
4. Sets `contact.re_engagement_category` to track the reason
5. Contact will be picked up by re-engagement pipeline on that date

This ensures prospect-defined timing is honored automatically.

---

## Referral Auto-Campaign Enrollment

Implemented automatic enrollment of referrals into outreach campaigns.

### LLM Schema Updates
Added `referral_info` field to categorization response schema:
- Type: Object with `name`, `email`, `company` (all nullable)
- Only populated for Referral (2.1) category
- LLM extracts referral contact details from reply text

### Data Model
Added `ReferralInfo` dataclass:
```python
@dataclass
class ReferralInfo:
    name: str | None
    email: str | None
    company: str | None
```

### Auto-Enrollment Process
When a reply is categorized as REFERRAL with referral info:
1. **Create Contact** - New contact created in database with referral details
2. **Link to Referrer** - `referred_by_contact_id` links to original contact
3. **HubSpot Sync** - Creates contact in HubSpot with referral note
4. **Campaign Addition** - Adds to SmartLead campaign with personalized message:
   ```
   Referred by {referrer_name} from {referrer_company}
   ```
5. **Logging** - Full audit trail of referral processing

This fulfills requirements 5.2.2 and 5.2.3 for automatic referral handling.

---

## Business Metrics Dashboard

Added email engagement metrics endpoint for campaign ROI tracking.

### New Schemas
- `EmailEngagementStats` - Opens, clicks, replies, bounces, unsubscribes with rates
- `CampaignROI` - Per-campaign metrics with conversion rates
- `EmailMetricsDashboard` - Combined dashboard response

### New Endpoint
`GET /api/v1/dashboard/email-metrics`

Returns:
- **Total Engagement** - Aggregate metrics from Prometheus counters
- **Today's Engagement** - Metrics from database for current day
- **Conversion Funnel** - Contacts → Replied → Interested → Meetings booked
- **Top Campaigns** - Per-campaign ROI (placeholder for future implementation)

### Webhook Integration
SmartLead webhook processing now records engagement metrics:
- EMAIL_OPENED events increment `email_opens_total`
- EMAIL_CLICKED events increment `email_clicks_total`
- EMAIL_REPLY events increment `email_replies_total`
- EMAIL_BOUNCED/HARD_BOUNCE/SOFT_BOUNCE events increment `email_bounces_total`
- EMAIL_UNSUBSCRIBED events increment `email_unsubscribes_total`

Non-reply events are tracked in metrics only; full processing only occurs for replies.

---

## Rate Limit Monitoring & Alerting

Enhanced rate limit handling across all integration clients.

### Base Client Updates
- Added `integration_name` parameter to identify the source of requests
- On 429 (Too Many Requests) response:
  1. Increments `rate_limit_hits_total` counter
  2. Reads `Retry-After` header for wait time
  3. Implements exponential backoff if no header
  4. Increments `rate_limit_retries_total` on retry
  5. Sends Sentry alert when retries exhausted

### Integration Client Updates
All clients now pass `integration_name`:
- `ApolloClient` → `integration_name="apollo"`
- `ConnectSafelyClient` → `integration_name="connectsafely"`
- `HubSpotClient` → `integration_name="hubspot"`
- `SmartLeadClient` → `integration_name="smartlead"`
- `HeyReachClient` → `integration_name="heyreach"`

### Alerting
When rate limit retries are exhausted:
```python
sentry_sdk.capture_message(
    f"Rate limit exhausted for {integration_name}",
    level="warning",
)
```

---

## Database Performance Monitoring

Added SQLAlchemy event listeners for query performance tracking.

### Event Listeners
Attached to `engine.sync_engine`:
- `before_cursor_execute` - Records query start time in context var
- `after_cursor_execute` - Calculates duration, records metrics, logs slow queries
- `checkout` - Updates connection pool gauges when connection acquired
- `checkin` - Updates connection pool gauges when connection returned

### Query Type Detection
Automatically classifies queries:
- SELECT → "select"
- INSERT → "insert"
- UPDATE → "update"
- DELETE → "delete"
- Other → "other"

### Slow Query Logging
Queries exceeding 100ms threshold:
1. Increment `db_slow_queries_total` counter
2. Log warning with query type, duration in ms, and statement preview (first 200 chars)

### Connection Pool Monitoring
Real-time tracking of:
- Total pool size
- Connections currently checked out
- Updated on every checkout/checkin event

---

## Log Rotation

Added file-based logging with automatic rotation and compression.

### Configuration Settings
New settings in `app/config.py`:
- `log_file_enabled` - Enable file logging (default: False for containers)
- `log_file_path` - Path to log file (default: `/var/log/outreach/app.log`)
- `log_file_rotation_days` - Rotation interval (default: 1 day)
- `log_file_retention_days` - Days to keep logs (default: 30)
- `log_file_compress` - Compress rotated files (default: True)

### CompressedTimedRotatingFileHandler
Custom handler extending `TimedRotatingFileHandler`:
- Rotates at midnight daily
- Compresses rotated files to `.gz` format using gzip
- Maintains configured number of backup files
- UTF-8 encoding for all log files

### Dual Output
When file logging enabled:
- **stdout** - Stream handler with configured format (JSON or console)
- **file** - Always JSON format for parseability by log aggregation tools

File logging is optional to support both:
- Container deployments (stdout only, aggregated by orchestrator)
- VM deployments (file logging with rotation)

---

## ELK Stack Integration

Added configuration for Elasticsearch, Logstash, Kibana log aggregation.

### docker-compose.elk.yml
Defines ELK stack services:

**Elasticsearch**
- Image: `docker.elastic.co/elasticsearch/elasticsearch:8.11.0`
- Single-node configuration for simplicity
- Security disabled for internal use
- Health check on cluster health endpoint
- Port 9200 exposed

**Kibana**
- Image: `docker.elastic.co/kibana/kibana:8.11.0`
- Connected to Elasticsearch
- Port 5601 exposed for dashboard access
- Health check on status API

**Filebeat**
- Image: `docker.elastic.co/beats/filebeat:8.11.0`
- Mounts application log directory
- Mounts Docker socket for container log collection (optional)
- Uses custom `filebeat.yml` configuration

### filebeat.yml Configuration

**Log Inputs**
- Application logs from `/var/log/outreach/app.log*`
- Celery worker logs from `/var/log/outreach/celery*.log*`
- Optional Docker container logs

**JSON Parsing**
- Keys merged under root
- Automatic error key addition for parse failures
- Service and environment fields added

**Timestamp Processing**
- Parses ISO format timestamps from log entries
- Multiple format patterns supported

**Output Configuration**
- Index pattern: `outreach-logs-{service}-{date}`
- Index lifecycle management enabled
- Daily rollover configured

**Index Template**
- 1 shard, 0 replicas (single-node)
- 5-second refresh interval
- Template applied to `outreach-logs-*` pattern

### Usage
```bash
# Start ELK stack alongside main application
docker-compose -f docker-compose.yml -f docker-compose.elk.yml up -d

# Access Kibana dashboard
open http://localhost:5601
```

---

## Implementation Summary

All requirement gaps have been implemented:

| # | Gap | Status | Implementation |
|---|-----|--------|----------------|
| 1 | Web Crawling | ✅ Complete | `app/integrations/webcrawler/` |
| 2 | LinkedIn Data | ✅ Complete | HeyReach enrichment methods |
| 3 | Business Metrics | ✅ Complete | `/dashboard/email-metrics` endpoint |
| 4 | HeyReach Integration | ✅ Complete | Full webhook + API client |
| 5 | Timing Extraction | ✅ Complete | LLM schema + categorization task |
| 6 | Referral Auto-Add | ✅ Complete | Auto-enrollment to SmartLead |
| 7 | Rate Limit Monitoring | ✅ Complete | Prometheus metrics + Sentry |
| 8 | DB Monitoring | ✅ Complete | SQLAlchemy event listeners |
| 9 | ELK Integration | ✅ Complete | docker-compose.elk.yml + filebeat.yml |
| 10 | Log Rotation | ✅ Complete | CompressedTimedRotatingFileHandler |
| 11 | Apollo Email Validation | ✅ Complete | `validate_email()`, `validate_emails()` methods |
| 12 | SmartLead Mailbox Monitoring | ✅ Complete | `get_warmup_status()`, `get_throttle_status()`, `get_master_inbox()` |
| 13 | HubSpot Notes | ✅ Complete | `app/integrations/hubspot/notes.py` |
| 14 | Channel Switching | ✅ Complete | `app/services/channel_switching/` + Celery task |
| 15 | Campaign Model | ✅ Complete | `app/db/models/campaign.py` + migration |
| 16 | LLM Company Validation | ✅ Complete | `app/services/validation/service.py` + Celery tasks |
| 17 | Category-Specific Notifications | ✅ Complete | `NOTIFICATION_MESSAGES` in constants.py |
| 18 | HubSpot Custom Properties | ✅ Complete | Property management methods in contacts.py |

### Files Created
- `app/integrations/webcrawler/__init__.py`
- `app/integrations/webcrawler/client.py`
- `app/integrations/heyreach/__init__.py`
- `app/integrations/heyreach/client.py`
- `app/api/webhooks/heyreach.py`
- `docker-compose.elk.yml`
- `filebeat.yml`
- `app/integrations/hubspot/notes.py` - HubSpot notes/engagements module
- `app/services/channel_switching/__init__.py` - Channel switching package
- `app/services/channel_switching/service.py` - Channel switching service
- `app/workers/channel_tasks.py` - Channel switching Celery tasks
- `app/db/migrations/versions/002_add_channel_switching_fields.py` - Migration for channel fields
- `tests.md` - Comprehensive test scenarios (192 tests)
- `tests_refined.md` - Human-readable test documentation
- `app/db/models/campaign.py` - Campaign model for LLM company validation
- `app/db/migrations/versions/003_add_campaigns_table.py` - Migration for campaigns table
- `app/services/validation/__init__.py` - Validation service package
- `app/services/validation/service.py` - LLM company validation service
- `app/workers/validation_tasks.py` - Company validation Celery tasks

### Files Modified
- `app/api/v1/dashboard.py` - Added email metrics endpoint
- `app/api/v1/schemas.py` - Added engagement stats schemas
- `app/api/webhooks/router.py` - Added HeyReach router
- `app/api/webhooks/schemas.py` - Added HeyReach payload schema
- `app/config.py` - Added HeyReach and log rotation settings
- `app/core/logging.py` - Added file rotation handler
- `app/core/metrics.py` - Added 13 new Prometheus metrics
- `app/core/constants.py` - Added `NOTIFICATION_MESSAGES` dict and `get_notification_message()` helper
- `app/db/repositories/contact.py` - Added `get_by_linkedin_url()`
- `app/db/session.py` - Added SQLAlchemy event listeners
- `app/db/models/contact.py` - Added channel switching fields + campaign FK relationship
- `app/integrations/base.py` - Added integration name tracking
- `app/integrations/apollo/client.py` - Added integration name + email validation methods
- `app/integrations/connectsafely/client.py` - Added integration name
- `app/integrations/hubspot/client.py` - Added integration name
- `app/integrations/hubspot/__init__.py` - Export HubSpotNotes
- `app/integrations/hubspot/contacts.py` - Added custom property management methods
- `app/integrations/smartlead/client.py` - Added integration name + mailbox management methods
- `app/integrations/webcrawler/client.py` - Added `fetch_homepage_only()` for fast validation
- `app/services/categorization/prompts.py` - Added timing/referral fields
- `app/services/categorization/service.py` - Added web/LinkedIn enrichment
- `app/services/notifications/formatter.py` - Added `category_message` field to NotificationContent
- `app/services/notifications/service.py` - Added category-specific message lookup
- `app/workers/categorization_tasks.py` - Added timing/referral handling
- `app/workers/webhook_tasks.py` - Added HeyReach task + engagement metrics
- `app/workers/celery_app.py` - Added validation tasks routes, autodiscover, and beat schedule
