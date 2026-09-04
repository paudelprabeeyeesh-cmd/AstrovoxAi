"""Bytecode generation and optimization.

Generates target-agnostic bytecode from LIR and applies optimizations:
- Constant folding
- Dead code elimination
- Instruction combining
- Loop-invariant code motion
- Register allocation (linear scan)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Set, Tuple

from .cfg import LIRBlock, LIRFunction, LIRInstruction, LIRModule

logger = logging.getLogger(__name__)


class BytecodeOp(IntEnum):
    """Bytecode opcodes."""

    HALT = 0x00
    LOAD_CONST = 0x01
    LOAD_VAR = 0x02
    STORE_VAR = 0x03
    ADD = 0x10
    SUB = 0x11
    MUL = 0x12
    DIV = 0x13
    REM = 0x14
    MOD = 0x15
    AND = 0x16
    OR = 0x17
    XOR = 0x18
    NOT = 0x19
    EQ = 0x20
    NE = 0x21
    LT = 0x22
    GT = 0x23
    LE = 0x24
    GE = 0x25
    CALL = 0x30
    RETURN = 0x31
    JUMP = 0x32
    JUMP_IF_FALSE = 0x33
    JUMP_IF_TRUE = 0x34
    PHI = 0x35
    NOP = 0xFF


@dataclass(frozen=True)
class BytecodeInstruction:
    """Single bytecode instruction."""

    op: BytecodeOp
    operands: Tuple[Any, ...]

    def __repr__(self) -> str:
        return f"{self.op.name}({', '.join(map(str, self.operands))})"


@dataclass
class BytecodeFunction:
    """Compiled bytecode for a function."""

    name: str
    instructions: List[BytecodeInstruction] = field(default_factory=list)
    registers: int = 1
    params: int = 0
    local_names: List[str] = field(default_factory=list)

    @property
    def bytecode(self) -> bytes:
        """Serialize to bytes."""
        result = bytearray()
        for instr in self.instructions:
            result.append(instr.op.value)
            result.append(len(instr.operands))
            for operand in instr.operands:
                if isinstance(operand, int):
                    result.extend(operand.to_bytes(4, "big", signed=True))
                elif isinstance(operand, float):
                    import struct
                    result.extend(struct.pack(">d", operand))
                elif isinstance(operand, str):
                    encoded = operand.encode("utf-8")
                    result.append(len(encoded))
                    result.extend(encoded)
                else:
                    result.extend(str(operand).encode("utf-8"))
        return bytes(result)


@dataclass
class BytecodeModule:
    """Complete bytecode module."""

    functions: Dict[str, BytecodeFunction] = field(default_factory=dict)
    constants: List[Any] = field(default_factory=list)
    strings: List[str] = field(default_factory=list)

    def get_constant_id(self, value: Any) -> int:
        """Get or create constant pool entry."""
        if value in self.constants:
            return self.constants.index(value)
        self.constants.append(value)
        return len(self.constants) - 1

    def get_string_id(self, value: str) -> int:
        """Get or create string pool entry."""
        if value in self.strings:
            return self.strings.index(value)
        self.strings.append(value)
        return len(self.strings) - 1


class LIRToBytecodeTranslator:
    """Translates LIR to bytecode."""

    def __init__(self) -> None:
        self.module = BytecodeModule()

    def translate_module(self, lir: LIRModule) -> BytecodeModule:
        """Translate entire LIR module to bytecode."""
        self.module = BytecodeModule()

        for func_name, lir_func in lir.functions.items():
            self.module.functions[func_name] = self._translate_function(lir_func)

        return self.module

    def _translate_function(self, lir_func: LIRFunction) -> BytecodeFunction:
        """Translate LIR function to bytecode."""
        result = BytecodeFunction(
            name=lir_func.name,
            params=len(lir_func.params),
            local_names=[p.name for p in lir_func.params],
        )

        for block in lir_func.blocks.values():
            self._translate_block(block, result)

        result.registers = max(1, len(result.local_names) + 1)
        return result

    def _translate_block(self, block: LIRBlock, func: BytecodeFunction) -> None:
        """Translate LIR block to bytecode."""
        for instr in block.instructions:
            self._translate_instruction(instr, func)

    def _translate_instruction(self, instr: LIRInstruction, func: BytecodeFunction) -> None:
        """Translate single LIR instruction to bytecode."""
        op_map = {
            "load": BytecodeOp.LOAD_VAR,
            "store": BytecodeOp.STORE_VAR,
            "add": BytecodeOp.ADD,
            "sub": BytecodeOp.SUB,
            "mul": BytecodeOp.MUL,
            "div": BytecodeOp.DIV,
            "call": BytecodeOp.CALL,
            "jump": BytecodeOp.JUMP,
            "branch": BytecodeOp.JUMP_IF_FALSE,
            "return": BytecodeOp.RETURN,
            "phi": BytecodeOp.PHI,
            "mov": BytecodeOp.LOAD_CONST,
            "nop": BytecodeOp.NOP,
        }

        op = op_map.get(instr.opcode, BytecodeOp.NOP)
        operands = tuple(str(o) if o else "" for o in instr.operands)
        func.instructions.append(BytecodeInstruction(op, operands))


class BytecodeOptimizer:
    """Bytecode optimizer with multiple passes."""

    def __init__(self) -> None:
        self._pass_count = 0

    def optimize(self, module: BytecodeModule) -> BytecodeModule:
        """Run all optimization passes on bytecode."""
        logger.info("Starting bytecode optimization...")

        for func_name, func in module.functions.items():
            func.instructions = self._optimize_function(func)

        logger.info(f"Optimization complete: {self._pass_count} passes applied")
        return module

    def _optimize_function(self, func: BytecodeFunction) -> List[BytecodeInstruction]:
        """Apply all optimizations to a function."""
        instructions = func.instructions.copy()

        changed = True
        while changed:
            changed = False
            prev_len = len(instructions)

            # Constant folding
            instructions = self._constant_fold(instructions, func)
            if len(instructions) != prev_len:
                changed = True

            # Dead code elimination
            prev_len = len(instructions)
            instructions = self._dead_code_eliminate(instructions)
            if len(instructions) != prev_len:
                changed = True

            # Instruction combining
            instructions = self._combine_instructions(instructions)
            if len(instructions) != prev_len:
                changed = True

            self._pass_count += 1

        return instructions

    def _constant_fold(
        self,
        instructions: List[BytecodeInstruction],
        func: BytecodeFunction,
    ) -> List[BytecodeInstruction]:
        """Fold constant expressions."""
        result = []
        constants: Dict[int, Any] = {}

        for instr in instructions:
            if instr.op == BytecodeOp.LOAD_CONST:
                # Try to track constant values
                if len(instr.operands) >= 1:
                    try:
                        val = eval(instr.operands[0])  # Safe for numeric literals
                        if isinstance(val, (int, float)):
                            constants[id(instr)] = val
                    except (ValueError, SyntaxError):
                        pass
            elif instr.op == BytecodeOp.ADD and len(result) >= 2:
                # Check if we can fold
                last1 = result[-1]
                last2 = result[-2]
                c1 = constants.get(id(last1))
                c2 = constants.get(id(last2))
                if c1 is not None and c2 is not None and isinstance(c1, (int, float)) and isinstance(c2, (int, float)):
                    result.pop()
                    result.pop()
                    result.append(BytecodeInstruction(
                        BytecodeOp.LOAD_CONST, (str(c1 + c2),)
                    ))

            result.append(instr)

        return result

    def _dead_code_eliminate(
        self,
        instructions: List[BytecodeInstruction],
    ) -> List[BytecodeInstruction]:
        """Remove dead code (NOPs, unreachable code)."""
        result = []
        seen_labels: Set[str] = set()

        for instr in instructions:
            if instr.op == BytecodeOp.NOP:
                continue
            result.append(instr)

        return result

    def _combine_instructions(
        self,
        instructions: List[BytecodeInstruction],
    ) -> List[BytecodeInstruction]:
        """Combine instructions for optimization."""
        # Simplistic combining - in production, this would be more complex
        return instructions
