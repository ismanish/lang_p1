# Fuzzy Matching System - Detailed Explanation

## Overview
The fuzzy matching system in `query_error_recovery.py` uses multiple strategies to find similar values when an exact match isn't found. It's particularly useful for handling:
- Misspelled movie titles
- Incorrect category names
- Partial matches
- Case-insensitive matches

## Code Breakdown

### 1. Main Fuzzy Matching Function
```python
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
```

## Matching Strategies Explained

### 1. Token-Based Matching
```python
value_tokens = set(value.split())
pv_tokens = set(pv.split())
if value_tokens.intersection(pv_tokens):
    score = fuzz.token_sort_ratio(value, pv)
```

This strategy:
1. Splits strings into individual words (tokens)
2. Checks if any tokens match exactly
3. If yes, calculates a similarity score

Example:
```python
Input: "Star Warz"
Tokens: {"STAR", "WARZ"}
Database: "Star Wars"
Tokens: {"STAR", "WARS"}
Result: Match found because "STAR" is common
```

### 2. Multiple Fuzzy Algorithms

#### a. Simple Ratio
```python
ratio = fuzz.ratio(value, pv)
```
Calculates character-by-character similarity.

Example:
```python
value1 = "Jurasic Park"
value2 = "Jurassic Park"
ratio = 94  # High score because only one character different
```

#### b. Partial Ratio
```python
partial_ratio = fuzz.partial_ratio(value, pv)
```
Finds best matching substring.

Example:
```python
value1 = "Star Wars: A New Hope"
value2 = "Star Wars"
partial_ratio = 100  # Perfect substring match
```

#### c. Token Sort Ratio
```python
token_sort = fuzz.token_sort_ratio(value, pv)
```
Sorts words before comparing.

Example:
```python
value1 = "Wars Star"
value2 = "Star Wars"
token_sort = 100  # Perfect match after sorting
```

#### d. Token Set Ratio
```python
token_set = fuzz.token_set_ratio(value, pv)
```
Compares unique sets of words.

Example:
```python
value1 = "The Star Wars Movie"
value2 = "Star Wars"
token_set = 100  # Perfect match for common words
```

## Real Examples from DVD Database

### Example 1: Misspelled Movie Title
```python
Input Query: "SELECT * FROM film WHERE title = 'Jurasic Park'"
Actual Title: "Jurassic Park"

Process:
1. Simple Ratio: 94 (one character difference)
2. Token Sort: 94 (words in same order)
3. Best Match Selected: "Jurassic Park"
```

### Example 2: Category Search
```python
Input Query: "SELECT * FROM category WHERE name = 'SciFi'"
Actual Category: "Science Fiction"

Process:
1. Token Match: No exact token match
2. Partial Ratio: 80 (Sci matches)
3. Special Case: Added variations ["Sci-Fi", "Science Fiction"]
4. Best Match Selected: "Science Fiction"
```

### Example 3: Word Order Variation
```python
Input Query: "SELECT * FROM film WHERE title = 'Wars Star'"
Actual Title: "Star Wars"

Process:
1. Token Sort Ratio: 100 (perfect match after sorting)
2. Simple Ratio: 67 (different order)
3. Best Match Selected: "Star Wars"
```

## Threshold and Scoring

```python
threshold: float = 50  # Default threshold
```

Score meanings:
- 100: Perfect match
- 90+: Very close match (e.g., one character different)
- 70-89: Good match (e.g., minor variations)
- 50-69: Possible match (needs verification)
- <50: Rejected as too different

## Usage in Recovery Process

```python
# Example from test1.py
test_cases = [
    ("""
    SELECT f.title, f.description 
    FROM film f 
    WHERE f.title = 'Jurasic Park'
    """, "film.title", "Jurasic Park")
]

# Recovery process
similar = recovery_helper.find_similar_values(search_term, possible_values)
if similar:
    best_match = similar[0][0]  # Get highest scoring match
    recovered_query = test_query.replace(
        f"'{search_term}'",
        f"'{best_match}'"
    )
```

## Performance Optimization

1. Caching of Values:
```python
def get_column_values(self, column_name: str, table_name: str) -> List[str]:
    cache_key = f"{table_name}.{column_name}"
    if cache_key in self.cache:
        return self.cache[cache_key]
```

2. Early Exit on Token Match:
```python
if exact_matches:
    return sorted(exact_matches, key=lambda x: x[1], reverse=True)
```

3. Limited Results:
```python
return sorted(matches, key=lambda x: x[1], reverse=True)[:5]  # Only top 5 matches
```
