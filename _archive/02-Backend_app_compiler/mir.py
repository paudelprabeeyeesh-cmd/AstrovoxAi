"""Mid-level Intermediate Representation (MIR).

MIR is a lowered, SSA-form representation suitable for optimization.
It abstracts away high-level constructs while preserving semantics.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from .hir import HIRFunction, HIRModule, HIRType, HIRVariable


class MIROpcode(str, Enum):
    """MIR instruction opcodes."""

    # Terminators
    RETURN = "return"
    BRANCH = "branch"
    SWITCH = "switch"

    # Memory
    ALLOCA = "alloca"
    LOAD = "load"
    STORE = "store"

    # Arithmetic
    ADD = "add"
    SUB = "sub"
    MUL = "mul"
    DIV = "div"
    REM = "rem"

    # Logical
    AND = "and"
    OR = "or"
    XOR = "xor"
    NOT = "not"

    # Comparison
    EQ = "eq"
    NE = "ne"
    LT = "lt"
    GT = "gt"
    LE = "le"
    GE = "ge"

    # Control
    CALL = "call"
    PHI = "phi"
    SELECT = "select"

    # Other
    CAST = "cast"
    EXTRACT = "extract"
    INSERT = "insert"


@dataclass(frozen=True)
class MIRValue:
    """Value in MIR (operand)."""

    name: str
    type: HIRType
    is_constant: bool = False
    constant_value: Any = None

    def __str__(self) -> str:
        if self.is_constant:
            return str(self.constant_value)
        return self.name


@dataclass(frozen=True)
class MIRInstruction:
    """Single MIR instruction."""

    opcode: MIROpcode
    operands: Tuple[MIRValue, ...]
    result: Optional[MIRValue]
    block_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        if self.result:
            return f"{self.result} = {self.opcode.value} {', '.join(str(o) for o in self.operands)}"
        return f"{self.opcode.value} {', '.join(str(o) for o in self.operands)}"


@dataclass(frozen=True)
class MIRBlock:
    """Basic block in MIR."""

    id: str
    instructions: Tuple[MIRInstruction, ...]
    terminator: Optional[MIRInstruction]
    predecessors: Tuple[str, ...] = ()
    successors: Tuple[str, ...] = ()


@dataclass(frozen=True)
class MIRFunction:
    """Function in MIR."""

    name: str
    params: Tuple[MIRValue, ...]
    return_type: HIRType
    blocks: Dict[str, MIRBlock]
    entry_block: str
    locals: Dict[str, MIRValue] = field(default_factory=dict)
    signature_hash: str = ""

    def __post_init__(self) -> None:
        if not self.signature_hash:
            object.__setattr__(
                self,
                "signature_hash",
                hashlib.sha256(
                    f"{self.name}:{self.return_type}:{[str(p.type) for p in self.params]}".encode()
                ).hexdigest()[:16],
            )


@dataclass(frozen=True)
class MIRModule:
    """Top-level MIR module."""

    name: str
    functions: Dict[str, MIRFunction]
    globals: Dict[str, MIRValue]
    source_hash: str = ""
    compiled_at: float = field(default_factory=time.time)


class MIRBuilder:
    """Builds MIR from HIR."""

    def __init__(self) -> None:
        self._counter = 0

    def build_from_hir(self, hir: HIRModule) -> MIRModule:
        """Build MIR from HIR module."""
        mir_functions = {}
        for name, hir_func in hir.functions.items():
            mir_functions[name] = self._lower_function(hir_func)

        return MIRModule(
            name=hir.name,
            functions=mir_functions,
            globals={},
            source_hash=hir.source_hash,
        )

    def _lower_function(self, hir_func: HIRFunction) -> MIRFunction:
        """Lower HIR function to MIR."""
        blocks = {}
        for hir_block in hir_func.body:
            mir_block = self._lower_block(hir_block)
            blocks[mir_block.id] = mir_block

        entry = hir_func.entry_block
        params = tuple(
            MIRValue(name=p.name, type=p.type) for p in hir_func.params
        )

        return MIRFunction(
            name=hir_func.name,
            params=params,
            return_type=hir_func.return_type,
            blocks=blocks,
            entry_block=entry,
            signature_hash=hir_func.signature_hash,
        )

    def _lower_block(self, hir_block: Any) -> MIRBlock:
        """Lower HIR block to MIR block."""
        instructions = []
        for stmt in hir_block.statements:
            mir_instrs = self._lower_statement(stmt, hir_block.id)
            instructions.extend(mir_instrs)

        return MIRBlock(
            id=hir_block.id,
            instructions=tuple(instructions),
            terminator=None,
            predecessors=hir_block.predecessors,
            successors=hir_block.successors,
        )

    def _lower_statement(self, stmt: Any, block_id: str) -> List[MIRInstruction]:
        """Lower HIR statement to MIR instructions."""
        return []

    def _next_temp(self, prefix: str = "tmp") -> str:
        """Generate unique temporary name."""
        self._counter += 1
        return f"{prefix}_{self._counter}"
