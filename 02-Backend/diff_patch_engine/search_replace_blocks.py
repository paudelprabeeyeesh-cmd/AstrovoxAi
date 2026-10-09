from typing import Optional


class SearchReplaceBlock:
    def __init__(self, old_text: str, new_text: str):
        self.old_text = old_text
        self.new_text = new_text

    def validate(self, file_content: str) -> bool:
        if not isinstance(self.old_text, str) or not isinstance(self.new_text, str):
            return False
        if not self.old_text or not self.new_text:
            return False
        if self.old_text not in file_content:
            return False
        count = file_content.count(self.old_text)
        return count == 1

    def get_match_position(self, file_content: str) -> Optional[int]:
        if not self.validate(file_content):
            return None
        return file_content.index(self.old_text)

    def apply(self, file_content: str) -> str:
        if not self.validate(file_content):
            raise ValueError("old_text is not unique or missing in file_content")
        return file_content.replace(self.old_text, self.new_text, 1)

    def to_dict(self) -> dict:
        return {"old_text": self.old_text, "new_text": self.new_text}

    @classmethod
    def from_dict(cls, data: dict) -> "SearchReplaceBlock":
        return cls(data["old_text"], data["new_text"])
