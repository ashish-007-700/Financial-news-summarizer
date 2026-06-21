"""Prompt used only when a model returns malformed JSON."""

REPAIR_PROMPT = """
Fix the broken JSON below so it becomes valid JSON matching the FinancialSummary
schema. Do not add new facts. Do not change values unless required to repair
syntax or field names.

Broken JSON:
{broken_json}

Return valid JSON only.
"""

