import time
import json
import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.json import JSON
from rich.live import Live
from rich.spinner import Spinner
from rich.layout import Layout
from workflow.pipeline import (
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
from src.db import SQLDB
from workflow.helper import format_json_results

app = typer.Typer(rich_markup_mode="rich")
console = Console()

def run_pipeline_orchestrator(question: str):
    """
    Main Pipeline Orchestration using a generator for status updates.
    Yields dicts with 'status' and optionally 'data' or 'error'.
    """
    rag = RAGPipeline()
    db = SQLDB()
    
    yield {"status": "Starting pipeline...", "step": 0}
    
    # Step 1: Rewrite
    yield {"status": "Rewriting query...", "step": 1}
    rewritten_q = rewrite_user_query(question)
    
    # Step 2: Parallel RAG
    yield {"status": "Retrieving context and examples...", "step": 2}
    retrieval_results = retrieve_context_parallel(rewritten_q, rag)
    
    # Step 3: Context Assembly
    yield {"status": "Assembling context...", "step": 3}
    context, few_shots = prepare_context_and_examples(retrieval_results)
    
    # Step 4: Query Planning
    yield {"status": "Creating SQL plan...", "step": 4}
    plan = create_sql_plan(question, context)
    
    # Step 5: SQL Generation
    yield {"status": "Generating SQL query...", "step": 5}
    sql_response = generate_sql_query(question, context, few_shots, plan)
    
    # Step 6: Smart Validation
    yield {"status": "Validating SQL...", "step": 6}
    validated_response = validate_generated_sql(question, sql_response, context)
    
    if hasattr(validated_response, "query"):
        yield {"status": "SQL generated successfully", "sql": validated_response.query}
    
    # Step 7: Execution & Healing
    yield {"status": "Executing SQL engine...", "step": 7}
    data, error = execute_and_heal_sql(question, validated_response, db, context)
    
    if error:
        yield {"status": "Pipeline failed", "error": error}
        return

    formatted_data = format_json_results(data)
    yield {"status": "Data retrieved successfully", "data": formatted_data}
    
    # Step 8: Data Analysis
    yield {"status": "Analyzing results...", "step": 8}
    analysis = analyze_sql_results(question, data)
    
    yield {"status": "Pipeline completed", "analysis": analysis.content}

@app.command()
def main(question: str = typer.Argument(None, help="The question to ask the AI Agent.")):
    """
    [bold green]Sqlwise AI Agent CLI[/bold green]
    
    Ask questions about your e-commerce data and get SQL-backed insights.
    """
    if question:
        process_question(question)
    else:
        console.print(Panel("[bold green]Welcome to Sqlwise AI Agent CLI![/bold green]\nType [bold red]'exit'[/bold red] or [bold red]'quit'[/bold red] to stop.", title="👋 Hello", border_style="green"))
        while True:
            try:
                question = console.input("\n[bold blue]💬 Enter your question[/bold blue]: ").strip()
                
                if question.lower() in ["exit", "quit"]:
                    console.print("[bold green]Goodbye! 👋[/bold green]")
                    break
                
                if not question:
                    continue
                    
                process_question(question)
            except KeyboardInterrupt:
                console.print("\n[bold green]Goodbye! 👋[/bold green]")
                break

def process_question(question: str):
    console.print(Panel(f"[bold blue]Question:[/bold blue] {question}", title="🚀 Sqlwise AI Agent", border_style="blue"))

    with Live(Spinner("dots", text="Initializing..."), refresh_per_second=10) as live:
        for update in run_pipeline_orchestrator(question):
            status = update.get("status")
            live.update(Spinner("dots", text=f"[bold yellow]{status}[/bold yellow]\n"))
            
            # if "sql" in update:
            #     live.update(Spinner("dots", text="[bold green]SQL Generated![/bold green]"))
            #     console.print(Panel(Syntax(update['sql'], "sql", theme="monokai", line_numbers=True), title="🔍 Generated SQL", border_style="green"))
            
            if "data" in update:
                live.update(Spinner("dots", text="[bold cyan]Data Retrieved![/bold cyan]"))
                try:
                    # Try to parse data as JSON for pretty printing if it's a string
                    data_content = update['data']
                    if isinstance(data_content, str):
                        try:
                            json_data = json.loads(data_content)
                            console.print(Panel(JSON(json.dumps(json_data)), title="📊 Data Results", border_style="cyan"))
                        except json.JSONDecodeError:
                            console.print(Panel(data_content, title="📊 Data Results", border_style="cyan"))
                    else:
                        console.print(Panel(JSON(json.dumps(data_content)), title="📊 Data Results", border_style="cyan"))
                except Exception as e:
                     console.print(Panel(str(update['data']), title="📊 Data Results (Raw)", border_style="cyan"))

            elif "analysis" in update:
                live.update(Spinner("dots", text="[bold magenta]Analysis Complete![/bold magenta]"))
                console.print(Panel(Markdown(update['analysis']), title="🤖 AI Analysis", border_style="magenta"))
            
            elif "error" in update:
                live.update(Spinner("dots", text="[bold red]Error![/bold red]"))
                console.print(Panel(f"[bold red]{update['error']}[/bold red]", title="❌ Error", border_style="red"))
            
    console.print("[bold green]✨ Pipeline Completed Successfully![/bold green]")

if __name__ == "__main__":
    app()
