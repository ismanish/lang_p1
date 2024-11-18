# PostgreSQL and DVD Rental Database Setup Guide

## Table of Contents
1. [Installing PostgreSQL](#installing-postgresql)
2. [Setting Up PostgreSQL](#setting-up-postgresql)
3. [Installing DVD Rental Sample Database](#installing-dvd-rental-sample-database)
4. [Configuring Database Connection](#configuring-database-connection)
5. [Troubleshooting](#troubleshooting)

## Installing PostgreSQL

### On macOS using Homebrew
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install PostgreSQL
brew install postgresql@15

# Start PostgreSQL service
brew services start postgresql@15
```

### On macOS using Postgres.app
1. Download Postgres.app from https://postgresapp.com/
2. Move to Applications folder
3. Double click to start
4. Click "Initialize" to create a new server

## Setting Up PostgreSQL

### 1. Initial Setup
```bash
# Create default user and database
createuser -s postgres
createdb postgres

# Set password for postgres user
psql -U postgres
postgres=# \password
Enter new password: your_password
Enter it again: your_password
```

### 2. Verify Installation
```bash
# Check PostgreSQL version
psql --version

# Connect to PostgreSQL
psql -U postgres

# Basic PostgreSQL commands
postgres=# \l          # List all databases
postgres=# \du         # List all users
postgres=# \q          # Quit psql
```

### 3. Configure PostgreSQL (if needed)
Edit postgresql.conf (location varies by installation method):
```bash
# For Homebrew installation
vim /usr/local/var/postgresql@15/postgresql.conf

# For Postgres.app
vim ~/Library/Application Support/Postgres/var/postgresql.conf
```

Common settings to adjust:
```ini
listen_addresses = '*'          # Listen on all available IP addresses
max_connections = 100          # Maximum concurrent connections
shared_buffers = 128MB         # Memory for caching
```

## Installing DVD Rental Sample Database

### 1. Download Sample Database
```bash
# Create a directory for the download
mkdir -p ~/Downloads/dvdrental
cd ~/Downloads/dvdrental

# Download the DVD Rental sample database
curl -O https://www.postgresqltutorial.com/wp-content/uploads/2019/05/dvdrental.zip

# Unzip the file
unzip dvdrental.zip
```

### 2. Create and Restore Database
```bash
# Create new database
createdb -U postgres dvdrental

# Restore the database using pg_restore
pg_restore -U postgres -d dvdrental dvdrental.tar
```

### 3. Verify Database Restoration
```bash
# Connect to the dvdrental database
psql -U postgres -d dvdrental

# Check tables
dvdrental=# \dt

# Sample query to verify data
dvdrental=# SELECT COUNT(*) FROM film;
```

## Configuring Database Connection

### 1. Create database.ini
Create a new file `database.ini` in your project root:
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

### 2. Set File Permissions
```bash
# Restrict access to database.ini
chmod 600 database.ini

# Ensure it's not tracked in git
echo "database.ini" >> .gitignore
```

### 3. Install Python Dependencies
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install required packages
pip install psycopg2-binary sqlalchemy python-dotenv
```

### 4. Test Database Connection
Create a test script `test_connection.py`:
```python
import psycopg2
from config import config

def test_connection():
    try:
        params = config()
        print('Connecting to PostgreSQL database...')
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        print('PostgreSQL database version:')
        cur.execute('SELECT version()')
        db_version = cur.fetchone()
        print(db_version)
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
            print('Database connection closed.')

if __name__ == '__main__':
    test_connection()
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Connection Refused
```bash
# Check if PostgreSQL is running
brew services list
# or for Postgres.app
ps aux | grep postgres

# Restart PostgreSQL
brew services restart postgresql@15
```

#### 2. Permission Denied
```bash
# Check user permissions
psql -U postgres -c "\du"

# Grant necessary permissions
psql -U postgres
postgres=# ALTER USER postgres WITH SUPERUSER;
```

#### 3. Database Does Not Exist
```bash
# List all databases
psql -U postgres -l

# Create database if missing
createdb -U postgres dvdrental
```

#### 4. Port Conflicts
```bash
# Check what's using PostgreSQL port
sudo lsof -i :5432

# Change PostgreSQL port in postgresql.conf
port = 5433  # or another available port
```

### Verification Queries
Test your DVD Rental database with these queries:
```sql
-- Check number of films
SELECT COUNT(*) FROM film;

-- Check number of customers
SELECT COUNT(*) FROM customer;

-- Check rental data
SELECT COUNT(*) FROM rental;

-- Test a join
SELECT f.title, COUNT(r.rental_id) as rental_count
FROM film f
JOIN inventory i ON f.film_id = i.film_id
JOIN rental r ON i.inventory_id = r.inventory_id
GROUP BY f.title
ORDER BY rental_count DESC
LIMIT 5;
```

### Backup and Restore
```bash
# Create backup
pg_dump -U postgres -d dvdrental > dvdrental_backup.sql

# Restore from backup
psql -U postgres -d dvdrental < dvdrental_backup.sql
```

## Additional Resources

### PostgreSQL Documentation
- [Official PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [psql Command Line Tool](https://www.postgresql.org/docs/current/app-psql.html)
- [PostgreSQL Tutorial](https://www.postgresqltutorial.com/)

### Sample Database Information
- [DVD Rental Database Schema](https://www.postgresqltutorial.com/postgresql-sample-database/)
- [Database Diagram](https://www.postgresqltutorial.com/wp-content/uploads/2018/03/dvd-rental-sample-database-diagram.png)

### Tools
- [pgAdmin](https://www.pgadmin.org/) - PostgreSQL administration tool
- [DBeaver](https://dbeaver.io/) - Universal database tool
- [Postico](https://eggerapps.at/postico/) - PostgreSQL client for macOS
