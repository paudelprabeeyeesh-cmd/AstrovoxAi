from typing import Optional, Tuple


class PreImageValidator:
    @staticmethod
    def validate_exact(old_text: str, current_file: str) -> bool:
        return old_text in current_file

    @staticmethod
    def validate_fuzzy(old_text: str, current_file: str, threshold: float = 0.85) -> bool:
        if not old_text or not current_file:
            return False
        old_lines = old_text.splitlines()
        file_lines = current_file.splitlines()
        max_match_ratio = 0.0
        for i in range(len(file_lines) - len(old_lines) + 1):
            window = file_lines[i : i + len(old_lines)]
            matches = sum(1 for a, b in zip(old_lines, window) if a == b)
            ratio = matches / max(len(old_lines), 1)
            if ratio > max_match_ratio:
                max_match_ratio = ratio
        return max_match_ratio >= threshold

    @staticmethod
    def find_best_match(old_text: str, current_file: str) -> Optional[Tuple[int, float]]:
        old_lines = old_text.splitlines()
        file_lines = current_file.splitlines()
        best_start = 0
        best_ratio = 0.0
        for i in range(len(file_lines) - len(old_lines) + 1):
            window = file_lines[i : i + len(old_lines)]
            matches = sum(1 for a, b in zip(old_lines, window) if a == b)
            ratio = matches / max(len(old_lines), 1)
            if ratio > best_ratio:
                best_ratio = ratio
                best_start = i
        if best_ratio > 0:
            return best_start, best_ratio
        return None

    @staticmethod
    def validate(old_text: str, current_file: str, fuzzy: bool = False) -> dict:
        exact = PreImageValidator.validate_exact(old_text, current_file)
        if exact:
            return {"valid": True, "mode": "exact", "position": current_file.index(old_text)}
        if fuzzy:
            match = PreImageValidator.find_best_match(old_text, current_file)
            if match and match[1] >= 0.85:
                return {"valid": True, "mode": "fuzzy", "position": match[0], "score": match[1]}
        return {"valid": False, "mode": "none", "position": None, "score": 0.0}
