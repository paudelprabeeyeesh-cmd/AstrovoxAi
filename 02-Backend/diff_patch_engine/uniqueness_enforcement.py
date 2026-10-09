from typing import Optional


class UniquenessEnforcer:
    @staticmethod
    def count_occurrences(text: str, pattern: str) -> int:
        return text.count(pattern)

    @staticmethod
    def is_unique(text: str, pattern: str) -> bool:
        if not pattern:
            return False
        return text.count(pattern) == 1

    @staticmethod
    def enforce(text: str, pattern: str) -> Optional[int]:
        if UniquenessEnforcer.is_unique(text, pattern):
            return text.index(pattern)
        return None

    @staticmethod
    def get_all_positions(text: str, pattern: str):
        positions = []
        start = 0
        while True:
            idx = text.find(pattern, start)
            if idx == -1:
                break
            positions.append(idx)
            start = idx + 1
        return positions

    @staticmethod
    def validate_patch(old_text: str, file_content: str) -> dict:
        count = UniquenessEnforcer.count_occurrences(file_content, old_text)
        return {
            "valid": count == 1,
            "occurrences": count,
            "positions": UniquenessEnforcer.get_all_positions(file_content, old_text)
            if count > 0
            else [],
        }
