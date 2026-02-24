from __future__ import annotations

from dataclasses import dataclass
from typing import Dict
from datetime import datetime


@dataclass
class Chunk:
    id: str
    source_type: str  # e.g. 'db_schema', 'business_logic', 'qna_logic'
    source_id: str    # a reference to the original artifact (path or name)
    chunk_text: str
    created_at: str   # ISO timestamp
    metadata: Dict
