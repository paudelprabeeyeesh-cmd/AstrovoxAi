"""
Citation and Traceability System - Phase 5.9

For knowledge-grounded answers, Astrovox should explain where the answer came from.
Each answer may include:
- File name
- Page number
- Section heading
- Source link
- Document excerpt
- Confidence score

This is especially important for education, medical information, law, business analysis, and research.
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field


class CitationType(Enum):
    """Types of citations"""
    DIRECT_QUOTE = "direct_quote"
    PARAPHRASE = "paraphrase"
    REFERENCE = "reference"
    CONCEPT = "concept"
    DATA = "data"


@dataclass
class Citation:
    """Represents a citation from a knowledge source"""
    citation_id: str
    source_id: str
    source_name: str
    source_type: str
    file_type: str
    page_number: Optional[int] = None
    section_heading: Optional[str] = None
    source_link: Optional[str] = None
    excerpt: str = ""
    citation_type: CitationType = CitationType.REFERENCE
    confidence: float = 1.0
    relevance: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class CitationSystem:
    """
    Manages citations and traceability for knowledge-grounded answers.
    Provides structured citation information and source attribution.
    """
    
    def __init__(self):
        self.citations: Dict[str, Citation] = {}
        self.next_citation_id = 1
        self.citation_links: Dict[str, List[str]] = {}  # answer_id -> citation_ids
    
    def create_citation(
        self,
        source_id: str,
        source_name: str,
        source_type: str,
        file_type: str,
        excerpt: str,
        page_number: Optional[int] = None,
        section_heading: Optional[str] = None,
        source_link: Optional[str] = None,
        citation_type: CitationType = CitationType.REFERENCE,
        confidence: float = 1.0,
        relevance: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new citation.
        
        Args:
            source_id: ID of the source document
            source_name: Name of the source
            source_type: Type of source (document, web, etc.)
            file_type: File type (pdf, docx, etc.)
            excerpt: Excerpt from the source
            page_number: Optional page number
            section_heading: Optional section heading
            source_link: Optional link to source
            citation_type: Type of citation
            confidence: Confidence in the citation
            relevance: Relevance to the answer
            metadata: Additional metadata
        
        Returns:
            Citation ID
        """
        citation_id = f"cite_{self.next_citation_id}"
        self.next_citation_id += 1
        
        citation = Citation(
            citation_id=citation_id,
            source_id=source_id,
            source_name=source_name,
            source_type=source_type,
            file_type=file_type,
            page_number=page_number,
            section_heading=section_heading,
            source_link=source_link,
            excerpt=excerpt,
            citation_type=citation_type,
            confidence=confidence,
            relevance=relevance,
            metadata=metadata or {},
        )
        
        self.citations[citation_id] = citation
        return citation_id
    
    def get_citation(self, citation_id: str) -> Optional[Citation]:
        """Get a citation by ID"""
        return self.citations.get(citation_id)
    
    def link_citations_to_answer(self, answer_id: str, citation_ids: List[str]):
        """Link citations to an answer"""
        self.citation_links[answer_id] = citation_ids
    
    def get_answer_citations(self, answer_id: str) -> List[Citation]:
        """Get all citations for an answer"""
        citation_ids = self.citation_links.get(answer_id, [])
        return [self.citations[cid] for cid in citation_ids if cid in self.citations]
    
    def format_citation(self, citation: Citation, format: str = "markdown") -> str:
        """
        Format a citation for display.
        
        Args:
            citation: Citation to format
            format: Format type (markdown, html, plain, academic)
        
        Returns:
            Formatted citation string
        """
        if format == "markdown":
            return self._format_markdown(citation)
        elif format == "html":
            return self._format_html(citation)
        elif format == "academic":
            return self._format_academic(citation)
        else:
            return self._format_plain(citation)
    
    def _format_markdown(self, citation: Citation) -> str:
        """Format citation in Markdown"""
        parts = []
        
        # Source name
        if citation.source_link:
            parts.append(f"[{citation.source_name}]({citation.source_link})")
        else:
            parts.append(f"**{citation.source_name}**")
        
        # Location information
        location_parts = []
        if citation.page_number:
            location_parts.append(f"p. {citation.page_number}")
        if citation.section_heading:
            location_parts.append(f"§ {citation.section_heading}")
        
        if location_parts:
            parts.append(f"({', '.join(location_parts)})")
        
        # Excerpt
        if citation.excerpt:
            excerpt = citation.excerpt[:200] + "..." if len(citation.excerpt) > 200 else citation.excerpt
            parts.append(f"\n> {excerpt}")
        
        # Confidence indicator
        if citation.confidence < 0.8:
            parts.append(f"\n*Confidence: {citation.confidence:.1%}*")
        
        return " ".join(parts)
    
    def _format_html(self, citation: Citation) -> str:
        """Format citation in HTML"""
        parts = []
        
        # Source name
        if citation.source_link:
            parts.append(f'<a href="{citation.source_link}">{citation.source_name}</a>')
        else:
            parts.append(f'<strong>{citation.source_name}</strong>')
        
        # Location information
        location_parts = []
        if citation.page_number:
            location_parts.append(f"p. {citation.page_number}")
        if citation.section_heading:
            location_parts.append(f"§ {citation.section_heading}")
        
        if location_parts:
            parts.append(f"({', '.join(location_parts)})")
        
        # Excerpt
        if citation.excerpt:
            excerpt = citation.excerpt[:200] + "..." if len(citation.excerpt) > 200 else citation.excerpt
            parts.append(f'<blockquote>{excerpt}</blockquote>')
        
        return " ".join(parts)
    
    def _format_academic(self, citation: Citation) -> str:
        """Format citation in academic style"""
        parts = []
        
        # Author (if available)
        author = citation.metadata.get("author", "Unknown")
        parts.append(f"{author}.")
        
        # Year (if available)
        year = citation.metadata.get("year", "n.d.")
        parts.append(f"({year}).")
        
        # Title
        title = citation.metadata.get("title", citation.source_name)
        parts.append(f"{title}.")
        
        # Source
        parts.append(f"{citation.source_name}.")
        
        # Location
        if citation.page_number:
            parts.append(f"p. {citation.page_number}.")
        
        return " ".join(parts)
    
    def _format_plain(self, citation: Citation) -> str:
        """Format citation in plain text"""
        parts = [citation.source_name]
        
        if citation.page_number:
            parts.append(f"(page {citation.page_number})")
        
        if citation.section_heading:
            parts.append(f"section: {citation.section_heading}")
        
        if citation.excerpt:
            excerpt = citation.excerpt[:200] + "..." if len(citation.excerpt) > 200 else citation.excerpt
            parts.append(f'"{excerpt}"')
        
        return " - ".join(parts)
    
    def generate_citation_list(
        self,
        answer_id: str,
        format: str = "markdown",
    ) -> str:
        """
        Generate a formatted list of citations for an answer.
        
        Args:
            answer_id: ID of the answer
            format: Format type
        
        Returns:
            Formatted citation list
        """
        citations = self.get_answer_citations(answer_id)
        
        if not citations:
            return ""
        
        if format == "markdown":
            lines = ["\n**Sources:**\n"]
            for i, citation in enumerate(citations, 1):
                lines.append(f"{i}. {self.format_citation(citation, format)}")
            return "\n".join(lines)
        
        elif format == "html":
            lines = ["<h3>Sources:</h3><ol>"]
            for citation in citations:
                lines.append(f"<li>{self.format_citation(citation, format)}</li>")
            lines.append("</ol>")
            return "\n".join(lines)
        
        else:
            lines = ["Sources:"]
            for i, citation in enumerate(citations, 1):
                lines.append(f"{i}. {self.format_citation(citation, format)}")
            return "\n".join(lines)
    
    def calculate_grounding_score(self, answer_id: str) -> float:
        """
        Calculate how well-grounded an answer is in its citations.
        
        Args:
            answer_id: ID of the answer
        
        Returns:
            Grounding score (0.0 to 1.0)
        """
        citations = self.get_answer_citations(answer_id)
        
        if not citations:
            return 0.0
        
        # Calculate average confidence and relevance
        avg_confidence = sum(c.confidence for c in citations) / len(citations)
        avg_relevance = sum(c.relevance for c in citations) / len(citations)
        
        # Combine scores
        grounding_score = (avg_confidence + avg_relevance) / 2
        
        return grounding_score
    
    def get_traceability_report(self, answer_id: str) -> Dict[str, Any]:
        """
        Generate a traceability report for an answer.
        
        Args:
            answer_id: ID of the answer
        
        Returns:
            Traceability report
        """
        citations = self.get_answer_citations(answer_id)
        
        if not citations:
            return {
                "answer_id": answer_id,
                "has_citations": False,
                "grounding_score": 0.0,
                "citation_count": 0,
            }
        
        # Group by source
        by_source = {}
        for citation in citations:
            source = citation.source_name
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(citation)
        
        # Calculate statistics
        grounding_score = self.calculate_grounding_score(answer_id)
        
        return {
            "answer_id": answer_id,
            "has_citations": True,
            "grounding_score": grounding_score,
            "citation_count": len(citations),
            "by_source": {
                source: len(citations)
                for source, citations in by_source.items()
            },
            "source_types": list(set(c.source_type for c in citations)),
            "file_types": list(set(c.file_type for c in citations)),
            "average_confidence": sum(c.confidence for c in citations) / len(citations),
            "average_relevance": sum(c.relevance for c in citations) / len(citations),
        }
    
    def verify_citation_accuracy(
        self,
        citation_id: str,
        actual_content: str,
    ) -> Dict[str, Any]:
        """
        Verify that a citation accurately reflects the source content.
        
        Args:
            citation_id: ID of the citation
            actual_content: Actual content from the source
        
        Returns:
            Verification result
        """
        citation = self.get_citation(citation_id)
        if not citation:
            return {
                "success": False,
                "error": "Citation not found",
            }
        
        # Simple verification (in production, would use more sophisticated methods)
        excerpt_lower = citation.excerpt.lower()
        content_lower = actual_content.lower()
        
        # Check if excerpt is contained in content
        is_contained = excerpt_lower in content_lower
        
        # Calculate similarity (simplified)
        excerpt_words = set(excerpt_lower.split())
        content_words = set(content_lower.split())
        overlap = len(excerpt_words & content_words)
        similarity = overlap / len(excerpt_words) if excerpt_words else 0.0
        
        return {
            "success": True,
            "is_contained": is_contained,
            "similarity": similarity,
            "is_accurate": is_contained or similarity > 0.8,
        }
    
    def delete_citation(self, citation_id: str) -> bool:
        """Delete a citation"""
        if citation_id in self.citations:
            del self.citations[citation_id]
            
            # Remove from answer links
            for answer_id, citation_ids in self.citation_links.items():
                if citation_id in citation_ids:
                    citation_ids.remove(citation_id)
            
            return True
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get citation system statistics"""
        if not self.citations:
            return {
                "total_citations": 0,
                "by_type": {},
                "by_source_type": {},
            }
        
        by_type = {}
        by_source_type = {}
        
        for citation in self.citations.values():
            # Count by citation type
            cite_type = citation.citation_type.value
            by_type[cite_type] = by_type.get(cite_type, 0) + 1
            
            # Count by source type
            source_type = citation.source_type
            by_source_type[source_type] = by_source_type.get(source_type, 0) + 1
        
        return {
            "total_citations": len(self.citations),
            "linked_answers": len(self.citation_links),
            "by_type": by_type,
            "by_source_type": by_source_type,
        }
