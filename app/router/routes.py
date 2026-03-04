import json
from fastapi import APIRouter
from workflow.rag_pipeline import (
    rewrite_user_query,
    retrieve_context_parallel,
    prepare_context_and_examples,
    create_sql_plan,
    generate_sql_query,
    validate_generated_sql,
    execute_and_heal_sql,
    analyze_sql_results
)
from src.rag import RAGPipeline
from db_setup.db import SQLDB
from workflow.helper import format_json_results
from fastapi.responses import StreamingResponse

api_router = APIRouter()

def run_pipeline_orchestrator(question: str):
    """
    Main Pipeline Orchestration using a generator for message updates.
    Yields dicts with 'message' and optionally 'data' or 'error'.
    """
    rag = RAGPipeline()
    db = SQLDB()
    
    yield json.dumps({"message": "Starting pipeline...", "step": 0}) + "\n"
    
    # Step 1: Rewrite
    yield json.dumps({"message": "Rewriting query...", "step": 1}) + "\n"
    rewritten_q = rewrite_user_query(question)
    
    # Step 2: Parallel RAG
    yield json.dumps({"message": "Retrieving context and examples...", "step": 2}) + "\n"
    retrieval_results = retrieve_context_parallel(rewritten_q, rag)
    
    # Step 3: Context Assembly
    yield json.dumps({"statu": "Assembling context...", "step": 3}) + "\n"
    context, few_shots = prepare_context_and_examples(retrieval_results)
    
    # Step 4: Query Planning
    yield json.dumps({"message": "Creating SQL plan...", "step": 4}) + "\n"
    plan = create_sql_plan(question, context)
    
    # Step 5: SQL Generation
    yield json.dumps({"message": "Generating SQL query...", "step": 5}) + "\n"
    sql_response = generate_sql_query(question, context, few_shots, plan)
    
    # Step 6: Smart Validation
    yield json.dumps({"message": "Validating SQL...", "step": 6.1}) + "\n"
    validated_response = validate_generated_sql(question, sql_response, context)
    
    if hasattr(validated_response, "query"):
        yield json.dumps({"message": "SQL generated successfully", "step": 6.2}) + "\n"
    
    # Step 7: Execution & Healing
    yield json.dumps({"message": "Executing SQL engine...", "step": 7}) + "\n"
    data, error = execute_and_heal_sql(question, validated_response, db, context)
    
    if error:
        yield json.dumps({"message": "Pipeline failed", "error": str(error)}) + "\n"
        return

    formatted_data = format_json_results(data)
    yield json.dumps({"message": "Data retrieved successfully", "data": str(formatted_data)}) + "\n"
    
    # Step 8: Data Analysis
    yield json.dumps({"message": "Analyzing results...", "step": 8}) + "\n"
    analysis = analyze_sql_results(question, data) # type: ignore
    
    yield json.dumps({"message": "Pipeline completed", "analysis": str(analysis.content)}) + "\n" # type: ignore



@api_router.get('/health')
def health_check():
    return {"status":200, "message":"Sucess OK !!"}


@api_router.get('/rag/excute')
def rag_execute(question:str):
    return StreamingResponse(run_pipeline_orchestrator(question), media_type="text/event-stream")
