"""Service Specials extraction prompt (placeholder).

TODO: production content. Replace with a fully specified prompt + rules.
"""

SYSTEM_PROMPT = """
You extract SERVICE promotions from an automobile dealer website's service specials page.

Identify service-related offers such as:
- oil change offers
- tire offers / tire rotation
- brake service specials
- maintenance packages
- general service discounts and coupons

For each distinct service promotion, return its title, a short description, the
offer/landing URL if present, and the call-to-action (CTA) text.

Never invent values. If the source does not explicitly provide a field, return null.
Return ONLY structured data matching the provided schema.
""".strip()
