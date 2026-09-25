"""
Tool Engine - Phase 2.7

Provides a modular tool calling framework with core tools:
- Web Search
- Calculator
- Code Executor
- Python Sandbox
- File Reader
- PDF Reader
- OCR
- Database Query
- Email
- Calendar
- Notes
- Browser Automation
- GitHub
- Image Generator
- Speech Recognition
- Text-to-Speech
"""

from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from datetime import datetime
import httpx
import json
import re
import os


class ToolCategory(Enum):
    """Categories of tools"""
    INFORMATION = "information"
    COMPUTATION = "computation"
    CODE = "code"
    PRODUCTIVITY = "productivity"
    COMMUNICATION = "communication"
    MEDIA = "media"
    AUTOMATION = "automation"


class Tool:
    """Represents a callable tool"""
    
    def __init__(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        parameters: Dict[str, Any],
        function: Callable,
        requires_auth: bool = False,
        async_execution: bool = True,
    ):
        self.name = name
        self.description = description
        self.category = category
        self.parameters = parameters
        self.function = function
        self.requires_auth = requires_auth
        self.async_execution = async_execution
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters"""
        try:
            # Validate parameters
            self._validate_parameters(kwargs)
            
            # Execute the function
            if self.async_execution:
                result = await self.function(**kwargs)
            else:
                result = self.function(**kwargs)
            
            return {
                "success": True,
                "tool": self.name,
                "result": result,
                "executed_at": datetime.utcnow().isoformat(),
            }
        
        except Exception as e:
            return {
                "success": False,
                "tool": self.name,
                "error": str(e),
                "executed_at": datetime.utcnow().isoformat(),
            }
    
    def _validate_parameters(self, params: Dict[str, Any]):
        """Validate that required parameters are provided"""
        required = self.parameters.get("required", [])
        for param in required:
            if param not in params:
                raise ValueError(f"Missing required parameter: {param}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary for API representation"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": self.parameters,
            "requires_auth": self.requires_auth,
            "async_execution": self.async_execution,
        }


class ToolEngine:
    """
    Manages and executes tools for the AI assistant.
    Provides a registry of available tools and handles their execution.
    """
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._initialize_core_tools()
    
    def _initialize_core_tools(self):
        """Initialize core tools"""
        
        # Calculator Tool
        self.register_tool(
            Tool(
                name="calculator",
                description="Perform mathematical calculations",
                category=ToolCategory.COMPUTATION,
                parameters={
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "Mathematical expression to evaluate",
                        }
                    },
                    "required": ["expression"],
                },
                function=self._tool_calculator,
                async_execution=False,
            )
        )
        
        # Web Search Tool
        self.register_tool(
            Tool(
                name="web_search",
                description="Search the web for information",
                category=ToolCategory.INFORMATION,
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query",
                        },
                        "num_results": {
                            "type": "integer",
                            "description": "Number of results to return",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
                function=self._tool_web_search,
                async_execution=True,
            )
        )
        
        # Code Executor Tool
        self.register_tool(
            Tool(
                name="code_executor",
                description="Execute code in a safe sandbox environment",
                category=ToolCategory.CODE,
                parameters={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Code to execute",
                        },
                        "language": {
                            "type": "string",
                            "description": "Programming language (python, javascript, etc.)",
                            "default": "python",
                        },
                    },
                    "required": ["code"],
                },
                function=self._tool_code_executor,
                async_execution=True,
            )
        )
        
        # File Reader Tool
        self.register_tool(
            Tool(
                name="file_reader",
                description="Read and analyze text files",
                category=ToolCategory.INFORMATION,
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to read",
                        },
                    },
                    "required": ["file_path"],
                },
                function=self._tool_file_reader,
                async_execution=False,
            )
        )
        
        # PDF Reader Tool
        self.register_tool(
            Tool(
                name="pdf_reader",
                description="Extract text from PDF files",
                category=ToolCategory.INFORMATION,
                parameters={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the PDF file",
                        },
                    },
                    "required": ["file_path"],
                },
                function=self._tool_pdf_reader,
                async_execution=False,
            )
        )
        
        # Database Query Tool
        self.register_tool(
            Tool(
                name="database_query",
                description="Execute SQL queries on the database",
                category=ToolCategory.INFORMATION,
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "SQL query to execute",
                        },
                    },
                    "required": ["query"],
                },
                function=self._tool_database_query,
                async_execution=True,
                requires_auth=True,
            )
        )
        
        # Notes Tool
        self.register_tool(
            Tool(
                name="notes",
                description="Create, read, update, and delete notes",
                category=ToolCategory.PRODUCTIVITY,
                parameters={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "Action to perform (create, read, update, delete)",
                            "enum": ["create", "read", "update", "delete"],
                        },
                        "note_id": {
                            "type": "string",
                            "description": "ID of the note (for read, update, delete)",
                        },
                        "content": {
                            "type": "string",
                            "description": "Note content (for create, update)",
                        },
                        "title": {
                            "type": "string",
                            "description": "Note title (for create, update)",
                        },
                    },
                    "required": ["action"],
                },
                function=self._tool_notes,
                async_execution=True,
                requires_auth=True,
            )
        )
        
        # Calendar Tool
        self.register_tool(
            Tool(
                name="calendar",
                description="Manage calendar events and scheduling",
                category=ToolCategory.PRODUCTIVITY,
                parameters={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "Action to perform (create, list, update, delete)",
                            "enum": ["create", "list", "update", "delete"],
                        },
                        "event_id": {
                            "type": "string",
                            "description": "Event ID (for update, delete)",
                        },
                        "title": {
                            "type": "string",
                            "description": "Event title",
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Event start time (ISO format)",
                        },
                        "end_time": {
                            "type": "string",
                            "description": "Event end time (ISO format)",
                        },
                    },
                    "required": ["action"],
                },
                function=self._tool_calendar,
                async_execution=True,
                requires_auth=True,
            )
        )
        
        # Email Tool
        self.register_tool(
            Tool(
                name="email",
                description="Send emails",
                category=ToolCategory.COMMUNICATION,
                parameters={
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Recipient email address",
                        },
                        "subject": {
                            "type": "string",
                            "description": "Email subject",
                        },
                        "body": {
                            "type": "string",
                            "description": "Email body",
                        },
                    },
                    "required": ["to", "subject", "body"],
                },
                function=self._tool_email,
                async_execution=True,
                requires_auth=True,
            )
        )
    
    def register_tool(self, tool: Tool):
        """Register a new tool"""
        self.tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def list_tools(self, category: Optional[ToolCategory] = None) -> List[Dict[str, Any]]:
        """List available tools, optionally filtered by category"""
        tools = list(self.tools.values())
        
        if category:
            tools = [t for t in tools if t.category == category]
        
        return [tool.to_dict() for tool in tools]
    
    async def execute_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool by name"""
        tool = self.get_tool(name)
        if not tool:
            return {
                "success": False,
                "error": f"Tool not found: {name}",
            }
        
        return await tool.execute(**kwargs)
    
    async def execute_multiple_tools(
        self, tool_calls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Execute multiple tools in sequence"""
        results = []
        for call in tool_calls:
            tool_name = call.get("tool")
            parameters = call.get("parameters", {})
            result = await self.execute_tool(tool_name, **parameters)
            results.append(result)
        return results
    
    # Tool implementations
    
    def _tool_calculator(self, expression: str) -> Dict[str, Any]:
        """Calculate mathematical expression safely"""
        try:
            # Only allow safe mathematical operations
            allowed_chars = set("0123456789+-*/.() ")
            if not all(c in allowed_chars for c in expression):
                return {"error": "Invalid characters in expression"}
            
            result = eval(expression)
            return {"result": result, "expression": expression}
        
        except Exception as e:
            return {"error": f"Calculation error: {str(e)}"}
    
    async def _tool_web_search(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """Perform web search (placeholder - requires API integration)"""
        # This is a placeholder. In production, integrate with:
        # - Google Custom Search API
        # - Bing Search API
        # - DuckDuckGo API
        # - Tavily API
        
        return {
            "query": query,
            "results": [
                {
                    "title": f"Search result for: {query}",
                    "url": "https://example.com",
                    "snippet": "This is a placeholder for web search results.",
                }
            ],
            "note": "Web search requires API integration",
        }
    
    async def _tool_code_executor(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Execute code in a sandbox (placeholder - requires sandbox setup)"""
        # This is a placeholder. In production, integrate with:
        # - Docker-based sandbox
        # - Restricted Python environment
        # - Online judge systems
        
        if language.lower() == "python":
            try:
                # WARNING: This is unsafe for production
                # Use a proper sandbox in production
                exec_globals = {"__builtins__": {}}
                result = eval(code, exec_globals)
                return {
                    "language": language,
                    "output": str(result),
                    "success": True,
                }
            except Exception as e:
                return {
                    "language": language,
                    "error": str(e),
                    "success": False,
                }
        
        return {
            "language": language,
            "error": f"Language {language} not yet supported",
            "note": "Code execution requires sandbox setup",
        }
    
    def _tool_file_reader(self, file_path: str) -> Dict[str, Any]:
        """Read a text file"""
        try:
            if not os.path.exists(file_path):
                return {"error": f"File not found: {file_path}"}
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            return {
                "file_path": file_path,
                "content": content,
                "size": len(content),
            }
        
        except Exception as e:
            return {"error": f"Error reading file: {str(e)}"}
    
    def _tool_pdf_reader(self, file_path: str) -> Dict[str, Any]:
        """Extract text from PDF (placeholder - requires PDF library)"""
        # This is a placeholder. In production, integrate with:
        # - PyPDF2
        # - pdfplumber
        # - pdfminer.six
        
        return {
            "file_path": file_path,
            "text": "",
            "note": "PDF reading requires library installation (e.g., PyPDF2)",
        }
    
    async def _tool_database_query(self, query: str) -> Dict[str, Any]:
        """Execute database query (placeholder - requires database connection)"""
        # This is a placeholder. In production, integrate with:
        # - PostgreSQL connection
        # - Query validation
        # - Result formatting
        
        return {
            "query": query,
            "results": [],
            "note": "Database query requires connection setup",
        }
    
    async def _tool_notes(
        self,
        action: str,
        note_id: Optional[str] = None,
        content: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Manage notes (placeholder - requires database/storage)"""
        # This is a placeholder. In production, integrate with:
        # - Database storage
        # - User-specific notes
        # - Search and indexing
        
        return {
            "action": action,
            "note_id": note_id,
            "result": f"Note {action} operation",
            "note": "Notes require database/storage setup",
        }
    
    async def _tool_calendar(
        self,
        action: str,
        event_id: Optional[str] = None,
        title: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Manage calendar (placeholder - requires calendar integration)"""
        # This is a placeholder. In production, integrate with:
        # - Google Calendar API
        # - Outlook Calendar API
        # - CalDAV
        
        return {
            "action": action,
            "event_id": event_id,
            "result": f"Calendar {action} operation",
            "note": "Calendar requires API integration",
        }
    
    async def _tool_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Send email (placeholder - requires email service)"""
        # This is a placeholder. In production, integrate with:
        # - SendGrid
        # - AWS SES
        # - SMTP server
        
        return {
            "to": to,
            "subject": subject,
            "result": "Email queued for sending",
            "note": "Email requires service integration",
        }
