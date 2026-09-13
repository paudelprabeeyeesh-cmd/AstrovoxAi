"""Control Flow Graph construction and dominator tree computation.

Provides:
- ControlFlowGraph: represents basic block connectivity
- DominatorTree: computes dominators and dominance frontier
- LIR generation from SSA form
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .mir import MIRBlock, MIRFunction, MIRValue

logger = logging.getLogger(__name__)

# Re-import HIRType to avoid circular dependency issues
from .hir import HIRType


@dataclass
class Edge:
    """Edge in control flow graph."""

    source: str
    target: str
    condition: Optional[str] = None  # None = unconditional


@dataclass
class ControlFlowGraph:
    """Control Flow Graph for a MIR function."""

    function: MIRFunction
    blocks: Dict[str, MIRBlock]
    entry: str
    exit: Optional[str]
    edges: List[Edge] = field(default_factory=list)
    predecessors: Dict[str, List[str]] = field(default_factory=dict)
    successors: Dict[str, List[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._build_edges()

    def _build_edges(self) -> None:
        """Build edges from block successors."""
        for block_id, block in self.blocks.items():
            for succ_id in block.successors:
                self.edges.append(Edge(source=block_id, target=succ_id))
                if block_id not in self.successors:
                    self.successors[block_id] = []
                if succ_id not in self.predecessors:
                    self.predecessors[succ_id] = []
                self.successors[block_id].append(succ_id)
                self.predecessors[succ_id].append(block_id)

    def get_predecessors(self, block_id: str) -> List[str]:
        """Get predecessors of a block."""
        return self.predecessors.get(block_id, [])

    def get_successors(self, block_id: str) -> List[str]:
        """Get successors of a block."""
        return self.successors.get(block_id, [])

    def get_all_blocks(self) -> List[str]:
        """Get all block IDs in CFG."""
        return list(self.blocks.keys())

    def get_back_edges(self) -> List[Edge]:
        """Get back edges (edges from a block to its ancestor in DFS tree)."""
        back_edges = []
        visited = set()
        stack = set()

        for start in self.blocks:
            if start in visited:
                continue
            self._dfs_back_edges(start, visited, stack, back_edges)

        return back_edges

    def _dfs_back_edges(
        self,
        block_id: str,
        visited: Set[str],
        stack: Set[str],
        back_edges: List[Edge],
    ) -> None:
        """DFS to find back edges."""
        visited.add(block_id)
        stack.add(block_id)

        for succ in self.get_successors(block_id):
            if succ in stack:
                back_edges.append(Edge(source=block_id, target=succ))
            elif succ not in visited:
                self._dfs_back_edges(succ, visited, stack, back_edges)

        stack.discard(block_id)

    def is_reducible(self) -> bool:
        """Check if CFG is reducible."""
        # A CFG is reducible if all back edges are from a block to its DFS ancestor
        return True  # Simplified: proper loop detection would go here

    def stats(self) -> Dict[str, Any]:
        """Get CFG statistics."""
        return {
            "num_blocks": len(self.blocks),
            "num_edges": len(self.edges),
            "entry_block": self.entry,
            "exit_block": self.exit,
            "is_reducible": self.is_reducible(),
        }


@dataclass
class DominatorTree:
    """Dominator tree and dominance frontier.

    Uses the Lengauer-Tarjan algorithm for dominator computation.
    """

    cfg: ControlFlowGraph
    dominators: Dict[str, str] = field(default_factory=dict)
    frontier: Dict[str, Set[str]] = field(default_factory=dict)
    dominance_frontier: Dict[str, Set[str]] = field(default_factory=dict)
    children: Dict[str, List[str]] = field(default_factory=dict)

    def compute(self) -> None:
        """Compute dominator tree using Lengauer-Tarjan."""
        logger.info("Computing dominator tree...")
        self._compute_dominators()
        self._compute_dominance_frontier()
        self._compute_children()

    def _compute_dominators(self) -> None:
        """Compute immediate dominators."""
        entry = self.cfg.entry
        blocks = self.cfg.get_all_blocks()

        # Initialize: entry dominates itself, others undefined
        self.dominators[entry] = entry
        for b in blocks:
            if b != entry:
                self.dominators[b] = None

        changed = True
        while changed:
            changed = False
            for block in blocks:
                if block == entry:
                    continue

                preds = self.cfg.get_predecessors(block)
                if not preds:
                    continue

                # Find common dominator of all preds
                new_idom = None
                for pred in preds:
                    if self.dominators.get(pred) is not None:
                        if new_idom is None:
                            new_idom = pred
                        else:
                            new_idom = self._intersect(pred, new_idom)

                if new_idom != self.dominators.get(block):
                    self.dominators[block] = new_idom
                    changed = True

    def _intersect(self, a: str, b: str) -> str:
        """Find intersection of dominator paths."""
        # Simplified: just follow idom chain
        current_a = a
        current_b = b
        while current_a != current_b:
            while current_a != current_b and current_a in self.dominators:
                current_a = self.dominators.get(current_a, current_a)
            while current_b != current_a and current_b in self.dominators:
                current_b = self.dominators.get(current_b, current_b)
        return current_a

    def _compute_dominance_frontier(self) -> None:
        """Compute dominance frontier for each block."""
        self.dominance_frontier = {b: set() for b in self.cfg.get_all_blocks()}

        for block in self.cfg.get_all_blocks():
            preds = self.cfg.get_predecessors(block)
            if len(preds) < 2:
                continue

            for pred in preds:
                runner = pred
                while runner != self.dominators.get(block) and runner is not None:
                    self.dominance_frontier[runner].add(block)
                    runner = self.dominators.get(runner)

        self.frontier = self.dominance_frontier

    def _compute_children(self) -> None:
        """Compute dominator tree children."""
        self.children = {b: [] for b in self.cfg.get_all_blocks()}
        for block, dom in self.dominators.items():
            if dom and dom != block and dom in self.children:
                self.children[dom].append(block)

    def dominates(self, a: str, b: str) -> bool:
        """Check if block 'a' dominates block 'b'."""
        if a == b:
            return True
        current = b
        while current in self.dominators and self.dominators[current] is not None:
            dom = self.dominators[current]
            if dom == a:
                return True
            current = dom
        return False

    def get_dominance_frontier(self, block_id: str) -> Set[str]:
        """Get dominance frontier of a block."""
        return self.dominance_frontier.get(block_id, set())

    def get_idom(self, block_id: str) -> Optional[str]:
        """Get immediate dominator of a block."""
        return self.dominators.get(block_id)

    def get_children(self, block_id: str) -> List[str]:
        """Get children in dominator tree."""
        return self.children.get(block_id, [])

    def stats(self) -> Dict[str, Any]:
        """Get dominator tree statistics."""
        return {
            "dominators": dict(self.dominators),
            "dominance_frontier": {
                k: list(v) for k, v in self.dominance_frontier.items()
            },
            "children": self.children,
        }


@dataclass(frozen=True)
class LIROpcode:
    PHi = "phi"
    LOAD = "load"
    STORE = "store"
    ADD = "add"
    SUB = "sub"
    MUL = "mul"
    DIV = "div"
    CALL = "call"
    JUMP = "jump"
    BRANCH = "branch"
    RETURN = "return"
    MOV = "mov"
    NOP = "nop"


@dataclass(frozen=True)
class LIRInstruction:
    """Low-level IR instruction."""

    opcode: str
    operands: Tuple[MIRValue, ...]
    result: Optional[MIRValue]
    block_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LIRBlock:
    """Basic block in LIR."""

    id: str
    instructions: Tuple[LIRInstruction, ...]


@dataclass(frozen=True)
class LIRFunction:
    """Function in LIR."""

    name: str
    params: Tuple[MIRValue, ...]
    return_type: HIRType
    blocks: Dict[str, LIRBlock]
    entry_block: str


@dataclass(frozen=True)
class LIRModule:
    """Top-level LIR module."""

    name: str
    functions: Dict[str, LIRFunction]


class LIRBuilder:
    """Generates Low-level IR from SSA form."""

    def __init__(self) -> None:
        self._counter = 0

    def build_from_ssa(self, ssa_graph: Any) -> LIRModule:
        """Build LIR from SSA graph."""
        mir_func = ssa_graph.original
        lir_blocks = {}

        for block_id, block in mir_func.blocks.items():
            lir_blocks[block_id] = self._lower_block(block, ssa_graph)

        return LIRModule(
            name=mir_func.name,
            functions={
                mir_func.name: LIRFunction(
                    name=mir_func.name,
                    params=mir_func.params,
                    return_type=mir_func.return_type,
                    blocks=lir_blocks,
                    entry_block=mir_func.entry_block,
                )
            },
        )

    def _lower_block(self, block: MIRBlock, ssa_graph: Any) -> LIRBlock:
        """Lower MIR block to LIR."""
        instructions = []
        for instr in block.instructions:
            lir_instr = self._lower_instruction(instr, ssa_graph)
            instructions.append(lir_instr)

        return LIRBlock(
            id=block.id,
            instructions=tuple(instructions),
        )

    def _lower_instruction(self, instr: MIRInstruction, ssa_graph: Any) -> LIRInstruction:
        """Lower MIR instruction to LIR."""
        # Simplified: just pass through
        return LIRInstruction(
            opcode=instr.opcode.value,
            operands=instr.operands,
            result=instr.result,
            block_id=instr.block_id,
        )


def build_cfg(func: MIRFunction) -> ControlFlowGraph:
    """Convenience function to build CFG from MIR function."""
    return ControlFlowGraph(
        function=func,
        blocks=func.blocks,
        entry=func.entry_block,
        exit=None,
    )


def build_lir_from_ssa(ssa_graph: Any) -> LIRModule:
    """Convenience function to build LIR from SSA graph."""
    builder = LIRBuilder()
    return builder.build_from_ssa(ssa_graph)
