import os
from typing import Annotated, Sequence, TypedDict, Optional, List, Dict, Any
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import Graph, StateGraph, END
from db_inspector import DVDRentalInspector
import config

# Load environment variables
load_dotenv()

def get_db_config():
    """Read database configuration."""
    return {
        'host': 'localhost',
        'database': 'dvdrental',
        'user': 'postgres',
        'password': 'your_password'
    }

def get_db_connection():
    """Get a connection to the database."""
    try:
        # Get database configuration
        params = config.config(section='local')
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(**params)
        return conn
    except Exception as e:
        raise Exception(f"Error connecting to the database: {str(e)}")

class State(TypedDict):
    """State type for the conversation."""
    messages: List[Any]  # List of messages in the conversation
    sql_query: str  # Generated SQL query
    query_result: Optional[List[Dict[str, Any]]]  # Results from database query
    current_response: str  # Current response being generated


def generate_sql(state: State) -> State:
    """Generate SQL query based on user input."""
    try:
        # Get database schema information
        inspector = DVDRentalInspector()
        schema_info = inspector.get_schema_for_prompt()
        table_stats = inspector.get_table_stats()
        
        # Create a comprehensive schema context
        schema_context = (f"Database Schema:\n"
                         f"{schema_info}\n\n"
                         f"Table Statistics:\n"
                         f"{table_stats}\n\n"
                         f"Important Rules:\n"
                         f"1. ALWAYS prefix column names with their table name or alias (e.g., customer.customer_id, c.customer_id)\n"
                         f"2. When joining tables:\n"
                         f"   - Use meaningful table aliases (e.g., c for customer, f for film)\n"
                         f"   - Qualify all column references with table aliases\n"
                         f"   - Use proper JOIN syntax (INNER JOIN, LEFT JOIN, etc.)\n"
                         f"3. In GROUP BY and ORDER BY:\n"
                         f"   - Use fully qualified column names\n"
                         f"   - Reference columns by their position number if using expressions\n"
                         f"4. For complex queries, use CTEs (WITH clause) to improve readability\n"
                         f"5. Handle NULL values appropriately using IS NULL or IS NOT NULL\n"
                         f"6. Use DISTINCT when necessary to avoid duplicate rows\n"
                         f"7. Always test edge cases (e.g., no results, NULL values)")
        
        example_query = """SELECT 
    c.customer_id,
    c.first_name,
    c.last_name,
    COUNT(r.rental_id) as rental_count
FROM 
    customer c
    INNER JOIN rental r ON c.customer_id = r.customer_id
GROUP BY 
    c.customer_id, c.first_name, c.last_name
ORDER BY 
    rental_count DESC"""
        
        messages = [
            SystemMessage(content=(f"You are a SQL query generator for a DVD rental database.\n"
                                 f"Generate only the SQL query without any markdown formatting or explanation.\n"
                                 f"The query should be executable in PostgreSQL.\n\n"
                                 f"{schema_context}\n\n"
                                 f"Example of a well-formed query:\n"
                                 f"{example_query}")),
            HumanMessage(content=state["messages"][-1].content)
        ]
        
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        response = llm.invoke(messages)
        sql_query = response.content.strip()
        
        # Clean any potential markdown formatting
        sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
        
        print(f"\nGenerated SQL: {sql_query}")
        
        return {
            "messages": state["messages"],
            "sql_query": sql_query,
            "query_result": state["query_result"],
            "current_response": state["current_response"]
        }
        
    except Exception as e:
        error_msg = f"Error generating SQL query: {str(e)}"
        print(error_msg)
        return {
            "messages": state["messages"],
            "sql_query": "",
            "query_result": None,
            "current_response": error_msg
        }

def execute_query(state: State) -> State:
    """Execute SQL query and return results."""
    print("\nExecuting query...\n")
    
    try:
        # Get database connection
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Execute query
        cur.execute(state["sql_query"])
        results = cur.fetchall()
        
        # Close database connection
        cur.close()
        conn.close()
        
        return {
            "messages": state["messages"],
            "sql_query": state["sql_query"],
            "query_result": results,
            "current_response": format_query_result(results)
        }
        
    except Exception as e:
        error_msg = f"Error executing query: {str(e)}"
        print(error_msg)
        return {
            "messages": state["messages"],
            "sql_query": state["sql_query"],
            "query_result": None,
            "current_response": error_msg
        }


def format_query_result(query_result: List[Dict[str, Any]]) -> str:
    """Format query result into a readable string."""
    if not query_result:
        return "No results found."
        
    # Get all column names from the first row
    columns = list(query_result[0].keys())
    
    # Format the results based on the number of rows
    if len(query_result) > 10:
        # For large result sets, show summary
        formatted = f"Found {len(query_result)} results. Here are the top 10:\n\n"
        rows = query_result[:10]
    else:
        formatted = f"Found {len(query_result)} results:\n\n"
        rows = query_result
    
    # Format each row
    for i, row in enumerate(rows, 1):
        row_str = []
        for col in columns:
            value = row[col]
            # Format numbers with commas
            if isinstance(value, (int, float)):
                value = f"{value:,}"
            row_str.append(f"{col}: {value}")
        formatted += f"{i}. " + ", ".join(row_str) + "\n"
    
    # Add note if results were truncated
    if len(query_result) > 10:
        formatted += f"\n... and {len(query_result) - 10} more results"
    
    return formatted

def generate_response(state: State) -> State:
    """Generate natural language response from query results."""
    if not state["query_result"]:
        error_msg = ("I apologize, but I couldn't retrieve the information from the database. This could be due to:\n"
                    "1. Database connection issues\n"
                    "2. Invalid SQL query\n"
                    "3. No results found\n\n"
                    "Please try rephrasing your question or ask about a different topic.")
        return {
            "messages": state["messages"],
            "sql_query": state["sql_query"],
            "query_result": None,
            "current_response": error_msg
        }

    results = state["query_result"]
    
    try:
        # Get database schema information for context
        inspector = DVDRentalInspector()
        schema_info = inspector.get_schema_for_prompt()
        table_stats = inspector.get_table_stats()
        
        # Create a comprehensive response context
        system_message = (f"You are a helpful assistant for a DVD rental store database.\n"
                         f"Your task is to interpret SQL query results and provide clear, natural language responses.\n\n"
                         f"Database Context:\n{schema_info}\n\n"
                         f"Table Statistics:\n{table_stats}\n\n"
                         f"Guidelines for Response:\n"
                         f"1. Focus on the most relevant information and present it in a way that's easy to understand\n"
                         f"2. If there are many results, summarize the key findings and mention only the most notable examples\n"
                         f"3. For movie-related queries:\n"
                         f"   - Always include the movie titles\n"
                         f"   - Mention relevant categories, ratings, or rental rates when applicable\n"
                         f"4. For customer-related queries:\n"
                         f"   - Use full names (first_name + last_name)\n"
                         f"   - Include relevant rental history or payment information\n"
                         f"5. When discussing time periods:\n"
                         f"   - Convert timestamps to readable dates\n"
                         f"   - Specify the time period covered by the data\n"
                         f"6. For numerical results:\n"
                         f"   - Round decimal values appropriately\n"
                         f"   - Use proper formatting for currency values\n"
                         f"   - Include percentages when relevant")

        # Create prompt for response generation
        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=state["messages"][-1].content),
            SystemMessage(content=f"SQL Query: {state['sql_query']}"),
            SystemMessage(content=f"Query Results:\n{format_query_result(results)}")
        ]
        
        # Generate response using ChatGPT
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        response = llm.invoke(messages)
        
        return {
            "messages": state["messages"],
            "sql_query": state["sql_query"],
            "query_result": results,
            "current_response": response.content
        }
    except Exception as e:
        error_msg = f"Error generating response: {str(e)}"
        print(error_msg)
        return {
            "messages": state["messages"],
            "sql_query": state["sql_query"],
            "query_result": results,
            "current_response": error_msg
        }

def create_graph() -> Graph:
    """Create the LangGraph workflow."""
    # Create graph
    workflow = StateGraph(State)
    
    # Add nodes for each step
    workflow.add_node("generate_sql", generate_sql)
    workflow.add_node("execute_query", execute_query)
    workflow.add_node("generate_response", generate_response)
    
    # Add edges between nodes
    workflow.add_edge("generate_sql", "execute_query")
    workflow.add_edge("execute_query", "generate_response")
    
    # Set entry and exit points
    workflow.set_entry_point("generate_sql")
    workflow.set_finish_point("generate_response")
    
    # Compile graph
    return workflow.compile()

def main():
    """Main chat loop."""
    print("\n=== DVD Rental Database Assistant ===")
    print("Type 'quit' or 'exit' to end the session")
    print("Ask questions about movies, rentals, customers, etc.\n")
    print("Example questions:")
    print("1. What are the top 5 most rented movies?")
    print("2. Which movies have never been rented?")
    print("3. Who are our most active customers?")
    print("4. What's the average rental duration?")
    print("5. How many movies do we have in each category?\n")

    # Test database connection
    try:
        conn = get_db_connection()
        conn.close()
        print("Database connection successful!\n")
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        return

    # Initialize state
    state: State = {
        "messages": [],
        "sql_query": "",
        "query_result": None,
        "current_response": ""
    }

    # Create workflow
    workflow = create_graph()

    while True:
        # Get user input
        user_input = input("\nYour question: ").strip()
        
        # Check for exit command
        if user_input.lower() in ['quit', 'exit']:
            print("\nGoodbye!")
            break
        
        if not user_input:
            continue

        print("\nThinking...\n")
        
        # Add user message to state
        state["messages"] = [HumanMessage(content=user_input)]
        
        try:
            # Generate SQL
            state = generate_sql(state)
            if state["sql_query"]:
                print("Generated SQL:", state["sql_query"])
            
            # Execute query and get response
            state = execute_query(state)
            if state["query_result"] is not None:
                state = generate_response(state)
                if state["current_response"]:
                    print("\nResponse:", state["current_response"])
                else:
                    print("\nNo response generated.")
            else:
                print("\nQuery execution failed.")
                
        except Exception as e:
            print(f"\nError: {str(e)}")
            continue


if __name__ == "__main__":
    main()
