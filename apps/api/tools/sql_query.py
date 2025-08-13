"""SQL Query Tool Module.
Provides SQL query execution functionality with JSON Schema validation,
Pydantic models, and guardrails for timeout and security limits.
"""
import asyncio
import sqlite3
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
import logging
import tempfile
import os

logger = logging.getLogger(__name__)

# Configuration constants for guardrails
MAX_QUERY_LENGTH = 5000  # characters
QUERY_TIMEOUT = 30.0  # seconds
MAX_RESULT_ROWS = 1000
MAX_RESPONSE_SIZE = 5 * 1024 * 1024  # 5MB

# Restricted SQL operations for security
RESTRICTED_OPERATIONS = {
    'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE',
    'GRANT', 'REVOKE', 'EXEC', 'EXECUTE', 'CALL'
}

# JSON Schema for SQL query tool
SQL_QUERY_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "SQL query to execute",
            "maxLength": MAX_QUERY_LENGTH
        },
        "database_url": {
            "type": "string",
            "description": "Database connection URL or file path",
            "default": ":memory:"
        },
        "max_rows": {
            "type": "integer",
            "description": "Maximum number of rows to return",
            "minimum": 1,
            "maximum": MAX_RESULT_ROWS,
            "default": 100
        },
        "read_only": {
            "type": "boolean",
            "description": "Execute in read-only mode (SELECT only)",
            "default": True
        }
    },
    "required": ["query"],
    "additionalProperties": False
}

class SQLQueryRequest(BaseModel):
    """Pydantic model for SQL query requests."""
    
    query: str = Field(
        ...,
        description="SQL query to execute",
        max_length=MAX_QUERY_LENGTH
    )
    database_url: str = Field(
        default=":memory:",
        description="Database connection URL or file path"
    )
    max_rows: int = Field(
        default=100,
        description="Maximum number of rows to return",
        ge=1,
        le=MAX_RESULT_ROWS
    )
    read_only: bool = Field(
        default=True,
        description="Execute in read-only mode (SELECT only)"
    )
    
    @validator('query')
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError("Query cannot be empty")
        
        query_upper = v.upper().strip()
        
        # Check for restricted operations in read-only mode
        for operation in RESTRICTED_OPERATIONS:
            if query_upper.startswith(operation) or f" {operation} " in query_upper:
                raise ValueError(f"Operation '{operation}' not allowed")
                
        return v.strip()

class SQLQueryResult(BaseModel):
    """Pydantic model for SQL query results."""
    
    columns: List[str] = Field(
        default=[],
        description="Column names"
    )
    rows: List[List[Any]] = Field(
        default=[],
        description="Query result rows"
    )
    row_count: int = Field(
        default=0,
        description="Number of rows returned"
    )
    execution_time: float = Field(
        ...,
        description="Query execution time in seconds"
    )
    
class SQLQueryResponse(BaseModel):
    """Pydantic model for SQL query responses."""
    
    success: bool = Field(
        ...,
        description="Whether query execution was successful"
    )
    result: Optional[SQLQueryResult] = Field(
        None,
        description="Query results if successful"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if execution failed"
    )
    query: str = Field(
        ...,
        description="Original SQL query"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Query execution timestamp"
    )
    
class SQLQueryTool:
    """SQL query tool implementation with guardrails."""
    
    def __init__(self):
        self.temp_db_path = None
        
    async def execute_query(self, request: SQLQueryRequest) -> SQLQueryResponse:
        """Execute SQL query with guardrails.
        
        Args:
            request: SQL query request parameters
            
        Returns:
            SQLQueryResponse: Query results and metadata
            
        Raises:
            ValueError: If request validation fails
            TimeoutError: If query times out
        """
        try:
            # Validate request
            if not isinstance(request, SQLQueryRequest):
                request = SQLQueryRequest(**request)
                
            logger.info(f"Executing SQL query: {request.query[:100]}...")
            
            # Execute query with timeout
            result = await self._execute_with_timeout(request)
            
            return SQLQueryResponse(
                success=True,
                result=result,
                query=request.query
            )
            
        except asyncio.TimeoutError:
            logger.error("SQL query timed out")
            return SQLQueryResponse(
                success=False,
                error=f"Query timed out after {QUERY_TIMEOUT}s",
                query=request.query
            )
        except ValueError as e:
            logger.error(f"SQL query validation failed: {str(e)}")
            return SQLQueryResponse(
                success=False,
                error=f"Validation error: {str(e)}",
                query=request.query
            )
        except Exception as e:
            logger.error(f"SQL query execution failed: {str(e)}")
            return SQLQueryResponse(
                success=False,
                error=f"Execution error: {str(e)}",
                query=request.query
            )
            
    async def _execute_with_timeout(self, request: SQLQueryRequest) -> SQLQueryResult:
        """Execute query with timeout protection."""
        start_time = asyncio.get_event_loop().time()
        
        # Use asyncio.wait_for to enforce timeout
        try:
            return await asyncio.wait_for(
                self._execute_query_sync(request),
                timeout=QUERY_TIMEOUT
            )
        except asyncio.TimeoutError:
            raise TimeoutError("Query execution timed out")
            
    async def _execute_query_sync(self, request: SQLQueryRequest) -> SQLQueryResult:
        """Execute SQL query synchronously.
        
        This is a mock implementation using SQLite.
        In production, integrate with actual database drivers.
        """
        start_time = asyncio.get_event_loop().time()
        
        # Create temporary database with sample data for demonstration
        if request.database_url == ":memory:":
            conn = sqlite3.connect(":memory:")
            await self._setup_sample_data(conn)
        else:
            # For file databases, create if not exists
            conn = sqlite3.connect(request.database_url)
            
        try:
            cursor = conn.cursor()
            
            # Execute query
            cursor.execute(request.query)
            
            # Fetch results
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchmany(request.max_rows)
                
                # Convert to serializable format
                serializable_rows = []
                for row in rows:
                    serializable_row = []
                    for item in row:
                        if isinstance(item, (bytes, bytearray)):
                            serializable_row.append(str(item))
                        else:
                            serializable_row.append(item)
                    serializable_rows.append(serializable_row)
                    
                execution_time = asyncio.get_event_loop().time() - start_time
                
                return SQLQueryResult(
                    columns=columns,
                    rows=serializable_rows,
                    row_count=len(serializable_rows),
                    execution_time=execution_time
                )
            else:
                # Non-SELECT query (shouldn't reach here in read-only mode)
                execution_time = asyncio.get_event_loop().time() - start_time
                return SQLQueryResult(
                    columns=[],
                    rows=[],
                    row_count=0,
                    execution_time=execution_time
                )
                
        finally:
            conn.close()
            
    async def _setup_sample_data(self, conn):
        """Setup sample data for demonstration."""
        cursor = conn.cursor()
        
        # Create sample tables
        cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            age INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            product TEXT NOT NULL,
            amount DECIMAL(10,2),
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)
        
        # Insert sample data
        sample_users = [
            (1, 'Alice Johnson', 'alice@example.com', 28),
            (2, 'Bob Smith', 'bob@example.com', 35),
            (3, 'Carol Davis', 'carol@example.com', 42),
            (4, 'David Wilson', 'david@example.com', 29),
            (5, 'Eve Brown', 'eve@example.com', 31)
        ]
        
        cursor.executemany(
            "INSERT INTO users (id, name, email, age) VALUES (?, ?, ?, ?)",
            sample_users
        )
        
        sample_orders = [
            (1, 1, 'Laptop', 999.99),
            (2, 1, 'Mouse', 29.99),
            (3, 2, 'Keyboard', 79.99),
            (4, 3, 'Monitor', 299.99),
            (5, 2, 'Headphones', 149.99),
            (6, 4, 'Webcam', 89.99),
            (7, 5, 'Speakers', 199.99)
        ]
        
        cursor.executemany(
            "INSERT INTO orders (id, user_id, product, amount) VALUES (?, ?, ?, ?)",
            sample_orders
        )
        
        conn.commit()
    
    def __del__(self):
        # Clean up temporary database if created
        if self.temp_db_path and os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)
            
# Convenience function for direct usage
async def execute_sql_query(query: str, **kwargs) -> SQLQueryResponse:
    """Convenience function for SQL query execution.
    
    Args:
        query: SQL query to execute
        **kwargs: Additional query parameters
        
    Returns:
        SQLQueryResponse: Query results
    """
    request = SQLQueryRequest(query=query, **kwargs)
    
    tool = SQLQueryTool()
    try:
        return await tool.execute_query(request)
    finally:
        del tool
        
if __name__ == "__main__":
    # Simple test
    import asyncio
    
    async def test_query():
        # Test basic SELECT query
        result = await execute_sql_query(
            "SELECT name, email, age FROM users WHERE age > 30 ORDER BY age"
        )
        
        print(f"Success: {result.success}")
        if result.success:
            print(f"Columns: {result.result.columns}")
            print(f"Rows returned: {result.result.row_count}")
            print(f"Execution time: {result.result.execution_time:.3f}s")
            for row in result.result.rows:
                print(f"  {row}")
        else:
            print(f"Error: {result.error}")
            
        # Test JOIN query
        result2 = await execute_sql_query("""
        SELECT u.name, u.email, o.product, o.amount 
        FROM users u 
        JOIN orders o ON u.id = o.user_id 
        WHERE o.amount > 100
        ORDER BY o.amount DESC
        """)
        
        print(f"\nJoin query success: {result2.success}")
        if result2.success:
            print(f"Rows returned: {result2.result.row_count}")
            for row in result2.result.rows:
                print(f"  {row}")
                
    asyncio.run(test_query())
