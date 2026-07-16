"""
Reliability Safeguards - Phase 2.14

Provides safeguards to ensure system reliability:
- Retry failed tool calls
- Validate structured outputs
- Detect conflicting information
- Request clarification when necessary
- Handle partial failures gracefully
- Log execution traces for diagnostics
"""

from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from datetime import datetime
import asyncio
import json


class FailureMode(Enum):
    """Types of failure modes"""
    TOOL_FAILURE = "tool_failure"
    MODEL_FAILURE = "model_failure"
    VALIDATION_FAILURE = "validation_failure"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    NETWORK_ERROR = "network_error"
    PARSE_ERROR = "parse_error"
    UNKNOWN = "unknown"


class RetryPolicy:
    """Retry policy for failed operations"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay_ms: int = 1000,
        max_delay_ms: int = 10000,
        backoff_multiplier: float = 2.0,
        retryable_errors: Optional[List[str]] = None,
    ):
        self.max_retries = max_retries
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        self.backoff_multiplier = backoff_multiplier
        self.retryable_errors = retryable_errors or [
            "timeout",
            "network",
            "rate_limit",
            "temporary",
        ]
    
    def should_retry(self, error: str, attempt: int) -> bool:
        """Determine if operation should be retried"""
        if attempt >= self.max_retries:
            return False
        
        error_lower = error.lower()
        return any(err in error_lower for err in self.retryable_errors)
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt"""
        delay = self.base_delay_ms * (self.backoff_multiplier ** attempt)
        return min(delay, self.max_delay_ms) / 1000.0  # Convert to seconds


class OutputValidator:
    """Validates structured outputs"""
    
    def __init__(self):
        self.validators = {
            "json": self._validate_json,
            "code": self._validate_code,
            "email": self._validate_email,
            "url": self._validate_url,
        }
    
    def validate(self, output: str, expected_format: str) -> tuple[bool, Optional[str]]:
        """
        Validate output against expected format.
        
        Args:
            output: The output to validate
            expected_format: Expected format (json, code, email, url, etc.)
        
        Returns:
            (is_valid, error_message)
        """
        validator = self.validators.get(expected_format.lower())
        if not validator:
            # If no specific validator, accept the output
            return True, None
        
        return validator(output)
    
    def _validate_json(self, output: str) -> tuple[bool, Optional[str]]:
        """Validate JSON output"""
        try:
            json.loads(output)
            return True, None
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {str(e)}"
    
    def _validate_code(self, output: str) -> tuple[bool, Optional[str]]:
        """Validate code output (basic checks)"""
        if not output.strip():
            return False, "Empty code output"
        
        # Check for basic code structure
        if any(keyword in output for keyword in ["def ", "function ", "class ", "import ", "const "]):
            return True, None
        
        # Accept non-empty output as valid code
        return True, None
    
    def _validate_email(self, output: str) -> tuple[bool, Optional[str]]:
        """Validate email address"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, output.strip()):
            return True, None
        return False, "Invalid email format"
    
    def _validate_url(self, output: str) -> tuple[bool, Optional[str]]:
        """Validate URL"""
        import re
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        if re.match(pattern, output.strip()):
            return True, None
        return False, "Invalid URL format"


class ReliabilitySafeguards:
    """
    Implements reliability safeguards for the intelligence engine.
    """
    
    def __init__(self):
        self.retry_policy = RetryPolicy()
        self.output_validator = OutputValidator()
        self.failure_log: List[Dict[str, Any]] = []
        self.conflict_detector = ConflictDetector()
    
    async def execute_with_retry(
        self,
        operation: Callable,
        operation_name: str,
        *args,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Execute an operation with retry logic.
        
        Args:
            operation: The operation to execute
            operation_name: Name of the operation for logging
            *args: Arguments to pass to operation
            **kwargs: Keyword arguments to pass to operation
        
        Returns:
            Operation result with retry information
        """
        attempt = 0
        last_error = None
        
        while attempt <= self.retry_policy.max_retries:
            try:
                if asyncio.iscoroutinefunction(operation):
                    result = await operation(*args, **kwargs)
                else:
                    result = operation(*args, **kwargs)
                
                return {
                    "success": True,
                    "result": result,
                    "attempts": attempt + 1,
                    "operation": operation_name,
                }
            
            except Exception as e:
                last_error = str(e)
                error_message = str(e)
                
                # Log the failure
                self._log_failure(
                    operation_name=operation_name,
                    attempt=attempt,
                    error=error_message,
                )
                
                # Check if we should retry
                if not self.retry_policy.should_retry(error_message, attempt):
                    break
                
                # Calculate delay and wait
                delay = self.retry_policy.get_delay(attempt)
                await asyncio.sleep(delay)
                
                attempt += 1
        
        # All retries exhausted
        return {
            "success": False,
            "error": last_error,
            "attempts": attempt + 1,
            "operation": operation_name,
        }
    
    def validate_output(
        self,
        output: str,
        expected_format: str,
        strict: bool = False,
    ) -> Dict[str, Any]:
        """
        Validate output against expected format.
        
        Args:
            output: The output to validate
            expected_format: Expected format
            strict: If True, fail validation on format mismatch
        
        Returns:
            Validation result
        """
        is_valid, error = self.output_validator.validate(output, expected_format)
        
        if not is_valid and strict:
            return {
                "valid": False,
                "error": error,
                "output": output,
            }
        
        return {
            "valid": is_valid,
            "error": error if not is_valid else None,
            "output": output,
        }
    
    def detect_conflicts(
        self,
        information_sources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Detect conflicting information from multiple sources.
        
        Args:
            information_sources: List of information sources with content
        
        Returns:
            Conflict detection result
        """
        return self.conflict_detector.detect(information_sources)
    
    def should_request_clarification(
        self,
        user_message: str,
        context: Dict[str, Any],
    ) -> tuple[bool, Optional[str]]:
        """
        Determine if clarification should be requested from the user.
        
        Args:
            user_message: The user's message
            context: Additional context
        
        Returns:
            (should_clarify, reason)
        """
        # Check for ambiguous messages
        if len(user_message.strip()) < 10:
            return True, "Message is too short and may be ambiguous"
        
        # Check for vague pronouns
        vague_pronouns = ["it", "that", "this", "something", "anything"]
        words = user_message.lower().split()
        if len(words) <= 3 and any(word in vague_pronouns for word in words):
            return True, "Message uses vague pronouns without context"
        
        # Check for multiple possible interpretations
        if context.get("has_multiple_intents", False):
            return True, "Multiple possible intents detected"
        
        # Check for missing required information
        if context.get("missing_required_info"):
            return True, f"Missing required information: {context['missing_required_info']}"
        
        return False, None
    
    def handle_partial_failure(
        self,
        completed_steps: List[Dict[str, Any]],
        failed_steps: List[Dict[str, Any]],
        original_request: str,
    ) -> Dict[str, Any]:
        """
        Handle partial failures gracefully.
        
        Args:
            completed_steps: Steps that completed successfully
            failed_steps: Steps that failed
            original_request: The original user request
        
        Returns:
            Response handling the partial failure
        """
        # Determine if we can provide a partial response
        can_provide_partial = len(completed_steps) > 0
        
        if not can_provide_partial:
            return {
                "success": False,
                "error": "All steps failed",
                "failed_steps": failed_steps,
            }
        
        # Generate a response that acknowledges the partial failure
        response = {
            "success": True,
            "partial": True,
            "message": f"Completed {len(completed_steps)} of {len(completed_steps) + len(failed_steps)} steps.",
            "completed_results": [step.get("result") for step in completed_steps],
            "failed_steps": [
                {
                    "step": step.get("step_id"),
                    "error": step.get("error"),
                }
                for step in failed_steps
            ],
        }
        
        return response
    
    def _log_failure(
        self,
        operation_name: str,
        attempt: int,
        error: str,
    ):
        """Log a failure for diagnostics"""
        failure_record = {
            "operation": operation_name,
            "attempt": attempt,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.failure_log.append(failure_record)
    
    def get_failure_statistics(self) -> Dict[str, Any]:
        """Get statistics about failures"""
        if not self.failure_log:
            return {
                "total_failures": 0,
                "by_operation": {},
                "recent_failures": [],
            }
        
        by_operation = {}
        for failure in self.failure_log:
            op = failure["operation"]
            if op not in by_operation:
                by_operation[op] = 0
            by_operation[op] += 1
        
        return {
            "total_failures": len(self.failure_log),
            "by_operation": by_operation,
            "recent_failures": self.failure_log[-10:],  # Last 10 failures
        }
    
    def cleanup_old_failures(self, max_age_hours: int = 24):
        """Clean up old failure logs"""
        cutoff = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        
        self.failure_log = [
            failure for failure in self.failure_log
            if datetime.fromisoformat(failure["timestamp"]).timestamp() >= cutoff
        ]
        
        return len(self.failure_log)


class ConflictDetector:
    """Detects conflicting information from multiple sources"""
    
    def __init__(self):
        self.similarity_threshold = 0.7
    
    def detect(self, information_sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect conflicts in information sources.
        
        Args:
            information_sources: List of sources with content and metadata
        
        Returns:
            Conflict detection result
        """
        conflicts = []
        
        # Compare each pair of sources
        for i in range(len(information_sources)):
            for j in range(i + 1, len(information_sources)):
                source1 = information_sources[i]
                source2 = information_sources[j]
                
                conflict = self._compare_sources(source1, source2)
                if conflict:
                    conflicts.append({
                        "source1": source1.get("source", f"source_{i}"),
                        "source2": source2.get("source", f"source_{j}"),
                        "conflict": conflict,
                    })
        
        return {
            "has_conflicts": len(conflicts) > 0,
            "conflicts": conflicts,
            "confidence": self._calculate_confidence(conflicts, len(information_sources)),
        }
    
    def _compare_sources(
        self,
        source1: Dict[str, Any],
        source2: Dict[str, Any],
    ) -> Optional[str]:
        """Compare two information sources for conflicts"""
        content1 = source1.get("content", "").lower()
        content2 = source2.get("content", "").lower()
        
        # Simple heuristic: check for contradictory statements
        contradictions = [
            ("is true", "is false"),
            ("is correct", "is incorrect"),
            ("yes", "no"),
            ("enabled", "disabled"),
            ("available", "unavailable"),
        ]
        
        for phrase1, phrase2 in contradictions:
            if phrase1 in content1 and phrase2 in content2:
                return f"Contradictory statements: '{phrase1}' vs '{phrase2}'"
        
        # Check for numerical conflicts
        numbers1 = self._extract_numbers(content1)
        numbers2 = self._extract_numbers(content2)
        
        if numbers1 and numbers2 and numbers1 != numbers2:
            return f"Numerical conflict: {numbers1} vs {numbers2}"
        
        return None
    
    def _extract_numbers(self, text: str) -> Optional[float]:
        """Extract the first number from text"""
        import re
        match = re.search(r'\d+\.?\d*', text)
        if match:
            return float(match.group())
        return None
    
    def _calculate_confidence(
        self,
        conflicts: List[Dict[str, Any]],
        total_sources: int,
    ) -> float:
        """Calculate confidence in conflict detection"""
        if total_sources < 2:
            return 0.0
        
        conflict_ratio = len(conflicts) / (total_sources * (total_sources - 1) / 2)
        return min(conflict_ratio * 2, 1.0)  # Scale to 0-1
