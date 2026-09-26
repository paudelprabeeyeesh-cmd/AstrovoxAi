"""Content Security Policy (CSP) headers."""

from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class CSPDirective:
    default_src: List[str] = None
    script_src: List[str] = None
    style_src: List[str] = None
    img_src: List[str] = None
    connect_src: List[str] = None
    font_src: List[str] = None
    object_src: List[str] = None
    media_src: List[str] = None
    frame_src: List[str] = None
    report_uri: Optional[str] = None
    report_to: Optional[str] = None

    def __post_init__(self):
        if self.default_src is None:
            self.default_src = ["'self'"]
        if self.script_src is None:
            self.script_src = ["'self'"]
        if self.style_src is None:
            self.style_src = ["'self'", "'unsafe-hashes'"]
        if self.img_src is None:
            self.img_src = ["'self'", "data:", "https:"]
        if self.connect_src is None:
            self.connect_src = ["'self'", "https://api.astrovox.ai"]
        if self.font_src is None:
            self.font_src = ["'self'", "data:"]
        if self.object_src is None:
            self.object_src = ["'none'"]
        if self.media_src is None:
            self.media_src = ["'self'"]
        if self.frame_src is None:
            self.frame_src = ["'self'"]

    def to_header(self) -> str:
        directives = []
        if self.default_src:
            directives.append(f"default-src {' '.join(self.default_src)}")
        if self.script_src:
            directives.append(f"script-src {' '.join(self.script_src)}")
        if self.style_src:
            directives.append(f"style-src {' '.join(self.style_src)}")
        if self.img_src:
            directives.append(f"img-src {' '.join(self.img_src)}")
        if self.connect_src:
            directives.append(f"connect-src {' '.join(self.connect_src)}")
        if self.font_src:
            directives.append(f"font-src {' '.join(self.font_src)}")
        if self.object_src:
            directives.append(f"object-src {' '.join(self.object_src)}")
        if self.media_src:
            directives.append(f"media-src {' '.join(self.media_src)}")
        if self.frame_src:
            directives.append(f"frame-src {' '.join(self.frame_src)}")
        if self.report_uri:
            directives.append(f"report-uri {self.report_uri}")
        if self.report_to:
            directives.append(f"report-to {self.report_to}")
        return "; ".join(directives)


class CSPManager:
    _policies: Dict[str, CSPDirective] = {}

    @classmethod
    def register(cls, name: str, policy: CSPDirective) -> None:
        cls._policies[name] = policy

    @classmethod
    def get_policy(cls, name: str) -> Optional[CSPDirective]:
        return cls._policies.get(name)

    @classmethod
    def get_header(cls, name: str = "default") -> str:
        policy = cls._policies.get(name)
        if policy:
            return policy.to_header()
        return ""
