import json
import os
from .db import SQLDB
from itertools import product
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.llm import SchemaChunkerAgent, BusinessLogicChunkerAgent, QnAChunkerAgent
from src.llm import CategoryGeneratorAgent
from utils import convert_json_to_toon

db = SQLDB()

def extract_tables():
    tables = db.query_db("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES")
    return [table[0] for table in tables['rows']] if tables['rows'] else []

def extract_schema(selected_tables):
    placeholders = ', '.join(f"'{table}'" for table in selected_tables)
    schema = db.query_db(f"SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME IN ({placeholders})")
    return schema

def create_metadata_table():
    check = db.query_db("SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'metadata'")
    if check.get('rows'):
        return
    db.query_db("CREATE TABLE metadata (TableName VARCHAR(255), Field VARCHAR(255), Description VARCHAR(255))")

def insert_metadata(metadata):
    table_name = metadata[1]
    col_name = metadata[2]
    db.query_db(f"INSERT INTO metadata (TableName, Field, Description) VALUES ('{table_name}', '{col_name}', '')")

def save_json(data, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"✅ Saved generated objects to {filepath}")

def serialize_pydantic_list(object_list):
    """Converts a list of Pydantic models to a list of dicts for JSON serialization."""
    if not object_list:
        return []
    # Support for Pydantic v2 (model_dump) and v1 (dict)
    return [obj.model_dump() if hasattr(obj, "model_dump") else (obj.dict() if hasattr(obj, "dict") else obj) 
            for obj in object_list]

def process_qna_generation(diff, biz_logic_ids, schema_context_str, qna_agent):
    print(f"  - Generating {diff} questions...")
    biz_logic_ids_str = ", ".join(biz_logic_ids)
    diff_context = (
        f"Schema Context: {schema_context_str}\n\n"
        f"Business Logic Focus on: {biz_logic_ids_str}"
        f"Difficulty Level: {diff}\n\n"
    )
    try:
        qna_response = qna_agent.generate_qna(diff_context)
        return serialize_pydantic_list(qna_response.chunks)
    except Exception as e:
        print(f"  - Error generating QnA for {diff}: {e}")
        return []

def setup():
    print("Initializing Database Setup with LLM Chunk Generation...")
    create_metadata_table()

    # 1. List all the tables
    all_tables = extract_tables()
    if not all_tables:
        print("No tables found in the database. Ensure your connection is correct and database is populated.")
        return

    print("\nAvailable tables in the database:")
    for i, table in enumerate(all_tables, 1):
        print(f"{i}. {table}")

    # 2. Select the tables want to use for proceed or all
    print("\nEnter a comma-separated list of tables to process, or type 'all' to process all tables.")
    user_input = input("Tables to process: ").strip()

    if user_input.lower() == 'all':
        selected_tables = all_tables
    else:
        selected_tables = [t.strip() for t in user_input.split(',')]
        invalid_tables = [t for t in selected_tables if t not in all_tables]
        if invalid_tables:
            print(f"Error: The following tables are not in the database: {', '.join(invalid_tables)}")
            return

    if not selected_tables:
        print("No tables selected. Exiting.")
        return

    print(f"\nProceeding with {len(selected_tables)} table(s): {', '.join(selected_tables)}")

    # 3. Proceed selected Tables.
    schema = extract_schema(selected_tables)

    if schema['rows']:
        # Group schema by table for toon compression
        schema_dict = {}
        for row in schema['rows']:
            _sch, table_name, column_name, data_type = row
            if table_name not in schema_dict:
                schema_dict[table_name] = {}
            schema_dict[table_name][column_name] = data_type

        schema_context_str = convert_json_to_toon(schema_dict)

        print("\nUsing LLM to generate chunks...")

        chunk_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'json_chunks')

        # Generator Agents
        schema_agent = SchemaChunkerAgent()
        business_agent = BusinessLogicChunkerAgent()
        qna_agent = QnAChunkerAgent()
        category_agent = CategoryGeneratorAgent()

        print("1. Generating DB Schema Chunks...")
        db_response = schema_agent.generate_chunks(schema_context_str)
        db_chunks = serialize_pydantic_list(db_response.chunks)
        save_json(db_chunks, os.path.join(chunk_dir, 'db.json'))
        
        print("2. Generate Categories...")
        categories = category_agent.generate_categories(schema_context_str)
        categories = categories.categories

        print("3. Generating Business Logic Chunks...")

        biz_chunks = []
        # Assuming 'categories' is your list
        tri_cat_chunks = [categories[i : i + 2] for i in range(0, len(categories), 2)]
        
        def process_biz_logic(cat):
            print(f"  - Generating logic for {cat}...")
            cat_context = f"{schema_context_str}\n\nFocus ONLY on metrics for: {cat}."
            biz_response = business_agent.generate_business_logic(cat_context)
            return serialize_pydantic_list(biz_response.chunks)

        with ThreadPoolExecutor(max_workers=3) as executor:
            biz_futures = {executor.submit(process_biz_logic, cat): cat for cat in tri_cat_chunks}
            for future in as_completed(biz_futures):
                cat = biz_futures[future]
                try:
                    biz_chunks.extend(future.result())
                except Exception as e:
                    print(f"  - Error generating for {cat}: {e}")

        save_json(biz_chunks, os.path.join(chunk_dir, 'business_logic.json'))

        print("4. Generating QnA Chunks...")

        qna_difficulties = ["Simple", "Moderate", "Complex"]
        tri_biz_logic_chunks = [[b['id'] for b in biz_chunks[i:i+4]] for i in range(0, len(biz_chunks), 4)]
        
        qna_chunks = []
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for diff, biz_logic_ids in product(qna_difficulties, tri_biz_logic_chunks):
                futures.append(executor.submit(process_qna_generation, diff, biz_logic_ids, schema_context_str, qna_agent))
            
            for future in as_completed(futures):
                qna_chunks.extend(future.result())

        save_json(qna_chunks, os.path.join(chunk_dir, 'qna.json'))

        print(f"\nAll chunks generated successfully! (Biz: {len(biz_chunks)}, QnA: {len(qna_chunks)})")
    else:
        print("No schema details found for the selected tables.")


