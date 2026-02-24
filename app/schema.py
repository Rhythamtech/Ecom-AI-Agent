from pydantic import BaseModel
from typing import List, Optional

class SqlResponse(BaseModel):
    query: str
    explanation: str

class QueryPlan(BaseModel):
    tables_needed: List[str]
    join_strategy: str
    filters: str
    aggregations: str
    sorting: str
    computed_columns: str
    full_plan: str

# --- Vectorstore Chunk Schemas ---

class DBChunkMetadata(BaseModel):
    doc_type: str
    table: str

class DBTableChunk(BaseModel):
    id: str
    text: str
    metadata: DBChunkMetadata

class DBChunksResponse(BaseModel):
    chunks: List[DBTableChunk]

class BusinessLogicChunk(BaseModel):
    id: str
    name: str
    description: str
    category: str
    grain: str
    formula_natural: str
    formula_sql: str
    tables: List[str]
    columns: List[str]

class BusinessLogicResponse(BaseModel):
    chunks: List[BusinessLogicChunk]

class QnAMetadata(BaseModel):
    tables: List[str]
    columns: List[str]
    category: str
    grain: str
    metric_id: str

class QnAChunk(BaseModel):
    question: str
    answer: str
    sql_query: str
    metadata: QnAMetadata

class QnAResponse(BaseModel):
    chunks: List[QnAChunk]

class CategoriesResponse(BaseModel):
    categories: List[str]