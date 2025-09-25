### 1. Proposed Squad Architecture

I recommend a squad named **`real_estate_receptionist_squad`** composed of three specialized assistants. This division of labor ensures each assistant can be fine-tuned for its specific task, leading to higher accuracy and a better caller experience.

*   **`lead_qualifier_assistant` (The Front Desk):**
    *   **Role:** This is the first point of contact. Its primary job is to greet the caller, understand their intent (buying, selling, renting, general inquiry), and capture basic lead information. It then routes the call to the appropriate specialist assistant or human agent.
    *   **Priority:** 1 (Handles all incoming calls).

*   **`property_info_assistant` (The Listing Expert):**
    *   **Role:** This assistant is a read-only expert on property listings. It answers specific questions about properties, such as price, square footage, number of bedrooms/bathrooms, availability, and open house schedules. It uses tools to query your property database (e.g., an MLS feed).
    *   **Priority:** 2 (Receives calls from the lead qualifier).

*   **`scheduling_assistant` (The Appointment Setter):**
    *   **Role:** This assistant handles the complex task of scheduling property viewings. It coordinates between the property's availability, the agent's calendar, and the client's preferred times.
    *   **Priority:** 2 (Receives calls from the lead qualifier or property info assistant).

### 2. Required Tools

To power these assistants, you will need a set of shared tools that connect to your brokerage's backend systems (CRM, MLS, Calendars). Following your architecture, these would be created in `shared/tools/` using your new `vapi-manager tool create` command.

#### For the `lead_qualifier_assistant`:
*   **`lookupClient`**
    *   **Description:** Searches the CRM for an existing client by phone number or email.
    *   **Parameters:** `phoneNumber`, `email`
*   **`createLead`**
    *   **Description:** Creates a new lead in the CRM.
    *   **Parameters:** `firstName`, `lastName`, `phoneNumber`, `email`, `leadType` (e.g., 'buyer', 'seller', 'renter'), `notes`

#### For the `property_info_assistant`:
*   **`searchProperties`**
    *   **Description:** Searches for available properties based on criteria.
    *   **Parameters:** `city`, `zipCode`, `minPrice`, `maxPrice`, `bedrooms`, `bathrooms`
*   **`getPropertyDetails`**
    *   **Description:** Retrieves detailed information for a specific property.
    *   **Parameters:** `propertyId` or `address`

#### For the `scheduling_assistant`:
*   **`checkAgentAvailability`**
    *   **Description:** Checks an agent's calendar for open slots for property viewings.
    *   **Parameters:** `agentName`, `preferredDate`
*   **`bookShowing`**
    *   **Description:** Books a property viewing on the agent's and property's calendars.
    *   **Parameters:** `propertyId`, `agentName`, `clientName`, `clientPhone`, `dateTimeISO`

### 3. Routing Logic and Call Flow

The intelligence of the squad lies in its routing rules. The `lead_qualifier_assistant` acts as the central router, ensuring the caller gets to the right place quickly.

#### A. The Call Flow:

1.  **Initial Contact:** The `lead_qualifier_assistant` answers the call.
2.  **Intent Detection:** It asks questions to determine the caller's intent.
    *   "Are you calling about a specific property, or would you like to start a new search?"
    *   "Are you looking to buy, sell, or rent a property?"
3.  **Routing Decision:**
    *   If the caller wants to know about a specific property -> **Transfer to `property_info_assistant`**.
    *   If the caller wants to book a viewing -> **Transfer to `scheduling_assistant`**.
    *   If the caller is a new lead with general questions -> The `lead_qualifier_assistant` creates a lead using the `createLead` tool and then can either transfer to a human agent on call or to the `property_info_assistant` to start a search.
    *   If the caller asks for a specific agent -> Transfer to their direct line or a messaging tool if they are unavailable.
    *   If the caller has a complaint or asks for a manager -> **Transfer to the Office Manager's number**.

#### B. Example `members.yaml` Configuration

This file defines the members and their primary transfer destinations.

**File:** `squads/real_estate_receptionist_squad/members.yaml`
```yaml
members:
  - assistant_name: "lead_qualifier_assistant"
    role: "primary_lead_qualifier"
    priority: 1
    destinations:
      - type: assistant
        assistant_name: "property_info_assistant"
        message: "Great, let me connect you with our property specialist who can pull up the details for you."
        conditions:
          - intent: "property_inquiry"
      - type: assistant
        assistant_name: "scheduling_assistant"
        message: "Of course, I'll transfer you to our scheduling coordinator to get that viewing booked."
        conditions:
          - intent: "schedule_showing"
      - type: number
        number: "${MORTGAGE_SPECIALIST_PHONE}"
        message: "For financing questions, let me connect you with our mortgage partner."
        conditions:
          - keywords: ["mortgage", "loan", "financing", "pre-approval"]

  - assistant_name: "property_info_assistant"
    role: "property_information"
    priority: 2
    destinations:
      - type: assistant
        assistant_name: "scheduling_assistant"
        message: "Now that you have the details, I can connect you to our scheduling coordinator to book a viewing."
        conditions:
          - intent: "schedule_showing_after_info"

  - assistant_name: "scheduling_assistant"
    role: "appointment_scheduler"
    priority: 2
    # This assistant typically ends the call after successful booking or offers to transfer back.
```

#### C. Example `routing/rules.yaml` Configuration

This file defines the high-level, intelligent routing logic for the entire squad.

**File:** `squads/real_estate_receptionist_squad/routing/rules.yaml`
```yaml
# Priority-based routing rules
priority_rules:
  - name: "hot_lead_to_human"
    priority: 1
    description: "Route high-intent sellers or buyers directly to an available agent."
    triggers:
      - type: keyword
        keywords: ["sell my house now", "make an offer", "urgent buyer"]
    action:
      destination: "round_robin_agent_line" # This would be an external number
      immediate_transfer: true

  - name: "escalation_to_manager"
    priority: 2
    description: "Route complaints or frustrated callers to the office manager."
    triggers:
      - type: sentiment
        threshold: -0.7
      - type: keyword
        keywords: ["manager", "complaint", "supervisor", "unhappy"]
    action:
      destination: "office_manager_phone"

# Intent-based routing rules
intent_rules:
  - name: "property_inquiry_routing"
    description: "Route property questions to the property info specialist."
    triggers:
      - type: intent
        intents: ["property_details", "ask_about_listing", "is_it_available"]
    action:
      destination: "property_info_assistant"

  - name: "scheduling_routing"
    description: "Route viewing requests to the scheduling assistant."
    triggers:
      - type: intent
        intents: ["schedule_showing", "book_appointment", "see_the_house"]
    action:
      destination: "scheduling_assistant"
```

### 4. Implementation Plan using Your Bootstrap Command

You can use the `squad bootstrap` command you just implemented to create this entire system in one step.

1.  **Create the Assistant Templates:**
    *   Create three new assistant templates in `templates/`: `real_estate_lead_qualifier`, `real_estate_property_info`, `real_estate_scheduler`. Each would have its own `assistant.yaml` and the relevant tools defined in its `tools/functions.yaml`.

2.  **Create the Squad "Meta-Template":**
    *   Create a new squad template directory: `templates/squads/real_estate_squad/`.
    *   Inside, create the `manifest.yaml`, `squad.yaml`, `members.yaml`, and `routing/rules.yaml` files as described above.

    **File:** `templates/squads/real_estate_squad/manifest.yaml`
    ```yaml
    description: "A complete real estate receptionist squad for lead qualification, property inquiries, and scheduling."

    # Tools to create before assistants (optional, but good practice)
    tools:
      - name: "crm-lookup"
        template: "data_lookup"
        variables:
          url: "https://api.yourcrm.com/clients"
      - name: "property-search"
        template: "data_lookup"
        variables:
          url: "https://api.mls.com/properties"
      - name: "calendar-booking"
        template: "appointment_booking"
        variables:
          url: "https://api.yourcalendar.com/book"

    # Assistants that make up this squad
    assistants:
      - name: "lead_qualifier_assistant"
        template: "real_estate_lead_qualifier"
        role: "Handles initial lead qualification and routing."
      - name: "property_info_assistant"
        template: "real_estate_property_info"
        role: "Provides detailed information about property listings."
      - name: "scheduling_assistant"
        template: "real_estate_scheduler"
        role: "Coordinates and books property viewings."
    ```

3.  **Run the Bootstrap Command:**
    ```bash
    vapi-manager squad bootstrap real_estate_reception --template real_estate_squad --deploy --env development
    ```

This single command will orchestrate the creation of all necessary tools, assistants, and the squad itself, giving you a fully functional, file-based real estate receptionist system ready for customization and deployment.

================================================================================