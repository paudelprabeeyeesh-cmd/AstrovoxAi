from __future__ import annotations

import bisect
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Block:
    pointer: int
    size: int
    free: bool = False
    block_id: Optional[str] = None
    coalesced_with: Optional[str] = None

    @property
    def end(self) -> int:
        return self.pointer + self.size


class MemoryPoolAllocator:
    def __init__(self, total_size: int) -> None:
        self.total_size = total_size
        self.blocks: List[Block] = [Block(pointer=0, size=total_size, free=True)]
        self.block_map: Dict[str, Block] = {}
        self.next_pointer = total_size
        self._next_block_id = 0

    def _block_sort_key(self, block: Block) -> int:
        return block.pointer

    def _insert_sorted(self, block: Block) -> None:
        bisect.insort(self.blocks, block, key=self._block_sort_key)

    def _allocate_block(self, size: int) -> Block:
        pointer = 0
        free_pointer = self.total_size - size

        for block in self.blocks:
            if block.free and block.size >= size and block.pointer <= free_pointer:
                pointer = block.pointer
                break
        else:
            raise MemoryError("Insufficient memory for allocation")

        used_block = Block(pointer=pointer, size=size, free=False, block_id=self._new_block_id())
        self._insert_sorted(used_block)
        return used_block

    def _coalesce(self) -> None:
        coalesced: List[Block] = []
        for block in self.blocks:
            if not coalesced:
                coalesced.append(block)
                continue
            prev = coalesced[-1]
            if prev.free and block.free:
                prev_cw = prev.coalesced_with or None
                block_cw = block.coalesced_with or None
                merged_cw: Optional[str]
                if prev_cw is None and block_cw is None:
                    merged_cw = None
                elif prev_cw is None:
                    merged_cw = block_cw
                elif block_cw is None:
                    merged_cw = prev_cw
                else:
                    merged_cw = ",".join([prev_cw, block_cw])
                merged = Block(
                    pointer=prev.pointer,
                    size=prev.size + block.size,
                    free=True,
                    coalesced_with=merged_cw,
                )
                coalesced[-1] = merged
            else:
                coalesced.append(block)
        self.blocks = coalesced

    def _new_block_id(self) -> str:
        self._next_block_id += 1
        return f"block-{self._next_block_id}"

    def allocate(self, size: int) -> Optional[str]:
        if size <= 0:
            return None
        for idx, block in enumerate(self.blocks):
            if block.free and block.size >= size:
                used_block = Block(pointer=block.pointer, size=size, free=False, block_id=self._new_block_id())
                if block.size > size:
                    free_block = Block(pointer=block.pointer + size, size=block.size - size, free=True)
                    self.blocks[idx] = free_block
                    self._insert_sorted(used_block)
                else:
                    self.blocks[idx] = used_block
                self.block_map[used_block.block_id] = used_block
                return used_block.block_id
        return None

    def free(self, block_id: str) -> bool:
        if block_id not in self.block_map:
            return False
        block = self.block_map[block_id]
        block.free = True
        del self.block_map[block_id]
        self._coalesce()
        return True

    def get_used_blocks(self) -> List[Block]:
        return [block for block in self.blocks if not block.free]

    def get_free_blocks(self) -> List[Block]:
        return [block for block in self.blocks if block.free]

    def get_fragmentation(self) -> float:
        free_blocks = self.get_free_blocks()
        if not free_blocks:
            return 0.0
        total_free = sum(block.size for block in free_blocks)
        largest_free = max(block.size for block in free_blocks)
        return 1.0 - (largest_free / total_free) if total_free else 0.0

    def used_size(self) -> int:
        return sum(block.size for block in self.blocks if not block.free)

    def free_size(self) -> int:
        return sum(block.size for block in self.blocks if block.free)

    def status(self) -> dict:
        return {
            "total_size": self.total_size,
            "used_size": self.used_size(),
            "free_size": self.free_size(),
            "fragmentation": self.get_fragmentation(),
            "block_count": len(self.blocks),
        }
