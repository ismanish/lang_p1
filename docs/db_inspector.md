# Database Inspector Module Documentation

## Overview
The `db_inspector.py` module provides database schema introspection capabilities for the DVD Rental Assistant. It uses SQLAlchemy to analyze the database structure and generate schema information for the AI model.

## Key Components

### 1. DVDRentalInspector Class
Main class that handles database inspection:
```python
class DVDRentalInspector:
    def __init__(self)
    def get_schema_for_prompt() -> str
    def get_table_stats() -> str
    def get_table_relationships() -> str
```

### 2. Core Features

#### Schema Introspection
- Table structure analysis
- Column information retrieval
- Foreign key relationship mapping
- Index information gathering

#### Statistics Generation
- Table row counts
- Data distribution analysis
- Column value statistics
- Relationship metrics

#### Relationship Mapping
- Foreign key detection
- Table dependencies
- Relationship cardinality
- Join path analysis

## Implementation Details

### 1. Schema Analysis
```python
def get_schema_for_prompt(self) -> str:
    """
    Generates a comprehensive schema description for the AI model.
    Includes:
    - Table names and descriptions
    - Column definitions and types
    - Primary and foreign keys
    - Constraints and indexes
    """
```

### 2. Table Statistics
```python
def get_table_stats(self) -> str:
    """
    Generates statistical information about tables:
    - Row counts
    - Data size
    - Update frequency
    - Common query patterns
    """
```

### 3. Relationship Analysis
```python
def get_table_relationships(self) -> str:
    """
    Maps relationships between tables:
    - Direct foreign key relationships
    - Indirect relationships
    - Join conditions
    - Cardinality information
    """
```

## Usage Examples

### Basic Schema Inspection
```python
inspector = DVDRentalInspector()
schema_info = inspector.get_schema_for_prompt()
print(schema_info)
```

### Getting Table Statistics
```python
inspector = DVDRentalInspector()
stats = inspector.get_table_stats()
print(stats)
```

## Technical Details

### Database Schema Components

#### Tables
- film
- customer
- rental
- inventory
- payment
- store
- staff
- address
- city
- country
- category
- language
- actor
- film_actor
- film_category

#### Key Relationships
1. film → inventory → rental → customer
2. film → film_category → category
3. film → film_actor → actor
4. customer → payment
5. store → staff → payment

### Schema Information Format
```text
Table: film
- film_id (PK): integer
- title: varchar(255)
- description: text
- release_year: integer
- language_id (FK): integer
- rental_duration: integer
- rental_rate: decimal
- length: integer
- replacement_cost: decimal
- rating: varchar(10)
- last_update: timestamp
```

## Integration with AI Model

### 1. Schema Context
- Used in SQL query generation
- Helps validate table/column references
- Guides join path selection

### 2. Statistical Context
- Influences query optimization
- Helps estimate result sizes
- Guides response formatting

### 3. Relationship Context
- Assists in join path selection
- Validates relationship traversal
- Optimizes query structure

## Performance Considerations

### Caching
1. Schema information caching
2. Statistics caching
3. Relationship map caching
4. Refresh strategies

### Optimization
1. Lazy loading of statistics
2. Incremental updates
3. Query result caching
4. Memory management

## Error Handling

### Common Issues
1. Database connection failures
2. Schema access permissions
3. Invalid table references
4. Statistics computation errors

### Recovery Strategies
1. Connection retry logic
2. Permission escalation
3. Default schema fallback
4. Error logging and reporting

## Future Enhancements

### 1. Advanced Features
- Schema change detection
- Real-time statistics updates
- Query pattern analysis
- Performance metrics

### 2. AI Integration
- Enhanced schema understanding
- Query optimization suggestions
- Relationship inference
- Data pattern recognition

### 3. Performance
- Distributed schema analysis
- Parallel statistics computation
- Incremental updates
- Memory optimization

## Development Guidelines

### Adding New Features
1. Schema analysis extensions
2. Statistical computations
3. Relationship mapping
4. Performance optimizations

### Testing
1. Unit tests for each component
2. Integration tests
3. Performance benchmarks
4. Error handling verification

## Maintenance

### Regular Tasks
1. Schema validation
2. Statistics updates
3. Cache management
4. Performance monitoring

### Monitoring
1. Schema changes
2. Query patterns
3. Performance metrics
4. Error rates
