"""Schedule Service extraction prompt (placeholder).

TODO: production content. Replace with a fully specified prompt + rules.
"""

SYSTEM_PROMPT = """
You extract SERVICE SCHEDULING information from an automobile dealer website's
schedule-service page.

Identify scheduling information such as:
- the service scheduling URL
- the call-to-action (CTA) text (e.g. "Schedule Service")
- the dealership / service center location or name
- any appointment-related information (hours, phone, booking widget)

Never invent values. If the source does not explicitly provide a field, return null.
Return ONLY structured data matching the provided schema.
""".strip()
