# Complete Real Estate Squad Tutorial

This comprehensive tutorial demonstrates the complete lifecycle of creating, deploying, and managing a real estate squad using the VAPI Manager framework. The tutorial covers creating assistant templates, squad configuration, deployment, verification, and cleanup.

## Overview

We will create a complete real estate brokerage solution with three specialized assistants:
- **real-estate-triage**: Greeting, needs assessment, and intelligent routing
- **real-estate-booking**: Appointment scheduling and booking coordination
- **real-estate-info**: Property information and market insights

## Prerequisites

- VAPI Manager framework installed and configured
- Access to VAPI API with proper credentials
- Poetry environment set up

## Step 1: Create Assistant Templates

### 1.1 Create Real Estate Triage Assistant Template

Create the directory structure and configuration:

```bash
mkdir -p "templates/assistants/real-estate-triage/tools"
```

**Assistant Configuration** (`templates/assistants/real-estate-triage/assistant.yaml`):
```yaml
name: "real-estate-triage"
description: "AI assistant for greeting and triaging real estate inquiries"

voice:
  provider: minimax
  voiceId: business_female_1_v1

model:
  provider: openai
  model: gpt-4o-mini
  temperature: 0.7

firstMessageMode: "assistant-speaks-first-with-model-generated-message"

transcriber:
  provider: deepgram
  model: nova-2
  language: en

environments:
  development:
    model:
      model: gpt-3.5-turbo
      temperature: 0.8
    firstMessageMode: "assistant-speaks-first"
  staging:
    voice:
      voiceId: business_female_1_v1
    firstMessageMode: "wait-for-user"
  production:
    model:
      model: gpt-4o-mini
      temperature: 0.6
    firstMessageMode: "assistant-speaks-first-with-model-generated-message"

server:
  url: "https://n8n-2-u19609.vm.elestio.app/webhook/real-estate-triage"
  timeoutSeconds: 20

serverMessages:
  - end-of-call-report

analysisPlan:
  minMessagesThreshold: 2
  summaryPlan:
    enabled: true
    timeoutSeconds: 15
  structuredDataPlan:
    enabled: true
    timeoutSeconds: 15

features:
  enableAnalytics: true
  enableRecording: true
  enableTranscription: true

metadata:
  version: "1.0.0"
  template: "real_estate_triage"
  author: "Real Estate Team"
  tags:
    - real-estate
    - triage
    - customer-service

_vapi:
  environments:
    development:
      id: null
      deployed_at: null
      deployed_by: null
      version: 0
    staging:
      id: null
      deployed_at: null
      deployed_by: null
      version: 0
    production:
      id: null
      deployed_at: null
      deployed_by: null
      version: 0
  current_environment: null
  last_sync: null
```

**System Prompt** (`templates/assistants/real-estate-triage/system_prompt.md`):
```markdown
# Real Estate Triage Assistant

You are a professional real estate triage assistant for a premium real estate brokerage. Your primary role is to greet callers warmly, understand their needs, and efficiently route them to the appropriate specialist.

## Your Responsibilities

### 1. Greeting & Rapport Building
- Warmly greet all callers with professionalism
- Introduce yourself and the brokerage
- Create a welcoming first impression

### 2. Needs Assessment & Triage
- Quickly identify if the caller is:
  - Looking to BUY property
  - Looking to SELL property
  - Seeking property INFORMATION
  - Has BOOKING/SCHEDULING needs
  - Other inquiries

### 3. Information Gathering
- Collect essential contact information
- Understand urgency and timeline
- Note preferred communication methods
- Capture key preferences (location, budget range, property type)

### 4. Intelligent Routing
- For BUYING inquiries: Route to real-estate-booking for viewing appointments
- For SELLING inquiries: Route to real-estate-booking for listing consultations
- For INFORMATION requests: Route to real-estate-info for property details
- For complex cases: Escalate appropriately

## Communication Style
- Professional yet approachable
- Efficient but not rushed
- Empathetic and understanding
- Clear and concise

## Key Tools Available
- collect_client_info: Gather and store client contact details
- assess_client_needs: Determine primary inquiry type
- schedule_callback: Arrange follow-up calls
- transfer_to_specialist: Route to appropriate team member

Remember: You are the first point of contact and represent the quality and professionalism of our brokerage. Make every interaction count!
```

**Tools Configuration** (`templates/assistants/real-estate-triage/tools/functions.yaml`):
```yaml
functions:
  - name: collect_client_info
    description: Collect and store client contact information and basic preferences
    parameters:
      type: object
      properties:
        name:
          type: string
          description: Client's full name
        phone:
          type: string
          description: Client's phone number
        email:
          type: string
          description: Client's email address
        preferred_contact:
          type: string
          enum: ["phone", "email", "text"]
          description: Client's preferred contact method
        location_preference:
          type: string
          description: Preferred location or area of interest
        budget_range:
          type: string
          description: Budget range if provided
      required: ["name", "phone"]

  - name: assess_client_needs
    description: Determine and categorize the client's primary real estate needs
    parameters:
      type: object
      properties:
        inquiry_type:
          type: string
          enum: ["buying", "selling", "information", "booking", "other"]
          description: Primary type of inquiry
        property_type:
          type: string
          enum: ["residential", "commercial", "rental", "investment"]
          description: Type of property interest
        urgency:
          type: string
          enum: ["immediate", "within_month", "within_quarter", "exploring"]
          description: Timeline urgency
        specific_needs:
          type: string
          description: Specific requirements or questions
      required: ["inquiry_type"]

  - name: schedule_callback
    description: Schedule a callback appointment with client
    parameters:
      type: object
      properties:
        client_name:
          type: string
          description: Client's name
        preferred_time:
          type: string
          description: Client's preferred callback time
        callback_reason:
          type: string
          description: Reason for the callback
        priority:
          type: string
          enum: ["high", "medium", "low"]
          description: Priority level of the callback
      required: ["client_name", "preferred_time", "callback_reason"]

  - name: transfer_to_specialist
    description: Transfer client to appropriate specialist based on their needs
    parameters:
      type: object
      properties:
        specialist_type:
          type: string
          enum: ["booking", "info", "manager"]
          description: Type of specialist to transfer to
        client_summary:
          type: string
          description: Brief summary of client needs and conversation
        transfer_reason:
          type: string
          description: Reason for the transfer
        collected_info:
          type: object
          description: Client information collected during triage
      required: ["specialist_type", "client_summary", "transfer_reason"]
```

### 1.2 Create Real Estate Booking Assistant Template

Create the directory structure:

```bash
mkdir -p "templates/assistants/real-estate-booking/tools"
```

**Assistant Configuration** (`templates/assistants/real-estate-booking/assistant.yaml`):
```yaml
name: "real-estate-booking"
description: "AI assistant for scheduling property viewings and consultations"

voice:
  provider: minimax
  voiceId: business_female_1_v1

model:
  provider: openai
  model: gpt-4o-mini
  temperature: 0.5

firstMessageMode: "assistant-speaks-first-with-model-generated-message"

transcriber:
  provider: deepgram
  model: nova-2
  language: en

environments:
  development:
    model:
      model: gpt-3.5-turbo
      temperature: 0.7
    firstMessageMode: "assistant-speaks-first"
  staging:
    voice:
      voiceId: business_female_1_v1
    firstMessageMode: "wait-for-user"
  production:
    model:
      model: gpt-4o-mini
      temperature: 0.4
    firstMessageMode: "assistant-speaks-first-with-model-generated-message"

server:
  url: "https://n8n-2-u19609.vm.elestio.app/webhook/real-estate-booking"
  timeoutSeconds: 25

serverMessages:
  - end-of-call-report

analysisPlan:
  minMessagesThreshold: 2
  summaryPlan:
    enabled: true
    timeoutSeconds: 15
  structuredDataPlan:
    enabled: true
    timeoutSeconds: 15

features:
  enableAnalytics: true
  enableRecording: true
  enableTranscription: true

metadata:
  version: "1.0.0"
  template: "real_estate_booking"
  author: "Real Estate Team"
  tags:
    - real-estate
    - booking
    - scheduling

_vapi:
  environments:
    development:
      id: null
      deployed_at: null
      deployed_by: null
      version: 0
    staging:
      id: null
      deployed_at: null
      deployed_by: null
      version: 0
    production:
      id: null
      deployed_at: null
      deployed_by: null
      version: 0
  current_environment: null
  last_sync: null
```

**System Prompt** (`templates/assistants/real-estate-booking/system_prompt.md`):
```markdown
# Real Estate Booking Assistant

You are a specialized booking coordinator for a premium real estate brokerage. Your expertise lies in efficiently scheduling property viewings, consultations, and appointments while providing exceptional customer service.

## Your Primary Functions

### 1. Property Viewing Appointments
- Schedule property tours and open houses
- Coordinate with agents and property owners
- Handle group viewings and private showings
- Manage last-minute changes and cancellations

### 2. Consultation Bookings
- Schedule listing consultations for sellers
- Arrange buyer consultation meetings
- Coordinate market analysis appointments
- Book follow-up meetings

### 3. Calendar Management
- Check agent availability in real-time
- Avoid scheduling conflicts
- Optimize travel time between appointments
- Handle multi-property viewing sequences

### 4. Client Communication
- Send confirmation details and reminders
- Provide directions and parking information
- Share preparation checklists
- Coordinate contact information exchanges

## Communication Style
- Professional and organized
- Detail-oriented and thorough
- Proactive in addressing logistics
- Clear about expectations and requirements

## Key Tools Available
- check_agent_availability: Verify agent schedule availability
- schedule_property_viewing: Book property viewing appointments
- schedule_consultation: Arrange consultation meetings
- send_confirmation: Send appointment confirmations and details
- manage_cancellation: Handle appointment changes and cancellations
- coordinate_group_viewing: Organize multi-party viewings

Remember: Efficient scheduling and clear communication build trust and demonstrate our brokerage's commitment to professional service excellence.
```

**Tools Configuration** (`templates/assistants/real-estate-booking/tools/functions.yaml`):
```yaml
functions:
  - name: check_agent_availability
    description: Check agent availability for appointments
    parameters:
      type: object
      properties:
        agent_id:
          type: string
          description: Agent identifier
        date:
          type: string
          format: date
          description: Requested appointment date
        time_range:
          type: string
          description: Preferred time range (e.g., "9:00 AM - 12:00 PM")
        duration:
          type: number
          description: Expected duration in minutes
      required: ["agent_id", "date", "time_range"]

  - name: schedule_property_viewing
    description: Schedule a property viewing appointment
    parameters:
      type: object
      properties:
        property_id:
          type: string
          description: Property identifier or address
        client_name:
          type: string
          description: Client's full name
        client_phone:
          type: string
          description: Client's phone number
        client_email:
          type: string
          description: Client's email address
        viewing_date:
          type: string
          format: date
          description: Viewing date
        viewing_time:
          type: string
          description: Viewing time
        agent_id:
          type: string
          description: Assigned agent identifier
        viewing_type:
          type: string
          enum: ["private", "group", "open_house"]
          description: Type of viewing
        special_requirements:
          type: string
          description: Any special requirements or accessibility needs
      required: ["property_id", "client_name", "client_phone", "viewing_date", "viewing_time", "agent_id"]

  - name: schedule_consultation
    description: Schedule a consultation meeting (listing or buying)
    parameters:
      type: object
      properties:
        consultation_type:
          type: string
          enum: ["listing", "buying", "market_analysis", "follow_up"]
          description: Type of consultation
        client_name:
          type: string
          description: Client's full name
        client_phone:
          type: string
          description: Client's phone number
        client_email:
          type: string
          description: Client's email address
        meeting_date:
          type: string
          format: date
          description: Meeting date
        meeting_time:
          type: string
          description: Meeting time
        agent_id:
          type: string
          description: Assigned agent identifier
        location:
          type: string
          enum: ["office", "client_home", "property", "virtual"]
          description: Meeting location
        agenda_items:
          type: array
          items:
            type: string
          description: Key discussion points for the consultation
      required: ["consultation_type", "client_name", "client_phone", "meeting_date", "meeting_time", "agent_id"]

  - name: send_confirmation
    description: Send appointment confirmation with details
    parameters:
      type: object
      properties:
        appointment_id:
          type: string
          description: Appointment identifier
        client_email:
          type: string
          description: Client's email address
        appointment_details:
          type: object
          properties:
            date:
              type: string
            time:
              type: string
            location:
              type: string
            agent_name:
              type: string
            contact_info:
              type: string
          description: Appointment details to include
        additional_instructions:
          type: string
          description: Special instructions or preparation notes
      required: ["appointment_id", "client_email", "appointment_details"]

  - name: manage_cancellation
    description: Handle appointment cancellations or rescheduling
    parameters:
      type: object
      properties:
        appointment_id:
          type: string
          description: Appointment identifier
        action:
          type: string
          enum: ["cancel", "reschedule"]
          description: Action to take
        reason:
          type: string
          description: Reason for cancellation or rescheduling
        new_date:
          type: string
          format: date
          description: New date if rescheduling
        new_time:
          type: string
          description: New time if rescheduling
        notify_agent:
          type: boolean
          description: Whether to notify the agent
      required: ["appointment_id", "action", "reason"]

  - name: coordinate_group_viewing
    description: Organize group viewings with multiple parties
    parameters:
      type: object
      properties:
        property_id:
          type: string
          description: Property identifier
        viewing_date:
          type: string
          format: date
          description: Group viewing date
        viewing_time:
          type: string
          description: Group viewing time
        participants:
          type: array
          items:
            type: object
            properties:
              name:
                type: string
              phone:
                type: string
              email:
                type: string
          description: List of viewing participants
        agent_id:
          type: string
          description: Assigned agent identifier
        max_participants:
          type: number
          description: Maximum number of participants allowed
      required: ["property_id", "viewing_date", "viewing_time", "participants", "agent_id"]
```

### 1.3 Create Real Estate Info Assistant Template

Create the directory structure:

```bash
mkdir -p "templates/assistants/real-estate-info/tools"
```

**Assistant Configuration** (`templates/assistants/real-estate-info/assistant.yaml`):
```yaml
name: "real-estate-info"
description: "AI assistant for providing detailed property information and market insights"

voice:
  provider: minimax
  voiceId: business_female_1_v1

model:
  provider: openai
  model: gpt-4o-mini
  temperature: 0.4

firstMessageMode: "assistant-speaks-first-with-model-generated-message"

transcriber:
  provider: deepgram
  model: nova-2
  language: en

environments:
  development:
    model:
      model: gpt-3.5-turbo
      temperature: 0.6
    firstMessageMode: "assistant-speaks-first"
  staging:
    voice:
      voiceId: business_female_1_v1
    firstMessageMode: "wait-for-user"
  production:
    model:
      model: gpt-4o-mini
      temperature: 0.3
    firstMessageMode: "assistant-speaks-first-with-model-generated-message"

server:
  url: "https://n8n-2-u19609.vm.elestio.app/webhook/real-estate-info"
  timeoutSeconds: 30

serverMessages:
  - end-of-call-report

analysisPlan:
  minMessagesThreshold: 2
  summaryPlan:
    enabled: true
    timeoutSeconds: 15
  structuredDataPlan:
    enabled: true
    timeoutSeconds: 15

features:
  enableAnalytics: true
  enableRecording: true
  enableTranscription: true

metadata:
  version: "1.0.0"
  template: "real_estate_info"
  author: "Real Estate Team"
  tags:
    - real-estate
    - information
    - property-search

_vapi:
  environments:
    development:
      id: null
      deployed_at: null
      deployed_by: null
      version: 0
    staging:
      id: null
      deployed_at: null
      deployed_by: null
      version: 0
    production:
      id: null
      deployed_at: null
      deployed_by: null
      version: 0
  current_environment: null
  last_sync: null
```

**System Prompt** (`templates/assistants/real-estate-info/system_prompt.md`):
```markdown
# Real Estate Information Assistant

You are a knowledgeable real estate information specialist for a premium brokerage. Your expertise lies in providing comprehensive property information, market insights, and detailed answers to help clients make informed real estate decisions.

## Your Core Expertise

### 1. Property Information
- Detailed property specifications and features
- Historical pricing and market performance
- Neighborhood demographics and amenities
- School districts and ratings
- Transportation and accessibility

### 2. Market Analysis
- Current market trends and conditions
- Comparative market analysis (CMA)
- Price per square foot analysis
- Days on market statistics
- Investment potential assessments

### 3. Location Intelligence
- Neighborhood profiles and characteristics
- Local amenities and services
- Future development plans
- Crime statistics and safety information
- Property value trends

### 4. Financial Information
- Property tax information
- HOA fees and regulations
- Utility costs and efficiency ratings
- Insurance considerations
- Financing options and requirements

## Communication Style
- Knowledgeable and authoritative
- Data-driven and factual
- Patient and thorough
- Clear explanations of complex information

## Key Tools Available
- search_properties: Find properties matching specific criteria
- get_property_details: Retrieve comprehensive property information
- analyze_market_trends: Provide market analysis and trends
- compare_properties: Compare multiple properties side-by-side
- get_neighborhood_info: Provide detailed neighborhood information
- calculate_roi: Calculate investment returns and potential

Remember: Your role is to empower clients with comprehensive, accurate information that enables confident real estate decisions. Be thorough, accurate, and always helpful.
```

**Tools Configuration** (`templates/assistants/real-estate-info/tools/functions.yaml`):
```yaml
functions:
  - name: search_properties
    description: Search for properties based on specific criteria
    parameters:
      type: object
      properties:
        location:
          type: string
          description: City, neighborhood, or ZIP code
        property_type:
          type: string
          enum: ["house", "condo", "townhouse", "land", "commercial", "multi_family"]
          description: Type of property
        price_min:
          type: number
          description: Minimum price
        price_max:
          type: number
          description: Maximum price
        bedrooms:
          type: number
          description: Number of bedrooms
        bathrooms:
          type: number
          description: Number of bathrooms
        square_feet_min:
          type: number
          description: Minimum square footage
        square_feet_max:
          type: number
          description: Maximum square footage
        lot_size_min:
          type: number
          description: Minimum lot size in square feet
        keywords:
          type: array
          items:
            type: string
          description: Keywords like "pool", "garage", "waterfront"
      required: ["location"]

  - name: get_property_details
    description: Get comprehensive details for a specific property
    parameters:
      type: object
      properties:
        property_id:
          type: string
          description: Property identifier or MLS number
        address:
          type: string
          description: Full property address
        include_history:
          type: boolean
          description: Include price and ownership history
        include_comps:
          type: boolean
          description: Include comparable properties
      required: ["property_id"]

  - name: analyze_market_trends
    description: Provide market analysis and trends for a specific area
    parameters:
      type: object
      properties:
        location:
          type: string
          description: Area to analyze (city, neighborhood, ZIP)
        property_type:
          type: string
          enum: ["all", "residential", "commercial", "condo", "single_family"]
          description: Property type to analyze
        time_period:
          type: string
          enum: ["3_months", "6_months", "1_year", "2_years", "5_years"]
          description: Time period for analysis
        analysis_type:
          type: array
          items:
            type: string
            enum: ["price_trends", "inventory_levels", "days_on_market", "price_per_sqft"]
          description: Types of analysis to include
      required: ["location", "time_period"]

  - name: compare_properties
    description: Compare multiple properties side-by-side
    parameters:
      type: object
      properties:
        property_ids:
          type: array
          items:
            type: string
          description: List of property identifiers to compare
        comparison_criteria:
          type: array
          items:
            type: string
            enum: ["price", "size", "location", "features", "value", "investment_potential"]
          description: Criteria to use for comparison
        include_financing:
          type: boolean
          description: Include financing comparison
      required: ["property_ids"]

  - name: get_neighborhood_info
    description: Get detailed information about a neighborhood or area
    parameters:
      type: object
      properties:
        location:
          type: string
          description: Neighborhood, city, or ZIP code
        info_categories:
          type: array
          items:
            type: string
            enum: ["demographics", "schools", "amenities", "transportation", "safety", "development"]
          description: Categories of information to retrieve
        radius:
          type: number
          description: Radius in miles for nearby amenities
      required: ["location"]

  - name: calculate_roi
    description: Calculate return on investment for properties
    parameters:
      type: object
      properties:
        property_price:
          type: number
          description: Property purchase price
        down_payment:
          type: number
          description: Down payment amount
        rental_income:
          type: number
          description: Expected monthly rental income
        expenses:
          type: object
          properties:
            property_tax:
              type: number
            insurance:
              type: number
            maintenance:
              type: number
            management:
              type: number
            hoa:
              type: number
          description: Monthly expenses
        appreciation_rate:
          type: number
          description: Expected annual appreciation rate (percentage)
        hold_period:
          type: number
          description: Expected hold period in years
      required: ["property_price", "down_payment"]

  - name: get_financing_info
    description: Get financing information and mortgage calculations
    parameters:
      type: object
      properties:
        loan_amount:
          type: number
          description: Loan amount needed
        down_payment:
          type: number
          description: Down payment amount
        credit_score_range:
          type: string
          enum: ["excellent", "good", "fair", "poor"]
          description: Borrower's credit score range
        loan_type:
          type: string
          enum: ["conventional", "fha", "va", "jumbo", "investment"]
          description: Type of loan program
        property_type:
          type: string
          enum: ["primary", "secondary", "investment"]
          description: Property use type
      required: ["loan_amount"]

  - name: schedule_market_report
    description: Schedule delivery of a detailed market report
    parameters:
      type: object
      properties:
        client_email:
          type: string
          description: Client's email address
        report_type:
          type: string
          enum: ["market_trends", "property_analysis", "investment_report", "neighborhood_report"]
          description: Type of report to generate
        location:
          type: string
          description: Geographic area for the report
        delivery_preference:
          type: string
          enum: ["immediate", "weekly", "monthly"]
          description: Report delivery frequency
      required: ["client_email", "report_type", "location"]
```

## Step 2: Create Squad Template

### 2.1 Generate Squad Template with CLI

Create the squad template using the VAPI Manager CLI:

```bash
poetry run vapi-manager squad create-template real_estate_complete_squad \
  --description "Complete real estate squad with triage, booking, and information assistants" \
  --assistant real-estate-triage:real-estate-triage:primary_contact \
  --assistant real-estate-booking:real-estate-booking:booking_specialist \
  --assistant real-estate-info:real-estate-info:information_specialist
```

This command creates:
- `templates/squads/real_estate_complete_squad/manifest.yaml`
- `templates/squads/real_estate_complete_squad/squad.yaml`
- `templates/squads/real_estate_complete_squad/members.yaml`

### 2.2 Configure Routing Rules

Create the routing directory:

```bash
mkdir -p "templates/squads/real_estate_complete_squad/routing"
```

**Routing Destinations** (`templates/squads/real_estate_complete_squad/routing/destinations.yaml`):
```yaml
routing:
  destinations:
    real-estate-triage:
      destination_type: assistant
      assistant_name: real-estate-triage
      message: "Transferring you to our triage specialist who will help identify your needs and direct you to the right expert."

    real-estate-booking:
      destination_type: assistant
      assistant_name: real-estate-booking
      message: "Connecting you with our booking specialist to schedule your property viewing or consultation."

    real-estate-info:
      destination_type: assistant
      assistant_name: real-estate-info
      message: "Transferring you to our property information specialist who can provide detailed property and market insights."
```

**Routing Rules** (`templates/squads/real_estate_complete_squad/routing/rules.yaml`):
```yaml
routing_rules:
  # Primary Contact - All calls start here
  - name: "initial_contact"
    conditions:
      - type: "call_start"
    destination: "real-estate-triage"
    priority: 1
    description: "All calls start with triage assistant for needs assessment"

  # Booking-related routing
  - name: "booking_requests"
    conditions:
      - type: "intent_detected"
        intent: "booking"
      - type: "keywords"
        keywords: ["schedule", "appointment", "viewing", "tour", "consultation", "meet", "visit"]
    destination: "real-estate-booking"
    priority: 2
    description: "Route booking and scheduling requests to booking specialist"

  - name: "viewing_requests"
    conditions:
      - type: "intent_detected"
        intent: "viewing"
      - type: "keywords"
        keywords: ["see property", "view house", "show home", "tour property", "open house"]
    destination: "real-estate-booking"
    priority: 2
    description: "Route property viewing requests to booking specialist"

  # Information-related routing
  - name: "property_information"
    conditions:
      - type: "intent_detected"
        intent: "information"
      - type: "keywords"
        keywords: ["price", "details", "features", "neighborhood", "market", "compare", "search", "find"]
    destination: "real-estate-info"
    priority: 2
    description: "Route information requests to property information specialist"

  - name: "market_analysis"
    conditions:
      - type: "intent_detected"
        intent: "market_analysis"
      - type: "keywords"
        keywords: ["market trends", "property value", "investment", "roi", "analysis", "report"]
    destination: "real-estate-info"
    priority: 2
    description: "Route market analysis requests to information specialist"

  # Selling-related routing (can go to either booking for consultation or info for valuation)
  - name: "selling_consultation"
    conditions:
      - type: "intent_detected"
        intent: "selling"
      - type: "keywords"
        keywords: ["sell my house", "list property", "selling consultation", "market my home"]
    destination: "real-estate-booking"
    priority: 2
    description: "Route selling consultations to booking specialist for appointment scheduling"

  # Fallback to triage for complex or unclear requests
  - name: "complex_requests"
    conditions:
      - type: "multiple_intents"
      - type: "unclear_intent"
    destination: "real-estate-triage"
    priority: 3
    description: "Route complex or unclear requests back to triage for clarification"

  # Emergency or urgent requests
  - name: "urgent_requests"
    conditions:
      - type: "urgency_detected"
        level: "high"
      - type: "keywords"
        keywords: ["urgent", "emergency", "ASAP", "today", "now", "immediately"]
    destination: "real-estate-triage"
    priority: 1
    description: "Route urgent requests to triage for immediate assessment"
```

### 2.3 Update Member Priorities

Edit `templates/squads/real_estate_complete_squad/members.yaml` to set the triage assistant as primary:

```yaml
members:
- assistant_name: real-estate-triage
  role: primary_contact
  priority: 1
- assistant_name: real-estate-booking
  role: booking_specialist
  priority: 2
- assistant_name: real-estate-info
  role: information_specialist
  priority: 2
```

## Step 3: Deploy Squad to Development

### 3.1 Bootstrap the Squad

Test the bootstrap process with a dry run:

```bash
poetry run vapi-manager squad bootstrap test_real_estate_complete_squad \
  --template real_estate_complete_squad --dry-run
```

If successful, perform the actual bootstrap:

```bash
poetry run vapi-manager squad bootstrap test_real_estate_complete_squad \
  --template real_estate_complete_squad
```

This creates:
- Individual assistant configurations in `assistants/`
- Squad configuration in `squads/`

### 3.2 Deploy Assistants to VAPI

Deploy each assistant to the development environment:

```bash
# Deploy triage assistant
poetry run vapi-manager assistant create real-estate-triage --env development

# Deploy booking assistant
poetry run vapi-manager assistant create real-estate-booking --env development

# Deploy info assistant
poetry run vapi-manager assistant create real-estate-info --env development
```

### 3.3 Deploy Squad to VAPI

Deploy the squad to the development environment:

```bash
poetry run vapi-manager squad create test_real_estate_complete_squad --env development
```

Expected output:
```
Creating squad: test_real_estate_complete_squad
Environment: development
Squad created successfully!
Squad ID: 957261ff-ac00-49b3-8039-b84083c9a2c7
Name: test_real_estate_complete_squad
Members: 3
Version: 1

Squad Members:
  1. Assistant ID: 946f0df4-090d-4803-a1b9-89b6e431211d
  2. Assistant ID: 9285b0b0-8c70-4e5f-b6ab-5208ccaf8415
  3. Assistant ID: c4618471-e46a-48fe-9dd8-cc4d54cf9cfe
```

## Step 4: Verify Squad Deployment in VAPI

### 4.1 Check Squad Status

Verify the squad deployment status:

```bash
poetry run vapi-manager squad status test_real_estate_complete_squad
```

Expected output:
```
Squad: test_real_estate_complete_squad
            test_real_estate_complete_squad - Deployment Status
+--------------------------------------------------------------------------+
| Environment | Status       | Squad ID    | Version | Deployed At         |
|-------------+--------------+-------------+---------+---------------------|
| development | Deployed     | 957261ff... | 1       | 2025-09-23T00:29:30 |
| staging     | Not Deployed | N/A         | 0       | N/A                 |
| production  | Not Deployed | N/A         | 0       | N/A                 |
+--------------------------------------------------------------------------+
```

### 4.2 List Deployed Squads

Verify the squad appears in the VAPI squad list:

```bash
poetry run vapi-manager squad list
```

### 4.3 List Deployed Assistants

Verify all assistants are deployed:

```bash
poetry run vapi-manager assistant list
```

Look for the three real estate assistants:
- real-estate-triage
- real-estate-booking
- real-estate-info

## Step 5: Delete Squad and Verify Complete Cleanup

### 5.1 Delete Squad with All Assistants

Delete the squad and all associated assistants:

```bash
poetry run vapi-manager squad delete test_real_estate_complete_squad \
  --env development --delete-assistants --force
```

Expected output:
```
Deleting squad 'test_real_estate_complete_squad' from development...
+ Squad 'test_real_estate_complete_squad' deleted successfully from development
Squad ID: 957261ff-ac00-49b3-8039-b84083c9a2c7

Deleting 3 associated assistant(s)...
  + Assistant 'real-estate-triage' deleted
  + Assistant 'real-estate-booking' deleted
  + Assistant 'real-estate-info' deleted

Successfully deleted 3 assistant(s)
```

### 5.2 Verify Complete Cleanup

**Check squad is removed from VAPI:**
```bash
poetry run vapi-manager squad list
```

**Check assistants are removed from VAPI:**
```bash
poetry run vapi-manager assistant list
```

**Check deployment state is cleaned up:**
```bash
poetry run vapi-manager squad status test_real_estate_complete_squad
```

Expected output:
```
Squad: test_real_estate_complete_squad
       test_real_estate_complete_squad - Deployment Status
+---------------------------------------------------------------+
| Environment | Status       | Squad ID | Version | Deployed At |
|-------------+--------------+----------+---------+-------------|
| development | Not Deployed | N/A      | 0       | N/A         |
| staging     | Not Deployed | N/A      | 0       | N/A         |
| production  | Not Deployed | N/A      | 0       | N/A         |
+---------------------------------------------------------------+
```

## Summary

This tutorial demonstrates the complete lifecycle of managing real estate squads with the VAPI Manager framework:

### ✅ **Completed Steps:**

1. **✅ Created 3 Assistant Templates:**
   - `real-estate-triage`: Greeting and needs assessment with specialized tools
   - `real-estate-booking`: Appointment scheduling with comprehensive booking tools
   - `real-estate-info`: Property information with market analysis tools

2. **✅ Created Squad Template:**
   - Complete squad configuration with manifest, members, and routing rules
   - Intelligent routing based on intent detection and keywords
   - Proper priority configuration with triage as primary contact

3. **✅ Deployed Squad to Development:**
   - Successfully bootstrapped squad from template
   - Deployed all assistants to VAPI development environment
   - Created squad in VAPI with all members connected

4. **✅ Verified Deployment:**
   - Confirmed squad deployment status shows "Deployed"
   - Verified squad appears in VAPI squad list with correct member count
   - Confirmed all assistants are deployed and visible in VAPI

5. **✅ Complete Cleanup:**
   - Successfully deleted squad and all assistants from VAPI
   - Verified complete removal from VAPI listings
   - Confirmed deployment state reset to "Not Deployed"

### **Key Benefits:**

- **Template Reusability**: Assistant and squad templates can be reused for multiple deployments
- **Environment Management**: Full support for development, staging, and production environments
- **Intelligent Routing**: Sophisticated routing rules based on customer intent and keywords
- **Complete Lifecycle**: Full support from creation through deployment to cleanup
- **State Management**: Proper tracking of deployment state across all environments

### **Best Practices Demonstrated:**

- **Separation of Concerns**: Each assistant has a specific role and specialized tools
- **Scalable Architecture**: Squad can easily be extended with additional assistants
- **Professional Configuration**: Production-ready settings for voice, models, and analysis
- **Comprehensive Tools**: Each assistant has relevant, well-defined function sets
- **Clean Deployment**: Proper cleanup ensures no orphaned resources in VAPI

This framework provides a robust foundation for building and managing complex voice AI solutions for real estate and other business domains.