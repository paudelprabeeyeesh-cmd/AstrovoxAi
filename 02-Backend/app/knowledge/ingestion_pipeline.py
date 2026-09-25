"""
Knowledge Ingestion Pipeline - Phase 5.4

Structured pipeline for processing knowledge sources:
- File detection
- Text extraction
- OCR if needed
- Chunking
- Metadata tagging
- Embedding generation
- Indexing
- Storage
- Permission assignment

This pipeline should be asynchronous so that large files do not freeze the user experience.
"""

from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, field
import asyncio


class IngestionStage(Enum):
    """Stages of the ingestion pipeline"""
    FILE_DETECTION = "file_detection"
    TEXT_EXTRACTION = "text_extraction"
    OCR_PROCESSING = "ocr_processing"
    CHUNKING = "chunking"
    METADATA_TAGGING = "metadata_tagging"
    EMBEDDING_GENERATION = "embedding_generation"
    INDEXING = "indexing"
    STORAGE = "storage"
    PERMISSION_ASSIGNMENT = "permission_assignment"
    COMPLETED = "completed"
    FAILED = "failed"


class FileType(Enum):
    """Supported file types"""
    PDF = "pdf"
    WORD = "word"
    POWERPOINT = "powerpoint"
    TEXT = "text"
    MARKDOWN = "markdown"
    CSV = "csv"
    EXCEL = "excel"
    IMAGE = "image"
    WEB_PAGE = "web_page"
    GITHUB_REPO = "github_repo"
    NOTION_PAGE = "notion_page"
    GOOGLE_DRIVE = "google_drive"


@dataclass
class IngestionTask:
    """A task in the ingestion pipeline"""
    task_id: str
    file_path: str
    file_type: FileType
    user_id: int
    workspace_id: Optional[str] = None
    project_id: Optional[str] = None
    current_stage: IngestionStage = IngestionStage.FILE_DETECTION
    status: str = "pending"
    progress: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    embeddings: List[Any] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class IngestionPipeline:
    """
    Manages the ingestion of knowledge sources through a structured pipeline.
    Processes files asynchronously to avoid blocking the user experience.
    """
    
    def __init__(self):
        self.tasks: Dict[str, IngestionTask] = {}
        self.active_tasks: Dict[str, IngestionTask] = {}
        self.next_task_id = 1
        
        # Stage handlers
        self.stage_handlers = {
            IngestionStage.FILE_DETECTION: self._handle_file_detection,
            IngestionStage.TEXT_EXTRACTION: self._handle_text_extraction,
            IngestionStage.OCR_PROCESSING: self._handle_ocr_processing,
            IngestionStage.CHUNKING: self._handle_chunking,
            IngestionStage.METADATA_TAGGING: self._handle_metadata_tagging,
            IngestionStage.EMBEDDING_GENERATION: self._handle_embedding_generation,
            IngestionStage.INDEXING: self._handle_indexing,
            IngestionStage.STORAGE: self._handle_storage,
            IngestionStage.PERMISSION_ASSIGNMENT: self._handle_permission_assignment,
        }
        
        # Callbacks for external integration
        self.on_chunk_complete: Optional[Callable] = None
        self.on_embedding_complete: Optional[Callable] = None
        self.on_task_complete: Optional[Callable] = None
    
    async def ingest_file(
        self,
        file_path: str,
        file_type: FileType,
        user_id: int,
        workspace_id: Optional[str] = None,
        project_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> IngestionTask:
        """
        Start ingesting a file through the pipeline.
        
        Args:
            file_path: Path to the file
            file_type: Type of file
            user_id: User ID
            workspace_id: Optional workspace ID
            project_id: Optional project ID
            metadata: Additional metadata
        
        Returns:
            Ingestion task
        """
        task_id = f"task_{self.next_task_id}"
        self.next_task_id += 1
        
        task = IngestionTask(
            task_id=task_id,
            file_path=file_path,
            file_type=file_type,
            user_id=user_id,
            workspace_id=workspace_id,
            project_id=project_id,
            metadata=metadata or {},
        )
        
        self.tasks[task_id] = task
        self.active_tasks[task_id] = task
        
        # Start async processing
        asyncio.create_task(self._process_task(task_id))
        
        return task
    
    async def _process_task(self, task_id: str):
        """Process a task through all pipeline stages"""
        task = self.tasks.get(task_id)
        if not task:
            return
        
        task.started_at = datetime.utcnow().isoformat()
        task.status = "processing"
        
        stages = [
            IngestionStage.FILE_DETECTION,
            IngestionStage.TEXT_EXTRACTION,
            IngestionStage.OCR_PROCESSING,
            IngestionStage.CHUNKING,
            IngestionStage.METADATA_TAGGING,
            IngestionStage.EMBEDDING_GENERATION,
            IngestionStage.INDEXING,
            IngestionStage.STORAGE,
            IngestionStage.PERMISSION_ASSIGNMENT,
        ]
        
        try:
            for stage in stages:
                task.current_stage = stage
                task.progress = (stages.index(stage) / len(stages)) * 100
                
                # Process stage
                await self._process_stage(task, stage)
            
            task.current_stage = IngestionStage.COMPLETED
            task.status = "completed"
            task.progress = 100.0
            task.completed_at = datetime.utcnow().isoformat()
            
            # Remove from active tasks
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            
            # Call completion callback
            if self.on_task_complete:
                await self.on_task_complete(task)
        
        except Exception as e:
            task.current_stage = IngestionStage.FAILED
            task.status = "failed"
            task.error = str(e)
            
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
    
    async def _process_stage(self, task: IngestionTask, stage: IngestionStage):
        """Process a single stage of the pipeline"""
        handler = self.stage_handlers.get(stage)
        if handler:
            await handler(task)
    
    async def _handle_file_detection(self, task: IngestionTask):
        """Handle file detection stage"""
        # Detect file properties
        task.metadata["file_size"] = await self._get_file_size(task.file_path)
        task.metadata["mime_type"] = await self._detect_mime_type(task.file_path)
        task.metadata["encoding"] = await self._detect_encoding(task.file_path)
    
    async def _handle_text_extraction(self, task: IngestionTask):
        """Handle text extraction stage"""
        # Extract text based on file type
        if task.file_type == FileType.PDF:
            task.metadata["extracted_text"] = await self._extract_pdf_text(task.file_path)
        elif task.file_type == FileType.WORD:
            task.metadata["extracted_text"] = await self._extract_word_text(task.file_path)
        elif task.file_type == FileType.POWERPOINT:
            task.metadata["extracted_text"] = await self._extract_ppt_text(task.file_path)
        elif task.file_type in [FileType.TEXT, FileType.MARKDOWN]:
            task.metadata["extracted_text"] = await self._extract_plain_text(task.file_path)
        elif task.file_type in [FileType.CSV, FileType.EXCEL]:
            task.metadata["extracted_text"] = await self._extract_spreadsheet_text(task.file_path)
        else:
            task.metadata["extracted_text"] = ""
    
    async def _handle_ocr_processing(self, task: IngestionTask):
        """Handle OCR processing stage"""
        # Only process if file is an image or if text extraction failed
        if task.file_type == FileType.IMAGE or not task.metadata.get("extracted_text"):
            task.metadata["ocr_text"] = await self._perform_ocr(task.file_path)
    
    async def _handle_chunking(self, task: IngestionTask):
        """Handle chunking stage"""
        text = task.metadata.get("extracted_text", "") + task.metadata.get("ocr_text", "")
        
        # Import chunking strategy
        from .chunking_strategy import ChunkingStrategy
        chunker = ChunkingStrategy()
        
        # Chunk the text
        task.chunks = chunker.chunk_text(
            text=text,
            file_type=task.file_type.value,
            metadata=task.metadata,
        )
        
        # Call chunk complete callback
        if self.on_chunk_complete:
            await self.on_chunk_complete(task.task_id, task.chunks)
    
    async def _handle_metadata_tagging(self, task: IngestionTask):
        """Handle metadata tagging stage"""
        # Enhance metadata with additional information
        task.metadata["chunk_count"] = len(task.chunks)
        task.metadata["language"] = await self._detect_language(task.metadata.get("extracted_text", ""))
        task.metadata["word_count"] = len(task.metadata.get("extracted_text", "").split())
        task.metadata["character_count"] = len(task.metadata.get("extracted_text", ""))
        task.metadata["ingested_at"] = datetime.utcnow().isoformat()
    
    async def _handle_embedding_generation(self, task: IngestionTask):
        """Handle embedding generation stage"""
        # Generate embeddings for each chunk
        for chunk in task.chunks:
            embedding = await self._generate_embedding(chunk["content"])
            chunk["embedding"] = embedding
            task.embeddings.append(embedding)
        
        # Call embedding complete callback
        if self.on_embedding_complete:
            await self.on_embedding_complete(task.task_id, task.embeddings)
    
    async def _handle_indexing(self, task: IngestionTask):
        """Handle indexing stage"""
        # Index chunks in vector store
        # This would integrate with the vector store from memory system
        task.metadata["indexed"] = True
        task.metadata["index_id"] = f"index_{task.task_id}"
    
    async def _handle_storage(self, task: IngestionTask):
        """Handle storage stage"""
        # Store chunks and metadata in database
        task.metadata["stored"] = True
        task.metadata["storage_id"] = f"storage_{task.task_id}"
    
    async def _handle_permission_assignment(self, task: IngestionTask):
        """Handle permission assignment stage"""
        # Assign permissions based on workspace/project
        task.metadata["permission_level"] = "workspace" if task.workspace_id else "private"
        task.metadata["owner_id"] = task.user_id
        task.metadata["workspace_id"] = task.workspace_id
        task.metadata["project_id"] = task.project_id
    
    # Helper methods
    
    async def _get_file_size(self, file_path: str) -> int:
        """Get file size"""
        import os
        return os.path.getsize(file_path)
    
    async def _detect_mime_type(self, file_path: str) -> str:
        """Detect MIME type"""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "application/octet-stream"
    
    async def _detect_encoding(self, file_path: str) -> str:
        """Detect file encoding"""
        # Simplified encoding detection
        return "utf-8"
    
    async def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF"""
        # Placeholder - would use PyPDF2 or pdfplumber
        return f"[PDF text extraction for {file_path}]"
    
    async def _extract_word_text(self, file_path: str) -> str:
        """Extract text from Word document"""
        # Placeholder - would use python-docx
        return f"[Word text extraction for {file_path}]"
    
    async def _extract_ppt_text(self, file_path: str) -> str:
        """Extract text from PowerPoint"""
        # Placeholder - would use python-pptx
        return f"[PowerPoint text extraction for {file_path}]"
    
    async def _extract_plain_text(self, file_path: str) -> str:
        """Extract text from plain text file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    async def _extract_spreadsheet_text(self, file_path: str) -> str:
        """Extract text from spreadsheet"""
        # Placeholder - would use pandas or openpyxl
        return f"[Spreadsheet text extraction for {file_path}]"
    
    async def _perform_ocr(self, file_path: str) -> str:
        """Perform OCR on image"""
        # Placeholder - would use pytesseract
        return f"[OCR text extraction for {file_path}]"
    
    async def _detect_language(self, text: str) -> str:
        """Detect language of text"""
        # Placeholder - would use langdetect
        return "en"
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        # Placeholder - would use OpenAI embeddings or similar
        return [0.0] * 1536  # Placeholder embedding
    
    # Task management methods
    
    def get_task(self, task_id: str) -> Optional[IngestionTask]:
        """Get an ingestion task by ID"""
        return self.tasks.get(task_id)
    
    def get_user_tasks(self, user_id: int) -> List[IngestionTask]:
        """Get all tasks for a user"""
        return [task for task in self.tasks.values() if task.user_id == user_id]
    
    def get_active_tasks(self) -> List[IngestionTask]:
        """Get currently active tasks"""
        return list(self.active_tasks.values())
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel an active task"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.status = "cancelled"
            task.current_stage = IngestionStage.FAILED
            task.error = "Task cancelled by user"
            del self.active_tasks[task_id]
            return True
        return False
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        total_tasks = len(self.tasks)
        completed_tasks = sum(1 for t in self.tasks.values() if t.status == "completed")
        failed_tasks = sum(1 for t in self.tasks.values() if t.status == "failed")
        active_tasks = len(self.active_tasks)
        
        by_file_type = {}
        for task in self.tasks.values():
            file_type = task.file_type.value
            by_file_type[file_type] = by_file_type.get(file_type, 0) + 1
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "active_tasks": active_tasks,
            "by_file_type": by_file_type,
        }
