import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from workflow.helper import extract_few_shot_examples, check_sql_syntax
from src.rag import RAGPipeline
from db_setup.db import SQLDB
from src.llm import (
    SQLAgent,
    DataAnalystAgent,
    QueryValidatorAgent,
    QueryRewriterAgent,
    QueryPlannerAgent,
    SelfHealerAgent,
)
from utils import convert_json_to_toon


# Singletons
query_rewriter = QueryRewriterAgent()
query_planner = QueryPlannerAgent()
sql_agent = SQLAgent()
query_validator = QueryValidatorAgent()
self_healer = SelfHealerAgent()
data_analyst = DataAnalystAgent()

def rewrite_user_query(question: str):
    return query_rewriter.rewrite(question)

def retrieve_context_parallel(question: str, rag: RAGPipeline):
    results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(rag.query_qna_index, question, "db"): "db",
            executor.submit(rag.query_qna_index, question, "business_logic", 2): "business",
            executor.submit(rag.query_qna_index, question, "qna", 3): "qna",
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception:
                results[key] = []
    return results

def prepare_context_and_examples(retrieval_results: dict):
    db_results = retrieval_results.get("db", [])
    business_results = retrieval_results.get("business", [])
    qna_results = retrieval_results.get("qna", [])

    toon_db = convert_json_to_toon(db_results)
    toon_business = convert_json_to_toon(business_results)
    toon_qna = convert_json_to_toon(qna_results)

    combined_context = toon_db + toon_business + toon_qna
    few_shots = extract_few_shot_examples(qna_results)

    return combined_context, few_shots

def create_sql_plan(question: str, context: str):
    return query_planner.plan(question, context)

def generate_sql_query(question: str, context: str, few_shots: str, plan):
    enriched_prompt = (
        f"Question: {question}\n\n"
        f"Context:\n{context}\n\n"
        f"Query Plan:\n{plan.full_plan}\n"
        f"Tables Needed: {', '.join(plan.tables_needed)}\n"
        f"Join Strategy: {plan.join_strategy}\n"
        f"Filters: {plan.filters}\n"
        f"Aggregations: {plan.aggregations}\n"
        f"Sorting: {plan.sorting}\n"
        f"Computed Columns: {plan.computed_columns}"
        f"{few_shots}"
    )
    return sql_agent.sql_agent(enriched_prompt)

def validate_generated_sql(question: str, sql_response, context: str):
    if not hasattr(sql_response, "query"):
        return sql_response

    syntax_error = check_sql_syntax(sql_response.query)
    if syntax_error is None:
        return sql_response

    return query_validator.validate_query(
        f"Question: {question}\n SQL Error: {syntax_error}",
        sql_response.query
    )

def execute_and_heal_sql(question: str, sql_response, db: SQLDB, context: str, max_retries: int = 3):
    if not hasattr(sql_response, "query"):
        return None, "No SQL query generated"

    current_sql = sql_response.query

    for attempt in range(1, max_retries + 1):
        try:
            data = db.query_db(current_sql)

            # Check for empty results
            rows = data.get("rows", [])
            columns = data.get("columns", [])

            if not rows and not columns:
                raise Exception("Query returned EMPTY results.")

            return data, None

        except Exception as e:
            if attempt < max_retries:
                healed = self_healer.heal(
                    question=question,
                    failed_sql=current_sql,
                    error_msg=str(e),
                    context=context,
                )
                current_sql = healed.query
            else:
                return None, str(e)

    return None, "All retry attempts exhausted"

def analyze_sql_results(question: str, data: dict):
    return data_analyst.data_analyst(question, str(data))
