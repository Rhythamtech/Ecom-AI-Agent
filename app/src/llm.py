from langchain_openai import ChatOpenAI
from .config import settings
from .prompts import (
    sql_system_prompt, data_analyst_prompt,
    query_validator_prompt, query_rewriter_prompt, query_planner_prompt,
    self_healer_prompt, schema_chunker_prompt, business_logic_chunker_prompt,
    qna_chunker_prompt, category_generator_prompt
)
from schema import (
    SqlResponse, QueryPlan, DBChunksResponse, 
    BusinessLogicResponse, QnAResponse,
    CategoriesResponse
)
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from typing import Optional
load_dotenv()



llm = ChatOpenAI(
    model=settings.OPENAI_MODEL,
    base_url=settings.OPENAI_BASE_URL,
    api_key=settings.OPENAI_API_KEY
)


class BaseAgent:
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt
    
    def base_agent(self, question: str, data: Optional[str] = None, schema: Optional[object] = None):
        prompt = ChatPromptTemplate.from_messages([
        ("system", self.system_prompt),
        ("user", "{question} \n {data}"),])

        chain = prompt | llm

        if schema:
            chain = prompt | llm.with_structured_output(schema)
            return chain.invoke({"question": question, "data": data})
        return chain.invoke({"question": question, "data": data})



class SQLAgent(BaseAgent):
    def __init__(self):
        super().__init__(sql_system_prompt)
    
    def sql_agent(self, question: str):
        schema = SqlResponse
        return self.base_agent(question=question, schema=schema)

class DataAnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__(data_analyst_prompt)
    
    def data_analyst(self, question: str, data: str):
        schema = None
        return self.base_agent(question=question, data=data)



class QueryValidatorAgent(BaseAgent):
    def __init__(self):
        super().__init__(query_validator_prompt)
    
    def validate_query(self, query: str, data: str):
        schema = SqlResponse
        return self.base_agent(question=query, data=data, schema=schema)


# ─── RAH Pipeline Agents ──────────────────────────────────────────

class QueryRewriterAgent(BaseAgent):
    def __init__(self):
        super().__init__(query_rewriter_prompt)

    def rewrite(self, question: str, db_context: str = "") -> str:
        return self.base_agent(question=question, data=db_context).content


class QueryPlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__(query_planner_prompt)

    def plan(self, question: str, context: str) -> QueryPlan:
        return self.base_agent(question=question, data=context, schema=QueryPlan)


class SelfHealerAgent(BaseAgent):
    def __init__(self):
        super().__init__(self_healer_prompt)

    def heal(self, question: str, failed_sql: str, error_msg: str, context: str) -> SqlResponse:
        diagnosis_input = (
            f"Original Question: {question}\n\n"
            f"Failed SQL Query:\n{failed_sql}\n\n"
            f"Error / Issue:\n{error_msg}\n\n"
            f"Database Context:\n{context}"
        )
        return self.base_agent(question=diagnosis_input, schema=SqlResponse)


# ─── Data Ingestion / Setup Agents ────────────────────────────────

class SchemaChunkerAgent(BaseAgent):
    def __init__(self):
        super().__init__(schema_chunker_prompt)

    def generate_chunks(self, schema_context: str) -> DBChunksResponse:
        return self.base_agent(question="", data=schema_context, schema=DBChunksResponse)

class BusinessLogicChunkerAgent(BaseAgent):
    def __init__(self):
        super().__init__(business_logic_chunker_prompt)

    def generate_business_logic(self, schema_context: str) -> BusinessLogicResponse:
        return self.base_agent(question="", data=schema_context, schema=BusinessLogicResponse)

class QnAChunkerAgent(BaseAgent):
    def __init__(self):
        super().__init__(qna_chunker_prompt)

    def generate_qna(self, schema_context: str) -> QnAResponse:
        return self.base_agent(question="", data=schema_context, schema=QnAResponse)

class CategoryGeneratorAgent(BaseAgent):
    def __init__(self):
        super().__init__(category_generator_prompt)

    def generate_categories(self, schema_context: str) -> CategoriesResponse:
        return self.base_agent(question="", data=schema_context, schema=CategoriesResponse)
