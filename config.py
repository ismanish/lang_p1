from configparser import ConfigParser

def config(filename='database.ini', section='local'):
    """Read database configuration from file."""
    # Create a parser
    parser = ConfigParser()
    # Read config file
    parser.read(filename)

    # Get section
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception(f'Section {section} not found in {filename}')

    return db
