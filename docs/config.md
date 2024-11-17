# Configuration Module Documentation

## Overview
The `config.py` module manages database configuration settings for the DVD Rental Assistant. It provides a secure and flexible way to handle database connection parameters using configuration files.

## Key Features

### 1. Configuration File Management
- Reads database configuration from `database.ini`
- Supports multiple configuration sections
- Secure credential management

### 2. Core Function

#### `config(filename='database.ini', section='postgresql')`
Reads and parses database configuration:
- **Parameters:**
  - `filename`: Path to configuration file (default: 'database.ini')
  - `section`: Configuration section to read (default: 'postgresql')
- **Returns:** Dictionary with database parameters
- **Raises:** Exception if section not found

### 3. Configuration Parameters
Standard parameters managed:
- `host`: Database host address
- `database`: Database name
- `user`: Database username
- `password`: Database password
- `port`: Database port (optional)

## Implementation Details

### Configuration File Format
```ini
[postgresql]
host=localhost
database=dvdrental
user=postgres
password=your_password

[local]
host=localhost
database=dvdrental
user=postgres
password=your_password
```

### Error Handling
- File not found errors
- Missing section errors
- Invalid parameter errors
- Permission issues

### Security Considerations
- No hardcoded credentials
- Secure file permissions
- Environment variable support
- Credential encryption support (future)

## Usage Examples

### Basic Usage
```python
from config import config

# Get default configuration
db_params = config()

# Get specific section
local_params = config(section='local')
```

### Error Handling Example
```python
try:
    params = config()
except Exception as e:
    print(f"Configuration error: {e}")
```

## Best Practices

### File Security
1. Restrict file permissions
2. Use environment variables for sensitive data
3. Keep backup configurations
4. Version control exclusion

### Configuration Management
1. Regular credential rotation
2. Environment-specific sections
3. Documentation of changes
4. Backup management

## Integration

### With Database Connection
```python
import psycopg2
from config import config

def connect():
    try:
        params = config()
        return psycopg2.connect(**params)
    except Exception as e:
        print(f"Connection error: {e}")
```

### With Environment Variables
```python
import os
from config import config

def get_config():
    params = config()
    # Override with environment variables if present
    if 'DB_PASSWORD' in os.environ:
        params['password'] = os.environ['DB_PASSWORD']
    return params
```

## Troubleshooting

### Common Issues
1. File permission problems
2. Missing configuration file
3. Invalid section names
4. Malformed configuration

### Solutions
1. Check file permissions
2. Verify file location
3. Review configuration format
4. Validate parameter names

## Future Enhancements
1. Configuration encryption
2. Multiple file support
3. Dynamic reloading
4. Validation schemas
5. Automated backup

## Development Guidelines

### Adding New Parameters
1. Update configuration file
2. Document new parameters
3. Add validation logic
4. Update error handling

### Testing
1. Unit test coverage
2. Configuration validation
3. Error case testing
4. Integration testing

## Maintenance

### Regular Tasks
1. Credential rotation
2. Permission checks
3. Backup verification
4. Documentation updates

### Monitoring
1. Access logging
2. Error tracking
3. Usage patterns
4. Security audits
