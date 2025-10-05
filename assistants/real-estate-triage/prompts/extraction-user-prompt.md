Extract ALL information from this real estate conversation:

## Required Data Points:

1. **Customer Information** (validated_phone is critical, first_name, last_name, email, customer_known status)
2. **Call Type** (property_inquiry_specific, property_inquiry_beginner, appointment_booking, etc.)
3. **Customer Journey Stage** (first_time_buyer, beginner_buyer, informed_buyer, etc.)
4. **Transfer Routing** (transferred_to, transfer_reason, was it silent?)
5. **Property Details** if discussed (address, type, MLS, price_range, bedrooms, search_sector)
6. **Appointment Details** if scheduled (type, date, time, status)
7. **Sentiment Analysis** (overall_sentiment, urgency_level, readiness_to_act)
8. **Lead Quality Scoring** (hot/warm/cool/cold with factors)
9. **Discovery Pitch Details** for beginners (was pitch made? customer response?)
10. **Messages Taken** for broker if any
11. **System Actions** and tools triggered
12. **Follow-up Requirements**

Return as JSON matching the schema exactly. Use null for missing values.

**Conversation:**
{{transcript}}