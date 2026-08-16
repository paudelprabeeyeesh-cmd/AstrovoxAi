"""
Intelligent Chunking Strategy - Phase 5.5

Splits large documents into meaningful chunks based on structure:
- Preserve headings
- Preserve paragraph boundaries
- Preserve tables when possible
- Keep code blocks intact
- Avoid cutting important definitions or formulas in half

Good chunking improves retrieval quality significantly.
"""

from typing import Dict, List, Any, Optional
from enum import Enum
import re


class ChunkType(Enum):
    """Types of chunks"""
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    CODE = "code"
    TABLE = "table"
    LIST = "list"
    FORMULA = "formula"
    QUOTE = "quote"
    METADATA = "metadata"


class ChunkingStrategy:
    """
    Intelligently chunks documents based on structure and content.
    Preserves semantic boundaries and improves retrieval quality.
    """
    
    def __init__(
        self,
        max_chunk_size: int = 1000,
        chunk_overlap: int = 200,
        preserve_structure: bool = True,
    ):
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap
        self.preserve_structure = preserve_structure
    
    def chunk_text(
        self,
        text: str,
        file_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Chunk text into meaningful segments.
        
        Args:
            text: Text to chunk
            file_type: Type of file (markdown, pdf, etc.)
            metadata: Additional metadata
        
        Returns:
            List of chunks with metadata
        """
        metadata = metadata or {}
        
        # Choose chunking strategy based on file type
        if file_type == "markdown":
            chunks = self._chunk_markdown(text)
        elif file_type == "pdf":
            chunks = self._chunk_pdf(text)
        elif file_type == "code":
            chunks = self._chunk_code(text)
        else:
            chunks = self._chunk_generic(text)
        
        # Add metadata to chunks
        for i, chunk in enumerate(chunks):
            chunk.update({
                "chunk_id": f"chunk_{i}",
                "chunk_index": i,
                "total_chunks": len(chunks),
                "file_type": file_type,
                "source_metadata": metadata,
            })
        
        return chunks
    
    def _chunk_markdown(self, text: str) -> List[Dict[str, Any]]:
        """Chunk markdown text preserving structure"""
        chunks = []
        
        # Split by headings
        sections = re.split(r'^(#{1,6}\s+.+)$', text, flags=re.MULTILINE)
        
        current_chunk = ""
        current_heading = "Introduction"
        
        for i in range(0, len(sections), 2):
            if i > 0:
                current_heading = sections[i-1].strip()
            
            content = sections[i] if i < len(sections) else ""
            
            # Process content within section
            section_chunks = self._chunk_section_content(content, current_heading)
            chunks.extend(section_chunks)
        
        return chunks if chunks else self._chunk_generic(text)
    
    def _chunk_section_content(self, content: str, heading: str) -> List[Dict[str, Any]]:
        """Chunk content within a section"""
        chunks = []
        
        # Preserve code blocks
        code_blocks = re.findall(r'```[\s\S]*?```', content)
        non_code_content = re.sub(r'```[\s\S]*?```', '<<CODE_BLOCK>>', content)
        
        # Split into paragraphs
        paragraphs = re.split(r'\n\n+', non_code_content)
        
        current_chunk = {
            "type": ChunkType.HEADING.value,
            "content": heading,
            "heading_level": heading.count('#'),
        }
        chunks.append(current_chunk)
        
        current_paragraph_chunk = ""
        code_block_index = 0
        
        for paragraph in paragraphs:
            # Check if this is a code block placeholder
            if '<<CODE_BLOCK>>' in paragraph:
                # Save current paragraph chunk
                if current_paragraph_chunk.strip():
                    chunks.append({
                        "type": ChunkType.PARAGRAPH.value,
                        "content": current_paragraph_chunk.strip(),
                    })
                    current_paragraph_chunk = ""
                
                # Add code block as separate chunk
                if code_block_index < len(code_blocks):
                    chunks.append({
                        "type": ChunkType.CODE.value,
                        "content": code_blocks[code_block_index].strip(),
                    })
                    code_block_index += 1
            else:
                # Add to current paragraph chunk
                if len(current_paragraph_chunk) + len(paragraph) > self.max_chunk_size:
                    if current_paragraph_chunk.strip():
                        chunks.append({
                            "type": ChunkType.PARAGRAPH.value,
                            "content": current_paragraph_chunk.strip(),
                        })
                    current_paragraph_chunk = paragraph
                else:
                    current_paragraph_chunk += "\n\n" + paragraph if current_paragraph_chunk else paragraph
        
        # Add remaining paragraph
        if current_paragraph_chunk.strip():
            chunks.append({
                "type": ChunkType.PARAGRAPH.value,
                "content": current_paragraph_chunk.strip(),
            })
        
        return chunks
    
    def _chunk_pdf(self, text: str) -> List[Dict[str, Any]]:
        """Chunk PDF text (assumes plain text extraction)"""
        # PDFs often have page breaks and sections
        chunks = []
        
        # Split by page breaks (common in PDF extractions)
        pages = re.split(r'\f', text)
        
        for page_num, page in enumerate(pages):
            # Further chunk by paragraphs
            paragraphs = re.split(r'\n\n+', page)
            
            current_chunk = ""
            for paragraph in paragraphs:
                if len(current_chunk) + len(paragraph) > self.max_chunk_size:
                    if current_chunk.strip():
                        chunks.append({
                            "type": ChunkType.PARAGRAPH.value,
                            "content": current_chunk.strip(),
                            "page_number": page_num + 1,
                        })
                    current_chunk = paragraph
                else:
                    current_chunk += "\n\n" + paragraph if current_chunk else paragraph
            
            if current_chunk.strip():
                chunks.append({
                    "type": ChunkType.PARAGRAPH.value,
                    "content": current_chunk.strip(),
                    "page_number": page_num + 1,
                })
        
        return chunks if chunks else self._chunk_generic(text)
    
    def _chunk_code(self, text: str) -> List[Dict[str, Any]]:
        """Chunk code preserving functions and classes"""
        chunks = []
        
        # Split by function/class definitions
        # This is a simplified approach
        code_blocks = re.split(r'\n(def |class )', text)
        
        current_chunk = ""
        
        for i, block in enumerate(code_blocks):
            if i > 0:
                block = code_blocks[i-1][-1] + block  # Add back the "def " or "class "
            
            if len(current_chunk) + len(block) > self.max_chunk_size:
                if current_chunk.strip():
                    chunks.append({
                        "type": ChunkType.CODE.value,
                        "content": current_chunk.strip(),
                    })
                current_chunk = block
            else:
                current_chunk += block if not current_chunk else "\n" + block
        
        if current_chunk.strip():
            chunks.append({
                "type": ChunkType.CODE.value,
                "content": current_chunk.strip(),
            })
        
        return chunks if chunks else self._chunk_generic(text)
    
    def _chunk_generic(self, text: str) -> List[Dict[str, Any]]:
        """Generic chunking for plain text"""
        chunks = []
        
        # Split into paragraphs
        paragraphs = re.split(r'\n\n+', text)
        
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            if len(current_chunk) + len(paragraph) > self.max_chunk_size:
                if current_chunk.strip():
                    chunks.append({
                        "type": ChunkType.PARAGRAPH.value,
                        "content": current_chunk.strip(),
                    })
                current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        if current_chunk.strip():
            chunks.append({
                "type": ChunkType.PARAGRAPH.value,
                "content": current_chunk.strip(),
            })
        
        return chunks if chunks else [{
            "type": ChunkType.PARAGRAPH.value,
            "content": text,
        }]
    
    def add_overlap(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add overlap between chunks for better context"""
        if self.chunk_overlap == 0:
            return chunks
        
        overlapped_chunks = []
        
        for i, chunk in enumerate(chunks):
            content = chunk["content"]
            
            # Add overlap from previous chunk
            if i > 0 and self.chunk_overlap > 0:
                prev_content = chunks[i-1]["content"]
                overlap_text = prev_content[-self.chunk_overlap:]
                content = overlap_text + "\n\n" + content
            
            # Add overlap to next chunk
            if i < len(chunks) - 1 and self.chunk_overlap > 0:
                next_content = chunks[i+1]["content"]
                overlap_text = next_content[:self.chunk_overlap]
                content = content + "\n\n" + overlap_text
            
            chunk["content"] = content
            overlapped_chunks.append(chunk)
        
        return overlapped_chunks
    
    def merge_small_chunks(
        self,
        chunks: List[Dict[str, Any]],
        min_chunk_size: int = 200,
    ) -> List[Dict[str, Any]]:
        """Merge chunks that are too small"""
        merged_chunks = []
        current_chunk = None
        
        for chunk in chunks:
            content = chunk["content"]
            
            if len(content) < min_chunk_size:
                if current_chunk is None:
                    current_chunk = chunk
                else:
                    current_chunk["content"] += "\n\n" + content
                    current_chunk["type"] = ChunkType.PARAGRAPH.value
            else:
                if current_chunk is not None:
                    merged_chunks.append(current_chunk)
                    current_chunk = None
                merged_chunks.append(chunk)
        
        if current_chunk is not None:
            merged_chunks.append(current_chunk)
        
        return merged_chunks
    
    def get_chunk_statistics(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics about chunks"""
        if not chunks:
            return {
                "total_chunks": 0,
                "average_size": 0,
                "by_type": {},
            }
        
        sizes = [len(chunk["content"]) for chunk in chunks]
        by_type = {}
        
        for chunk in chunks:
            chunk_type = chunk.get("type", "unknown")
            by_type[chunk_type] = by_type.get(chunk_type, 0) + 1
        
        return {
            "total_chunks": len(chunks),
            "average_size": sum(sizes) / len(sizes),
            "min_size": min(sizes),
            "max_size": max(sizes),
            "by_type": by_type,
        }
