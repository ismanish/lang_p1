from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
import json
from typing import Dict, List, Any, Optional
import configparser
import os

class DVDRentalInspector:
    def __init__(self):
        """Initialize the schema inspector with database configuration from database.ini."""
        self.config = self._get_db_config()
        db_url = f"postgresql://{self.config['user']}:{self.config['password']}@{self.config['host']}/{self.config['database']}"
        self.engine = create_engine(db_url)
        self.inspector = inspect(self.engine)
        
    def _get_db_config(self) -> Dict[str, str]:
        """Read database configuration from database.ini."""
        config = configparser.ConfigParser()
        config.read('database.ini')
        return config['local']
    
    def get_schema_info(self) -> str:
        """Get comprehensive schema information including tables, columns, and relationships."""
        schema_info = []
        
        for table_name in self.inspector.get_table_names():
            table_info = [f"\nTable: {table_name}"]
            table_info.append("-" * (len(table_name) + 7))
            
            # Get columns
            table_info.append("Columns:")
            columns = self.inspector.get_columns(table_name)
            for col in columns:
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                table_info.append(f"  - {col['name']} ({str(col['type']).upper()}) {nullable}")
            
            # Get primary keys
            pk = self.inspector.get_pk_constraint(table_name)
            if pk['constrained_columns']:
                table_info.append(f"\nPrimary Key: {', '.join(pk['constrained_columns'])}")
            
            # Get foreign keys
            fks = self.inspector.get_foreign_keys(table_name)
            if fks:
                table_info.append("\nForeign Keys:")
                for fk in fks:
                    ref_table = fk['referred_table']
                    ref_cols = fk['referred_columns']
                    local_cols = fk['constrained_columns']
                    for local_col, ref_col in zip(local_cols, ref_cols):
                        table_info.append(f"  - {local_col} -> {ref_table}({ref_col})")
            
            schema_info.append("\n".join(table_info))
        
        return "\n\n".join(schema_info)
    
    def get_table_stats(self) -> str:
        """Get statistics about the tables including row counts and numeric column distributions."""
        stats = ["Table Statistics:\n"]
        
        with self.engine.connect() as conn:
            for table_name in self.inspector.get_table_names():
                # Get row count
                count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                row_count = conn.execute(count_query).scalar()
                
                table_stats = [f"\n{table_name}:"]
                table_stats.append(f"  Total Rows: {row_count}")
                
                # Get numeric column statistics
                columns = self.inspector.get_columns(table_name)
                numeric_stats = []
                
                for col in columns:
                    if str(col['type']).startswith(('INT', 'FLOAT', 'DECIMAL', 'NUMERIC')):
                        stats_query = text(f"""
                            SELECT 
                                MIN({col['name']}) as min_val,
                                MAX({col['name']}) as max_val,
                                AVG({col['name']}) as avg_val
                            FROM {table_name}
                            WHERE {col['name']} IS NOT NULL
                        """)
                        
                        result = conn.execute(stats_query).fetchone()
                        if result and any(x is not None for x in result):
                            numeric_stats.append(
                                f"    {col['name']}:\n"
                                f"      Min: {result[0]}\n"
                                f"      Max: {result[1]}\n"
                                f"      Avg: {result[2]:.2f}"
                            )
                
                if numeric_stats:
                    table_stats.append("  Numeric Column Statistics:")
                    table_stats.extend(numeric_stats)
                
                stats.append("\n".join(table_stats))
        
        return "\n".join(stats)

    def get_sample_data(self, limit: int = 3) -> Dict[str, List[Dict[str, Any]]]:
        """Get sample data from each table."""
        samples = {}
        with self.engine.connect() as conn:
            for table_name in self.inspector.get_table_names():
                query = text(f"SELECT * FROM {table_name} LIMIT :limit")
                result = conn.execute(query, {"limit": limit}).fetchall()
                if result:
                    samples[table_name] = [dict(row._mapping) for row in result]
        return samples

    def get_schema_for_prompt(self) -> str:
        """Get schema information formatted specifically for the LLM prompt."""
        schema_info = []
        
        for table_name in self.inspector.get_table_names():
            columns = [col['name'] for col in self.inspector.get_columns(table_name)]
            fks = self.inspector.get_foreign_keys(table_name)
            
            # Add table name and columns
            table_info = f"- {table_name} ({', '.join(columns)})"
            
            # Add relationships if any foreign keys exist
            if fks:
                relationships = []
                for fk in fks:
                    ref_table = fk['referred_table']
                    local_cols = fk['constrained_columns']
                    relationships.append(f"  Related to {ref_table} via {', '.join(local_cols)}")
                table_info += "\n" + "\n".join(relationships)
            
            schema_info.append(table_info)
        
        return "\n".join(schema_info)

def get_database_info() -> Dict[str, Any]:
    """Get comprehensive database information including schema, statistics, and sample data."""
    inspector = DVDRentalInspector()
    
    return {
        "schema": inspector.get_schema_info(),
        "stats": inspector.get_table_stats(),
        "samples": inspector.get_sample_data(),
        "prompt_schema": inspector.get_schema_for_prompt()
    }

if __name__ == "__main__":
    # Example usage
    info = get_database_info()
    print("\n=== Schema Information ===")
    print(info["schema"])
    print("\n=== Table Statistics ===")
    print(info["stats"])
    print("\n=== Schema for Prompt ===")
    print(info["prompt_schema"])
