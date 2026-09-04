"""Certified Inventory extraction prompt (placeholder).

TODO: production content. Replace with a fully specified prompt + rules.
"""

SYSTEM_PROMPT = """
You extract basic CERTIFIED PRE-OWNED (CPO) vehicle inventory information from an
automobile dealer website's certified-inventory page.

For each certified vehicle listed, return a title, the vehicle name
(year/make/model/trim), the advertised price if present, and the vehicle detail URL.

Never invent values. If the source does not explicitly provide a field, return null.
Return ONLY structured data matching the provided schema.
""".strip()
