import os
from typing import Dict, Any, List
import psycopg2
from psycopg2.extras import RealDictCursor
import config
from query_error_recovery import QueryRecoveryHelper
import re

def test_query_recovery():
    """Test the query recovery functionality with various scenarios."""
    
    # Get database connection parameters
    params = config.config(section='local')
    print("Database parameters:", params)
    
    # Initialize the recovery helper
    recovery_helper = QueryRecoveryHelper(params)
    
    # Test cases with slightly misspelled movie titles
    test_cases = [
        ("""
        SELECT f.title, f.description 
        FROM film f 
        WHERE f.title = 'Jurasic Park'
        """, "film.title", "Jurasic Park"),
        
        ("""
        SELECT f.title, f.description 
        FROM film f 
        WHERE f.title LIKE '%Star Warz%'
        """, "film.title", "Star Warz"),
        
        ("""
        SELECT f.title, c.name 
        FROM film f 
        JOIN film_category fc ON f.film_id = fc.film_id 
        JOIN category c ON fc.category_id = c.category_id 
        WHERE c.name = 'Sience Fiction'
        """, "category.name", "Sience Fiction"),
        
        # Additional test case for Sci-Fi
        ("""
        SELECT f.title, c.name 
        FROM film f 
        JOIN film_category fc ON f.film_id = fc.film_id 
        JOIN category c ON fc.category_id = c.category_id 
        WHERE c.name = 'SciFi'
        """, "category.name", "SciFi")
    ]
    
    # First, let's check if we can connect and get some sample data
    try:
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        print("\nChecking database connection...")
        
        # Get some sample film titles
        cur.execute("SELECT title FROM film LIMIT 5")
        sample_titles = cur.fetchall()
        print("\nSample film titles:", sample_titles)
        
        # Get categories
        cur.execute("SELECT name FROM category")
        categories = cur.fetchall()
        print("\nAvailable categories:", categories)
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database connection test failed: {str(e)}")
        return
    
    for test_query, field_path, search_term in test_cases:
        print("\nTesting query:")
        print(test_query.strip())
        print("-" * 50)
        
        conn = None
        try:
            # First try to execute the original query
            conn = psycopg2.connect(**params)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(test_query)
            results = cur.fetchall()
            
            # If no results found, treat it as an error case
            if not results:
                raise Exception(f"No results found for {search_term}")
                
            cur.close()
            print("Results found:", results)
            
        except Exception as e:
            error_msg = str(e)
            print(f"Query failed or returned no results: {error_msg}")
            
            print(f"\nLooking for similar values to '{search_term}' in {field_path}...")
            table, column = field_path.split('.')
            
            # Get all possible values for this column
            cur = conn.cursor()
            cur.execute(f"SELECT DISTINCT {column} FROM {table}")
            possible_values = [str(row[0]) for row in cur.fetchall()]
            
            # For categories, add some common variations
            if table == 'category':
                search_variations = [
                    search_term,
                    search_term.replace(' ', '-'),
                    search_term.replace('-', ' '),
                    'Sci-Fi' if 'sci' in search_term.lower() else search_term,
                    'Science Fiction' if 'sci' in search_term.lower() else search_term
                ]
                
                # Try each variation
                best_similar = None
                best_score = 0
                for variation in search_variations:
                    similar = recovery_helper.find_similar_values(variation, possible_values)
                    if similar and similar[0][1] > best_score:
                        best_similar = similar[0]
                        best_score = similar[0][1]
                
                if best_similar:
                    similar = [(best_similar[0], best_similar[1])]
                else:
                    similar = []
            else:
                # For other fields, use regular fuzzy matching
                similar = recovery_helper.find_similar_values(search_term, possible_values)
            
            if similar:
                print("\nSimilar values found:")
                for match, score in similar:
                    print(f"  - {match} (similarity: {score}%)")
                
                # Use the best match to create a recovered query
                best_match = similar[0][0]
                recovered_query = test_query.replace(f"'{search_term}'", f"'{best_match}'")
                recovered_query = recovered_query.replace(f"'%{search_term}%'", f"'%{best_match}%'")
                
                print("\nTrying recovered query:")
                print(recovered_query.strip())
                
                try:
                    cur = conn.cursor(cursor_factory=RealDictCursor)
                    cur.execute(recovered_query)
                    results = cur.fetchall()
                    print("\nQuery executed successfully!")
                    print("Results:")
                    for row in results:
                        print(row)
                except Exception as e2:
                    print(f"\nRecovered query failed: {str(e2)}")
            else:
                print(f"No similar values found for '{search_term}'")
        
        finally:
            if conn:
                conn.close()

def extract_movie_title(question):
    """Extract movie title from the question."""
    # Common patterns for movie titles in questions
    patterns = [
        r"'([^']+)'",  # Matches anything in single quotes
        r'"([^"]+)"',  # Matches anything in double quotes
        r"(?:rented|watched|borrowed)\s+(?:the\s+)?(?:movie\s+)?([A-Za-z0-9\s]+?)(?:\s+(?:movie|film))?\s*\??$",  # Matches "rented MOVIE_NAME"
        r"(?:rented|watched|borrowed)\s+(?:the\s+)?(?:movie\s+)?([A-Za-z0-9\s]+?)(?:\s+(?:on|at|in|from))?"  # Matches "rented MOVIE_NAME on/at/in"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None

def get_highest_demand_movie():
    """Get the movie with the highest number of rentals."""
    return """
    WITH rental_counts AS (
        SELECT 
            f.film_id,
            f.title,
            COUNT(r.rental_id) AS rental_count
        FROM 
            film f
            INNER JOIN inventory i ON f.film_id = i.film_id
            INNER JOIN rental r ON i.inventory_id = r.inventory_id
        GROUP BY 
            f.film_id, f.title
    )
    SELECT 
        film_id,
        title,
        rental_count
    FROM 
        rental_counts
    ORDER BY 
        rental_count DESC
    LIMIT 1;
    """

def get_query_template(question: str) -> tuple[str, dict]:
    """Get the appropriate query template based on the question pattern."""
    # Define query patterns and their corresponding templates
    patterns = [
        # Who rented a specific movie
        {
            'pattern': r'(?:who|which\s+customers?)\s+(?:has\s+)?rented\s+(?:the\s+)?(?:movie\s+)?([^?]+)',
            'template': """
                SELECT 
                    c.first_name,
                    c.last_name,
                    r.rental_date
                FROM 
                    customer c
                    JOIN rental r ON c.customer_id = r.customer_id
                    JOIN inventory i ON r.inventory_id = i.inventory_id
                    JOIN film f ON i.film_id = f.film_id
                WHERE 
                    f.title ILIKE %s;
            """,
            'params': lambda m: (m.group(1).strip().strip("'\""),)
        },
        # Movie with highest demand/most rentals
        {
            'pattern': r'(?:which|what)\s+(?:movie|film)\s+(?:has|with)\s+(?:the\s+)?(?:highest|most)\s+(?:demand|rentals?|popularity)',
            'template': """
                WITH rental_counts AS (
                    SELECT 
                        f.film_id,
                        f.title,
                        COUNT(r.rental_id) AS rental_count
                    FROM 
                        film f
                        INNER JOIN inventory i ON f.film_id = i.film_id
                        INNER JOIN rental r ON i.inventory_id = r.inventory_id
                    GROUP BY 
                        f.film_id, f.title
                )
                SELECT 
                    film_id,
                    title,
                    rental_count
                FROM 
                    rental_counts
                ORDER BY 
                    rental_count DESC
                LIMIT 1;
            """,
            'params': lambda m: tuple()
        },
        # Movie with highest profit
        {
            'pattern': r'(?:which|what)\s+(?:movie|film)\s+(?:made|generated|earned|has|with)\s+(?:the\s+)?(?:highest|most|maximum)\s+(?:profit|revenue|earnings|money|income)',
            'template': """
                WITH film_profit AS (
                    SELECT 
                        f.film_id,
                        f.title,
                        SUM(p.amount) AS total_profit
                    FROM 
                        film f
                        INNER JOIN inventory i ON f.film_id = i.film_id
                        INNER JOIN rental r ON i.inventory_id = r.inventory_id
                        INNER JOIN payment p ON r.rental_id = p.rental_id
                    GROUP BY 
                        f.film_id, f.title
                )
                SELECT 
                    film_id,
                    title,
                    total_profit
                FROM 
                    film_profit
                ORDER BY 
                    total_profit DESC
                LIMIT 1;
            """,
            'params': lambda m: tuple()
        },
        # Top N most rented movies
        {
            'pattern': r'(?:what|show|list)\s+(?:are|me)\s+(?:the\s+)?(?:top|most)\s+(\d+)\s+(?:most\s+)?(?:rented|popular)\s+(?:movies|films)',
            'template': """
                WITH rental_counts AS (
                    SELECT 
                        f.film_id,
                        f.title,
                        COUNT(r.rental_id) AS rental_count
                    FROM 
                        film f
                        INNER JOIN inventory i ON f.film_id = i.film_id
                        INNER JOIN rental r ON i.inventory_id = r.inventory_id
                    GROUP BY 
                        f.film_id, f.title
                )
                SELECT 
                    film_id,
                    title,
                    rental_count
                FROM 
                    rental_counts
                ORDER BY 
                    rental_count DESC
                LIMIT %s;
            """,
            'params': lambda m: (int(m.group(1)),)
        },
        # Movies by category
        {
            'pattern': r'(?:show|list|what)\s+(?:me\s+)?(?:are\s+)?(?:the\s+)?(?:movies|films)\s+(?:in|from)\s+(?:the\s+)?(\w+)\s+category',
            'template': """
                SELECT 
                    f.title,
                    c.name as category,
                    f.release_year,
                    f.rating
                FROM 
                    film f
                    JOIN film_category fc ON f.film_id = fc.film_id
                    JOIN category c ON fc.category_id = c.category_id
                WHERE 
                    c.name ILIKE %s
                ORDER BY 
                    f.title;
            """,
            'params': lambda m: (m.group(1).strip(),)
        }
    ]
    
    # Try to match the question against patterns
    question = question.strip().lower()
    for p in patterns:
        match = re.search(p['pattern'], question, re.IGNORECASE)
        if match:
            params = p['params'](match)
            return p['template'], params
    
    return None, None

def format_query_result(question: str, results: List[Dict[str, Any]]) -> str:
    """Format query results based on the question type."""
    if not results:
        return "No results found."
        
    if "profit" in question.lower() or "revenue" in question.lower() or "earnings" in question.lower():
        result = results[0]
        return f"The movie that made the most profit is \"{result['title']},\" with a total profit of ${result['total_profit']:.2f}."
        
    if "highest demand" in question.lower() or "most rented" in question.lower():
        result = results[0]
        return f"The movie with the highest demand is \"{result['title']},\" which has been rented {result['rental_count']} times."
    
    if "top" in question.lower() and "most rented" in question.lower():
        response = ["Here are the most rented movies:"]
        for i, r in enumerate(results, 1):
            response.append(f"{i}. {r['title']} ({r['rental_count']} rentals)")
        return "\n".join(response)
    
    if "category" in question.lower():
        response = [f"Movies in the {results[0]['category']} category:"]
        for r in results:
            response.append(f"- {r['title']} ({r['release_year']}, {r['rating']})")
        return "\n".join(response)
    
    if "rented" in question.lower():
        response = []
        for r in results:
            response.append(f"{r['first_name']} {r['last_name']} rented it on {r['rental_date']}")
        return "\n".join(response)
    
    return str(results)

def interactive_mode():
    """Interactive mode for the DVD rental database assistant."""
    params = config.config(section='local')
    recovery_helper = QueryRecoveryHelper(params)
    
    print("\n=== DVD Rental Database Assistant ===")
    print("Type 'quit' or 'exit' to end the session\n")
    print("Example questions:")
    print("1. What are the top 5 most rented movies?")
    print("2. Who rented 'BUCKET BROTHERHOOD'?")
    print("3. Show me movies in the Action category")
    print("4. What's the average rental duration?\n")

    while True:
        try:
            question = input("\nYour question: ").strip()
            if question.lower() in ['quit', 'exit']:
                print("\nGoodbye!")
                break

            print("\nThinking...\n")
            
            # Get query template and parameters
            sql_query, query_params = get_query_template(question)
            
            if sql_query:
                print("Generated SQL:", sql_query)
                print("\nExecuting query...\n")
                
                try:
                    conn = psycopg2.connect(**params)
                    cur = conn.cursor(cursor_factory=RealDictCursor)
                    
                    # Execute the query with parameters
                    cur.execute(sql_query, query_params)
                    results = cur.fetchall()
                    
                    if not results and len(query_params) > 0:
                        # Try fuzzy matching if exact match fails
                        print("\nNo exact matches found. Looking for similar titles...")
                        possible_values = recovery_helper.get_column_values('title', 'film')
                        similar = recovery_helper.find_similar_values(query_params[0], possible_values)
                        
                        if similar:
                            print("\nSimilar movie titles found:")
                            for title, score in similar:
                                print(f"  - {title} (similarity: {score}%)")
                            
                            # Try the closest match
                            closest_match = similar[0][0]
                            print(f"\nTrying with closest match: {closest_match}")
                            
                            # Update query params with the closest match
                            query_params = (closest_match,) + query_params[1:]
                            cur.execute(sql_query, query_params)
                            results = cur.fetchall()
                    
                    if results:
                        print("\nResponse:")
                        print(format_query_result(question, results))
                    else:
                        print("\nNo results found.")
                    
                    cur.close()
                    conn.close()
                    
                except Exception as e:
                    print(f"Error executing query: {str(e)}")
            else:
                print("I'm sorry, I don't understand that question yet. Please try one of the example questions.")
                
        except Exception as e:
            print(f"Error: {str(e)}")
            continue

if __name__ == "__main__":
    interactive_mode()

# To Account for multiple issues in the query:

# def test_query_recovery_multiple_issues():
#     """Test query recovery with multiple issues in the same query."""
    
#     params = config.config(section='local')
#     recovery_helper = QueryRecoveryHelper(params)
    
#     # Test case with multiple issues
#     test_cases = [
#         ("""
#         SELECT f.title, c.name, a.first_name 
#         FROM film f 
#         JOIN film_category fc ON f.film_id = fc.film_id 
#         JOIN category c ON fc.category_id = c.category_id 
#         JOIN film_actor fa ON f.film_id = fa.film_id
#         JOIN actor a ON fa.actor_id = a.actor_id
#         WHERE c.name = 'Sience Fiction'
#         AND f.title = 'Jurasic Park'
#         AND a.first_name = 'Jeniffer'
#         """, 
#         [
#             ("category.name", "Sience Fiction"),
#             ("film.title", "Jurasic Park"),
#             ("actor.first_name", "Jeniffer")
#         ])
#     ]
    
#     for test_query, field_issues in test_cases:
#         print("\nTesting query with multiple issues:")
#         print(test_query.strip())
#         print("-" * 50)
        
#         conn = None
#         try:
#             # First try the original query
#             conn = psycopg2.connect(**params)
#             cur = conn.cursor(cursor_factory=RealDictCursor)
#             cur.execute(test_query)
#             results = cur.fetchall()
            
#             if not results:
#                 raise Exception("No results found")
                
#         except Exception as e:
#             print(f"Query failed as expected: {str(e)}")
            
#             # Track all corrections needed
#             corrections = {}
#             recovered_query = test_query
            
#             # Process each issue
#             for field_path, search_term in field_issues:
#                 table, column = field_path.split('.')
                
#                 # Get possible values for this column
#                 cur = conn.cursor()
#                 cur.execute(f"SELECT DISTINCT {column} FROM {table}")
#                 possible_values = [str(row[0]) for row in cur.fetchall()]
                
#                 # Handle category special cases
#                 if table == 'category':
#                     search_variations = [
#                         search_term,
#                         search_term.replace(' ', '-'),
#                         search_term.replace('-', ' '),
#                         'Sci-Fi' if 'sci' in search_term.lower() else search_term,
#                         'Science Fiction' if 'sci' in search_term.lower() else search_term
#                     ]
                    
#                     best_similar = None
#                     best_score = 0
#                     for variation in search_variations:
#                         similar = recovery_helper.find_similar_values(variation, possible_values)
#                         if similar and similar[0][1] > best_score:
#                             best_similar = similar[0]
#                             best_score = similar[0][1]
                    
#                     if best_similar:
#                         similar = [(best_similar[0], best_similar[1])]
#                     else:
#                         similar = []
#                 else:
#                     similar = recovery_helper.find_similar_values(search_term, possible_values)
                
#                 if similar:
#                     print(f"\nFor {field_path}, found similar values:")
#                     for match, score in similar:
#                         print(f"  - {match} (similarity: {score}%)")
                    
#                     best_match = similar[0][0]
#                     corrections[search_term] = best_match
                    
#             # Apply all corrections to query
#             for original, corrected in corrections.items():
#                 recovered_query = recovered_query.replace(f"'{original}'", f"'{corrected}'")
#                 recovered_query = recovered_query.replace(f"'%{original}%'", f"'%{corrected}%'")
            
#             print("\nTrying recovered query with all corrections:")
#             print(recovered_query.strip())
            
#             try:
#                 cur = conn.cursor(cursor_factory=RealDictCursor)
#                 cur.execute(recovered_query)
#                 results = cur.fetchall()
#                 print("\nQuery executed successfully!")
#                 print("Results:")
#                 for row in results:
#                     print(row)
#             except Exception as e2:
#                 print(f"\nRecovered query failed: {str(e2)}")
        
#         finally:
#             if conn:
#                 conn.close()
