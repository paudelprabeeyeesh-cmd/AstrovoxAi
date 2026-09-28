import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PromptVisibility(str, Enum):
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"


@dataclass
class PromptTemplate:
    template_id: str
    prompt_id: str
    content: str
    variables: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class PromptListing:
    prompt_id: str
    title: str
    author_id: str
    description: str
    content: str
    visibility: PromptVisibility
    tags: List[str] = field(default_factory=list)
    templates: List[PromptTemplate] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class PromptMarketplace:
    def __init__(self) -> None:
        self._prompts: Dict[str, PromptListing] = {}

    def share_prompt(
        self,
        title: str,
        author_id: str,
        description: str,
        content: str,
        visibility: PromptVisibility = PromptVisibility.PUBLIC,
        tags: Optional[List[str]] = None,
        templates: Optional[List[Dict[str, Any]]] = None,
    ) -> PromptListing:
        prompt_id = str(uuid.uuid4())
        template_objs = []
        if templates:
            for t in templates:
                template_objs.append(PromptTemplate(
                    template_id=str(uuid.uuid4()),
                    prompt_id=prompt_id,
                    content=t.get("content", ""),
                    variables=t.get("variables", []),
                    description=t.get("description", ""),
                ))

        listing = PromptListing(
            prompt_id=prompt_id,
            title=title,
            author_id=author_id,
            description=description,
            content=content,
            visibility=visibility,
            tags=tags or [],
            templates=template_objs,
        )
        self._prompts[prompt_id] = listing
        logger.info("Shared prompt %s", title)
        return listing

    def render_template(self, prompt_id: str, template_id: str, variables: Dict[str, str]) -> str:
        if prompt_id not in self._prompts:
            raise KeyError(f"Prompt not found: {prompt_id}")
        prompt = self._prompts[prompt_id]
        template = next((t for t in prompt.templates if t.template_id == template_id), None)
        if template is None:
            raise KeyError(f"Template not found: {template_id}")
        content = template.content
        for key, value in variables.items():
            content = content.replace(f"{{{key}}}", value)
        return content

    def search_prompts(
        self,
        query: str = "",
        tags: Optional[List[str]] = None,
        author_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[PromptListing]:
        results = list(self._prompts.values())
        if query:
            q = query.lower()
            results = [p for p in results if q in p.title.lower() or q in p.description.lower()]
        if tags:
            tag_set = set(tags)
            results = [p for p in results if tag_set.issubset(set(p.tags))]
        if author_id:
            results = [p for p in results if p.author_id == author_id]
        return results[:limit]

    def get_prompt(self, prompt_id: str) -> PromptListing:
        if prompt_id not in self._prompts:
            raise KeyError(f"Prompt not found: {prompt_id}")
        return self._prompts[prompt_id]

    def list_prompts(self) -> List[PromptListing]:
        return list(self._prompts.values())
