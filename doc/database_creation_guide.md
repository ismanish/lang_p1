# PostgreSQL DVD Rental Database Creation Guide

## Overview
This documentation explains the `create_postgres_rental_db.py` script, which creates and populates a PostgreSQL database with the Pagila (DVD rental) sample dataset. The script handles database creation, schema setup, and data import using a configuration-based approach.

## Configuration Management (database.ini)

### Purpose of database.ini
The `database.ini` file is a configuration file that stores database connection parameters. It uses the INI format, which is easy to read and modify. The file supports multiple environments (e.g., local, cloud) with different connection parameters.

### Structure of database.ini
```ini
[local]
host = localhost
database = dvdrental
user = manishsingh
password = 

[cloud]  # (Optional) For future cloud deployment
host = your-cloud-host
database = dvdrental
user = your-cloud-user
password = your-cloud-password
```

### Configuration Management Functions

#### 1. create_config()
```python
def create_config():
    """Create a configuration file for database connection."""
```
- Creates a new `database.ini` file if it doesn't exist
- Sets up default configuration for local PostgreSQL connection
- Can be extended to include cloud or other environment configurations
- Automatically called if `database.ini` is missing

#### 2. get_config(env='local')
```python
def get_config(env='local'):
    """Read database connection parameters."""
```
- Reads and parses the `database.ini` file
- Returns connection parameters for the specified environment
- Creates default configuration if file doesn't exist
- Validates environment existence in configuration

## Core Functionality

### 1. SQL File Execution (execute_sql_file)
```python
def execute_sql_file(cursor, sql_content, user):
    """Execute SQL statements from a file content."""
```
This function handles:
- PostgreSQL function definitions with dollar-quoted strings (`$$`, `$_$`)
- COPY statements for data import
- User ownership transfers
- Statement parsing and execution
- Error handling for each SQL statement

Special features:
- Preserves multi-line function definitions
- Handles COPY FROM STDIN operations
- Maintains proper SQL statement context
- Provides detailed error reporting

### 2. Database Creation (create_database)
```python
def create_database(config):
    """Create and populate the PostgreSQL database with Sakila data."""
```
Steps:
1. Connects to PostgreSQL server
2. Drops existing database if present
3. Creates new database
4. Downloads schema SQL from Pagila repository
5. Executes schema creation
6. Downloads and imports data
7. Handles all database operations with proper connection management

### 3. Statistics Reporting (print_database_stats)
```python
def print_database_stats(config):
    """Print statistics about the database."""
```
Features:
- Connects to the created database
- Queries record counts for all tables
- Handles transaction rollback on errors
- Provides clear statistical output

## Database Schema Overview

The script creates the following tables:
1. `actor` - Store actor information
2. `category` - Movie categories
3. `film` - Movie information
4. `film_actor` - Mapping between films and actors
5. `film_category` - Mapping between films and categories
6. `language` - Available languages
7. `country` - Country information
8. `city` - City information
9. `address` - Address information
10. `store` - Store information
11. `staff` - Staff member information
12. `customer` - Customer information
13. `inventory` - Inventory tracking
14. `rental` - Rental records
15. `payment` - Payment records

## Usage

### Command Line Interface
```bash
python create_postgres_rental_db.py <environment>
```
Example:
```bash
python create_postgres_rental_db.py local
```

### Error Handling
The script includes comprehensive error handling for:
- Configuration issues
- Database connection problems
- SQL execution errors
- Data import issues
- Transaction management

### Security Considerations
1. Passwords are stored in `database.ini` (should be properly secured)
2. User permissions are handled during database creation
3. Supports different users for different environments

## Data Import Process

### Schema Creation
1. Downloads schema SQL from Pagila GitHub repository
2. Processes and executes CREATE TABLE statements
3. Creates necessary functions and triggers
4. Sets up proper ownership and permissions

### Data Import
1. Downloads data SQL from Pagila repository
2. Processes COPY statements for bulk data import
3. Maintains data integrity during import
4. Handles special characters and formatting

## Performance Considerations

1. Uses COPY for efficient bulk data loading
2. Manages transactions appropriately
3. Handles large SQL statements properly
4. Provides progress feedback during long operations

## Troubleshooting

Common issues and solutions:
1. Database connection failures
   - Verify PostgreSQL is running
   - Check credentials in database.ini
   - Ensure proper permissions

2. Schema creation errors
   - Check PostgreSQL version compatibility
   - Verify user permissions
   - Review error messages in output

3. Data import issues
   - Ensure proper encoding
   - Check disk space
   - Verify table structures

## Maintenance

To maintain the database:
1. Regularly backup the database
2. Update configuration as needed
3. Monitor database size and performance
4. Keep PostgreSQL version compatible

## Future Enhancements

Potential improvements:
1. Add cloud deployment support
2. Implement data validation
3. Add incremental updates
4. Include more robust error recovery
5. Add database backup functionality
