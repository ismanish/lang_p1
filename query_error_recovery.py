from typing import Dict, List, Any, Optional, Tuple
import difflib
import psycopg2
from psycopg2.extras import RealDictCursor
from langchain.schema import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
import re
from fuzzywuzzy import fuzz, process

class QueryRecoveryHelper:
    def __init__(self, db_config):
        self.db_config = db_config
        self.max_attempts = 3
        self.cache = {}  # Cache for column values

    def get_column_values(self, column_name: str, table_name: str) -> List[str]:
        """Get all unique values for a specific column with caching."""
        cache_key = f"{table_name}.{column_name}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor()
            cur.execute(f"SELECT DISTINCT {column_name} FROM {table_name} WHERE {column_name} IS NOT NULL")
            values = [str(row[0]) for row in cur.fetchall()]
            cur.close()
            conn.close()
            self.cache[cache_key] = values
            return values
        except Exception as e:
            print(f"Error fetching values for {column_name}: {str(e)}")
            return []

    def find_similar_values(self, value: str, possible_values: List[str], threshold: float = 50) -> List[Tuple[str, int]]:
        """Find similar values using fuzzy matching with fuzzywuzzy."""
        if not value or not possible_values:
            return []

        # Normalize input value and possible values
        value = value.upper()
        possible_values = [str(v).upper() for v in possible_values]

        # Try exact token matching first
        value_tokens = set(value.split())
        exact_matches = []
        for pv in possible_values:
            pv_tokens = set(pv.split())
            if value_tokens.intersection(pv_tokens):
                score = fuzz.token_sort_ratio(value, pv)
                if score >= threshold:
                    exact_matches.append((pv, score))

        if exact_matches:
            return sorted(exact_matches, key=lambda x: x[1], reverse=True)

        # Use multiple fuzzy matching strategies
        matches = []
        for pv in possible_values:
            # Try different fuzzy matching algorithms
            ratio = fuzz.ratio(value, pv)
            partial_ratio = fuzz.partial_ratio(value, pv)
            token_sort = fuzz.token_sort_ratio(value, pv)
            token_set = fuzz.token_set_ratio(value, pv)
            
            # Take the highest score
            best_score = max(ratio, partial_ratio, token_sort, token_set)
            if best_score >= threshold:
                matches.append((pv, best_score))

        return sorted(matches, key=lambda x: x[1], reverse=True)[:5]

    def extract_value_patterns(self, query: str) -> List[Tuple[str, str, str, str]]:
        """Extract patterns from query with context."""
        patterns = [
            # Basic equality patterns
            (r"(?:title|film\.title)\s*=\s*'([^']*)'", "film", "title", r"(?i)(?:where|and)\s+(?:\w+\.)?title\s*=\s*'[^']*'"),
            (r"(?:first_name|customer\.first_name)\s*=\s*'([^']*)'", "customer", "first_name", r"(?i)(?:where|and)\s+(?:\w+\.)?first_name\s*=\s*'[^']*'"),
            (r"(?:last_name|customer\.last_name)\s*=\s*'([^']*)'", "customer", "last_name", r"(?i)(?:where|and)\s+(?:\w+\.)?last_name\s*=\s*'[^']*'"),
            (r"(?:name|category\.name)\s*=\s*'([^']*)'", "category", "name", r"(?i)(?:where|and)\s+(?:\w+\.)?name\s*=\s*'[^']*'"),
            
            # LIKE patterns with wildcards
            (r"(?:title|film\.title)\s+LIKE\s+'%([^%]+)%'", "film", "title", r"(?i)(?:where|and)\s+(?:\w+\.)?title\s+LIKE\s+'%[^%]+%'"),
            (r"(?:first_name|customer\.first_name)\s+LIKE\s+'%([^%]+)%'", "customer", "first_name", r"(?i)(?:where|and)\s+(?:\w+\.)?first_name\s+LIKE\s+'%[^%]+%'"),
            (r"(?:last_name|customer\.last_name)\s+LIKE\s+'%([^%]+)%'", "customer", "last_name", r"(?i)(?:where|and)\s+(?:\w+\.)?last_name\s+LIKE\s+'%[^%]+%'"),
            (r"(?:name|category\.name)\s+LIKE\s+'%([^%]+)%'", "category", "name", r"(?i)(?:where|and)\s+(?:\w+\.)?name\s+LIKE\s+'%[^%]+%'"),
            
            # ILIKE patterns
            (r"(?:title|film\.title)\s+ILIKE\s+'%([^%]+)%'", "film", "title", r"(?i)(?:where|and)\s+(?:\w+\.)?title\s+ILIKE\s+'%[^%]+%'"),
            (r"(?:first_name|customer\.first_name)\s+ILIKE\s+'%([^%]+)%'", "customer", "first_name", r"(?i)(?:where|and)\s+(?:\w+\.)?first_name\s+ILIKE\s+'%[^%]+%'"),
            (r"(?:last_name|customer\.last_name)\s+ILIKE\s+'%([^%]+)%'", "customer", "last_name", r"(?i)(?:where|and)\s+(?:\w+\.)?last_name\s+ILIKE\s+'%[^%]+%'"),
            (r"(?:name|category\.name)\s+ILIKE\s+'%([^%]+)%'", "category", "name", r"(?i)(?:where|and)\s+(?:\w+\.)?name\s+ILIKE\s+'%[^%]+%'")
        ]
        
        found_patterns = []
        for pattern, table, column, context_pattern in patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                # Get the context around the match
                context_match = re.search(context_pattern, query)
                if context_match:
                    context = context_match.group(0)
                    found_patterns.append((match.group(1), table, column, context))
        
        return found_patterns

    def analyze_query_and_suggest(self, failed_query: str) -> Dict[str, List[Tuple[str, int]]]:
        """Analyze failed query and suggest similar values with confidence scores."""
        suggestions = {}
        
        # Extract values and their context from the query
        extracted_patterns = self.extract_value_patterns(failed_query)
        
        for value, table, column, context in extracted_patterns:
            possible_values = self.get_column_values(column, table)
            similar = self.find_similar_values(value, possible_values)
            
            if similar:
                key = f"{table}.{column}"
                suggestions[key] = {
                    'matches': similar,
                    'context': context,
                    'original': value
                }
        
        return suggestions

    def generate_recovery_query(self, failed_query: str, error_message: str, suggestions: Dict[str, Any]) -> str:
        """Generate a new query using suggestions."""
        if not suggestions:
            return failed_query

        recovered_query = failed_query
        for column_key, suggestion_data in suggestions.items():
            if suggestion_data['matches']:
                best_match, score = suggestion_data['matches'][0]
                original = suggestion_data['original']
                context = suggestion_data['context']
                
                # Replace in the specific context rather than globally
                recovered_query = recovered_query.replace(
                    f"'{original}'",
                    f"'{best_match}'"
                )
                
                # If using LIKE, adjust the pattern
                recovered_query = recovered_query.replace(
                    f"LIKE '%{original}%'",
                    f"LIKE '%{best_match}%'"
                )

        return recovered_query

    def recover_query(self, failed_query: str, error_message: str) -> Tuple[str, Dict[str, Any]]:
        """Main method to recover from query errors."""
        suggestions = self.analyze_query_and_suggest(failed_query)
        if suggestions:
            recovered_query = self.generate_recovery_query(failed_query, error_message, suggestions)
            return recovered_query, suggestions
        return failed_query, {}