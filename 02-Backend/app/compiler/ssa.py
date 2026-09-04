"""Static Single Assignment (SSA) transformation for MIR.

Converts MIR into SSA form using the standard algorithm:
1. Compute dominator tree
2. Insert phi functions at dominance frontiers
3. Rename variables to ensure each assignment has a unique name
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .cfg import ControlFlowGraph, DominatorTree
from .mir import MIRBlock, MIRFunction, MIRInstruction, MIROpcode, MIRValue

logger = logging.getLogger(__name__)


@dataclass
class SSAGraph:
    """SSA representation of a function."""

    original: MIRFunction
    cfg: ControlFlowGraph
    dominator_tree: DominatorTree
    phi_functions: Dict[str, List[MIRInstruction]] = field(default_factory=dict)
    renamed_blocks: Dict[str, MIRBlock] = field(default_factory=dict)
    variable_mappings: Dict[str, List[str]] = field(default_factory=dict)


class SSATransformer:
    """Performs SSA transformation on MIR."""

    def __init__(self) -> None:
        self._stacks: Dict[str, List[str]] = defaultdict(list)
        self._counters: Dict[str, int] = defaultdict(int)

    def transform(self, func: MIRFunction) -> SSAGraph:
        """Transform MIR function into SSA form."""
        logger.info(f"Transforming function '{func.name}' to SSA form...")

        cfg = ControlFlowGraph(func)
        dom_tree = DominatorTree(cfg)
        dom_tree.compute()

        ssa_graph = SSAGraph(
            original=func,
            cfg=cfg,
            dominator_tree=dom_tree,
        )

        self._insert_phi_functions(ssa_graph)
        self._rename_variables(ssa_graph)

        return ssa_graph

    def _insert_phi_functions(self, graph: SSAGraph) -> None:
        """Insert phi functions at dominance frontiers."""
        func = graph.original
        df = graph.dominator_tree.dominance_frontier

        for block_id in func.blocks:
            preds = graph.cfg.get_predecessors(block_id)
            if len(preds) < 2:
                continue

            for var_name in self._get_live_out(block_id, func):
                phi_operands = []
                for pred_id in preds:
                    phi_operands.append(MIRValue(name=var_name, type=HIRType("any")))

                phi_instr = MIRInstruction(
                    opcode=MIROpcode.PHI,
                    operands=tuple(phi_operands),
                    result=MIRValue(name=f"{var_name}_phi_{block_id}", type=HIRType("any")),
                    block_id=block_id,
                )

                if block_id not in graph.phi_functions:
                    graph.phi_functions[block_id] = []
                graph.phi_functions[block_id].append(phi_instr)

        logger.info(f"Inserted {sum(len(v) for v in graph.phi_functions.values())} phi functions")

    def _get_live_out(self, block_id: str, func: MIRFunction) -> Set[str]:
        """Get variables that are live out of a block."""
        live = set()
        for instr in func.blocks[block_id].instructions:
            live.update(op.name for op in instr.operands if op.name and not op.is_constant)
        return live

    def _rename_variables(self, graph: SSAGraph) -> None:
        """Rename variables using depth-first traversal."""
        entry = graph.original.entry_block
        self._visit(entry, graph)

    def _visit(self, block_id: str, graph: SSAGraph) -> None:
        """Visit a block for variable renaming."""
        block = graph.original.blocks[block_id]
        new_instructions = []

        for instr in block.instructions:
            new_operands = tuple(
                self._rename_operand(op) for op in instr.operands
            )

            new_result = instr.result
            if instr.result and instr.opcode != MIROpcode.PHI:
                new_result = self._new_name(instr.result.name)

            new_instr = MIRInstruction(
                opcode=instr.opcode,
                operands=new_operands,
                result=new_result,
                block_id=block_id,
            )
            new_instructions.append(new_instr)

        new_block = MIRBlock(
            id=block_id,
            instructions=tuple(new_instructions),
            terminator=block.terminator,
            predecessors=block.predecessors,
            successors=block.successors,
        )
        graph.renamed_blocks[block_id] = new_block

        for succ_id in block.successors:
            self._visit(succ_id, graph)

    def _rename_operand(self, value: MIRValue) -> MIRValue:
        """Rename a single operand to its current SSA name."""
        if value.is_constant:
            return value
        stack = self._stacks.get(value.name, [])
        if stack:
            return MIRValue(name=stack[-1], type=value.type, is_constant=value.is_constant)
        return value

    def _new_name(self, var_name: str) -> MIRValue:
        """Create a new SSA name for a variable assignment."""
        counter = self._counters[var_name]
        self._counters[var_name] = counter + 1
        new_name = f"{var_name}_{counter}"
        self._stacks[var_name].append(new_name)
        return MIRValue(name=new_name, type=HIRType("any"))


def build_ssa(func: MIRFunction) -> SSAGraph:
    """Convenience function to build SSA from MIR function."""
    transformer = SSATransformer()
    return transformer.transform(func)


from .hir import HIRType
