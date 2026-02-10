import json
from src.db import SQLDB
from src.llm import SQLAgent, DataAnalystAgent
from src.rag import RAGPipeline

def pretty_print_json(data):
    """Beautifies and prints JSON data, handling Pydantic models and lists of objects."""
    if isinstance(data, list):
        data = [obj.dict() if hasattr(obj, 'dict') else obj for obj in data]
    elif hasattr(data, 'dict'):
        data = data.dict()
    
    print(json.dumps(data, indent=4, default=str, sort_keys=True))

def main():
    db = SQLDB()
    q = "How can i boost the revenue?"
    
    # Analyze query using RAG or SQL Agent
    # Note: Swap to SQLAgent() if you need query generation
    context = RAGPipeline().query_qna_index(q)
    
    print("\n" + "═"*60)
    print(" 🔍  ANALYSING THE USER QUERY")
    print("═"*60)
    pretty_print_json(context)
    print("═"*60 + "\n")

    # Analyze query using RAG or SQL Agent
    # Note: Swap to SQLAgent() if you need query generation
    response = SQLAgent().sql_agent(question=q + "\n\n" + str(context))
  
    # Example of how to use the results further:
    if hasattr(response, 'query'):
        data = db.query_db(response.query)
        print(" 📊  DATABASE RESULTS")
        pretty_print_json(data)
    
        print(" 🤖  LLM ANALYSIS")
        analysis = DataAnalystAgent().data_analyst(q, data)
        print(analysis.content)

    

if __name__ == "__main__":
    main()
