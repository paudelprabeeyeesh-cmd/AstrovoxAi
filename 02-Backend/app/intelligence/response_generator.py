"""
Response Generator - Phase 2.9

Generates responses in multiple formats:
- Plain text
- Markdown
- Tables
- Code
- JSON
- HTML
- CSV
- Mermaid diagrams
- Mathematical notation (LaTeX)
- Charts
"""

from typing import Dict, List, Any, Optional
from enum import Enum
import json
import re


class ResponseFormat(Enum):
    """Supported response formats"""
    PLAIN_TEXT = "plain_text"
    MARKDOWN = "markdown"
    CODE = "code"
    JSON = "json"
    HTML = "html"
    CSV = "csv"
    TABLE = "table"
    MERMAID = "mermaid"
    LATEX = "latex"
    CHART = "chart"


class ResponseGenerator:
    """
    Generates and formats responses in multiple formats.
    Handles format detection, conversion, and optimization.
    """
    
    def __init__(self):
        self.format_detectors = {
            ResponseFormat.JSON: self._detect_json,
            ResponseFormat.CODE: self._detect_code,
            ResponseFormat.TABLE: self._detect_table,
            ResponseFormat.MERMAID: self._detect_mermaid,
            ResponseFormat.LATEX: self._detect_latex,
            ResponseFormat.CSV: self._detect_csv,
        }
    
    def generate_response(
        self,
        content: str,
        format: Optional[ResponseFormat] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a response in the specified format.
        
        Args:
            content: The raw content to format
            format: Desired format (auto-detected if None)
            context: Additional context for formatting
        
        Returns:
            Formatted response with metadata
        """
        # Auto-detect format if not specified
        if format is None:
            format = self.detect_format(content)
        
        # Format the content
        formatted_content = self.format_content(content, format, context)
        
        return {
            "content": formatted_content,
            "format": format.value,
            "raw_content": content,
            "metadata": self._get_format_metadata(format, content),
        }
    
    def detect_format(self, content: str) -> ResponseFormat:
        """
        Auto-detect the best format for the content.
        
        Args:
            content: The content to analyze
        
        Returns:
            Detected ResponseFormat
        """
        # Check each format detector
        for format, detector in self.format_detectors.items():
            if detector(content):
                return format
        
        # Default to markdown (it's a good general-purpose format)
        return ResponseFormat.MARKDOWN
    
    def _detect_json(self, content: str) -> bool:
        """Detect if content is JSON"""
        try:
            json.loads(content.strip())
            return True
        except:
            return False
    
    def _detect_code(self, content: str) -> bool:
        """Detect if content is code"""
        code_indicators = [
            "def ", "function ", "class ", "import ", "from ",
            "const ", "let ", "var ", "=>", "{", "}",
        ]
        content_lower = content.lower()
        return any(indicator in content for indicator in code_indicators)
    
    def _detect_table(self, content: str) -> bool:
        """Detect if content is a table"""
        # Check for markdown table syntax
        lines = content.strip().split("\n")
        if len(lines) >= 2:
            # Check for separator line
            if "|" in lines[0] and "|" in lines[1]:
                separator = lines[1].strip()
                if re.match(r"^\|?[\s\-:]+\|?$", separator):
                    return True
        return False
    
    def _detect_mermaid(self, content: str) -> bool:
        """Detect if content is a Mermaid diagram"""
        mermaid_keywords = [
            "graph TD", "graph LR", "flowchart TD", "sequenceDiagram",
            "classDiagram", "stateDiagram", "erDiagram", "gantt",
        ]
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in mermaid_keywords)
    
    def _detect_latex(self, content: str) -> bool:
        """Detect if content contains LaTeX"""
        latex_patterns = [
            r"\\[a-z]+\{", r"\$\$.*\$\$", r"\$.*\$",
            r"\\begin\{", r"\\end\{",
        ]
        for pattern in latex_patterns:
            if re.search(pattern, content):
                return True
        return False
    
    def _detect_csv(self, content: str) -> bool:
        """Detect if content is CSV"""
        lines = content.strip().split("\n")
        if len(lines) >= 2:
            # Check if all lines have similar comma-separated structure
            first_commas = lines[0].count(",")
            for line in lines[1:]:
                if line.count(",") != first_commas:
                    return False
            return True
        return False
    
    def format_content(
        self,
        content: str,
        format: ResponseFormat,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Format content according to the specified format.
        
        Args:
            content: Raw content
            format: Desired format
            context: Additional context
        
        Returns:
            Formatted content
        """
        if format == ResponseFormat.PLAIN_TEXT:
            return self._format_plain_text(content)
        elif format == ResponseFormat.MARKDOWN:
            return self._format_markdown(content)
        elif format == ResponseFormat.CODE:
            return self._format_code(content, context)
        elif format == ResponseFormat.JSON:
            return self._format_json(content)
        elif format == ResponseFormat.HTML:
            return self._format_html(content)
        elif format == ResponseFormat.CSV:
            return self._format_csv(content)
        elif format == ResponseFormat.TABLE:
            return self._format_table(content)
        elif format == ResponseFormat.MERMAID:
            return self._format_mermaid(content)
        elif format == ResponseFormat.LATEX:
            return self._format_latex(content)
        elif format == ResponseFormat.CHART:
            return self._format_chart(content, context)
        else:
            return content
    
    def _format_plain_text(self, content: str) -> str:
        """Format as plain text"""
        # Remove markdown formatting
        content = re.sub(r"[*_`#]", "", content)
        return content.strip()
    
    def _format_markdown(self, content: str) -> str:
        """Format as markdown"""
        # Ensure proper markdown structure
        lines = content.split("\n")
        formatted_lines = []
        
        for line in lines:
            # Ensure code blocks are properly formatted
            if line.strip().startswith("```"):
                formatted_lines.append(line)
            else:
                formatted_lines.append(line)
        
        return "\n".join(formatted_lines)
    
    def _format_code(self, content: str, context: Optional[Dict[str, Any]]) -> str:
        """Format as code block"""
        language = context.get("language", "python") if context else "python"
        return f"```{language}\n{content}\n```"
    
    def _format_json(self, content: str) -> str:
        """Format as JSON"""
        try:
            # Try to parse and pretty-print
            data = json.loads(content)
            return json.dumps(data, indent=2)
        except:
            # If not valid JSON, return as-is
            return content
    
    def _format_html(self, content: str) -> str:
        """Format as HTML"""
        # Basic HTML formatting
        html = f"<div class='response'>\n"
        lines = content.split("\n")
        for line in lines:
            if line.strip():
                html += f"  <p>{line}</p>\n"
        html += "</div>"
        return html
    
    def _format_csv(self, content: str) -> str:
        """Format as CSV"""
        # Ensure proper CSV formatting
        lines = content.split("\n")
        csv_lines = []
        for line in lines:
            # Quote fields if they contain commas
            fields = line.split(",")
            quoted_fields = [f'"{field.strip()}"' if "," in field else field.strip() for field in fields]
            csv_lines.append(",".join(quoted_fields))
        return "\n".join(csv_lines)
    
    def _format_table(self, content: str) -> str:
        """Format as markdown table"""
        lines = content.split("\n")
        if not lines:
            return content
        
        # If already a table, return as-is
        if self._detect_table(content):
            return content
        
        # Try to convert to table format
        # This is a simple conversion - in production, use proper table parsing
        return content
    
    def _format_mermaid(self, content: str) -> str:
        """Format as Mermaid diagram"""
        # Ensure mermaid code block
        if not content.strip().startswith("```mermaid"):
            return f"```mermaid\n{content}\n```"
        return content
    
    def _format_latex(self, content: str) -> str:
        """Format as LaTeX"""
        # Ensure proper LaTeX delimiters
        if "$$" not in content:
            # Try to wrap in display math
            return f"$$\n{content}\n$$"
        return content
    
    def _format_chart(self, content: str, context: Optional[Dict[str, Any]]) -> str:
        """Format as chart (placeholder - requires chart library)"""
        # This is a placeholder. In production, integrate with:
        # - Chart.js
        # - Plotly
        # - D3.js
        
        return f"```json\n{json.dumps({'type': 'chart', 'data': content}, indent=2)}\n```"
    
    def _get_format_metadata(self, format: ResponseFormat, content: str) -> Dict[str, Any]:
        """Get metadata about the formatted content"""
        metadata = {
            "format": format.value,
            "length": len(content),
            "line_count": len(content.split("\n")),
        }
        
        if format == ResponseFormat.JSON:
            try:
                data = json.loads(content)
                metadata["json_keys"] = list(data.keys()) if isinstance(data, dict) else None
                metadata["json_type"] = type(data).__name__
            except:
                pass
        
        return metadata
    
    def convert_format(
        self,
        content: str,
        from_format: ResponseFormat,
        to_format: ResponseFormat,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Convert content from one format to another.
        
        Args:
            content: Content in source format
            from_format: Source format
            to_format: Target format
            context: Additional context
        
        Returns:
            Converted content
        """
        # First, normalize to plain text
        if from_format != ResponseFormat.PLAIN_TEXT:
            plain_content = self.format_content(content, ResponseFormat.PLAIN_TEXT)
        else:
            plain_content = content
        
        # Then, format to target
        return self.format_content(plain_content, to_format, context)
    
    def supports_format(self, format: ResponseFormat) -> bool:
        """Check if a format is supported"""
        return format in ResponseFormat
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported formats"""
        return [f.value for f in ResponseFormat]
