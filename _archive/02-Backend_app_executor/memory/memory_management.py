"""Advanced Memory Management System.

Provides:
1. Generational Garbage Collector (Young/Old generations)
2. Arena Allocator for fast allocation/deallocation
3. Reference Counting for immediate cleanup
4. Memory pool management
5. Object lifecycle tracking
"""

from __future__ import annotations

import heapq
import threading
import time
import weakref
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = __import__('logging').getLogger(__name__)


class GCTrigger(str, Enum):
    """Garbage collection triggers."""
    ALLOCATION_THRESHOLD = "allocation_threshold"
    TIME_INTERVAL = "time_interval"
    MANUAL = "manual"


@dataclass
class GCStats:
    """Garbage collection statistics."""
    collections_young: int = 0
    collections_old: int = 0
    objects_collected: int = 0
    memory_freed: int = 0
    pause_time: float = 0.0
    last_collection: float = 0.0


@dataclass
class ObjectHeader:
    """Object header for GC tracking."""
    obj_id: int
    size: int
    generation: int = 0  # 0 = young, 1 = old
    marked: bool = False
    refcount: int = 0
    next_free: Optional[int] = None
    timestamp: float = field(default_factory=time.time)


class Arena:
    """Arena allocator for fast allocation/deallocation of similar-sized objects."""

    def __init__(self, object_size: int, chunk_size: int = 4096):
        self.object_size = object_size
        self.chunk_size = chunk_size
        self.objects_per_chunk = chunk_size // object_size
        self.chunks: List[bytearray] = []
        self.free_list: List[int] = []  # offsets within chunks
        self.allocated: Set[int] = set()
        self._lock = threading.RLock()
        self._allocate_chunk()

    def _allocate_chunk(self) -> None:
        """Allocate a new chunk of memory."""
        chunk = bytearray(self.chunk_size)
        self.chunks.append(chunk)
        # Add all objects in chunk to free list
        for i in range(self.objects_per_chunk):
            offset = i * self.object_size
            self.free_list.append((len(self.chunks) - 1) * self.chunk_size + offset)

    def allocate(self) -> Optional[int]:
        """Allocate an object from the arena."""
        with self._lock:
            if not self.free_list:
                self._allocate_chunk()
            if self.free_list:
                offset = self.free_list.pop()
                self.allocated.add(offset)
                return offset
        return None

    def deallocate(self, offset: int) -> None:
        """Deallocate an object back to the arena."""
        with self._lock:
            if offset in self.allocated:
                self.allocated.remove(offset)
                self.free_list.append(offset)

    def get_object(self, offset: int) -> memoryview:
        """Get memoryview for an object at offset."""
        chunk_index = offset // self.chunk_size
        inner_offset = offset % self.chunk_size
        if 0 <= chunk_index < len(self.chunks):
            return memoryview(self.chunks[chunk_index])[inner_offset:inner_offset + self.object_size]
        raise ValueError(f"Invalid offset: {offset}")

    def stats(self) -> Dict[str, Any]:
        """Get arena statistics."""
        with self._lock:
            return {
                "object_size": self.object_size,
                "chunks": len(self.chunks),
                "allocated": len(self.allocated),
                "free": len(self.free_list),
                "utilization": len(self.allocated) / (len(self.chunks) * self.objects_per_chunk) if self.chunks else 0
            }


class GenerationalGC:
    """Generational garbage collector with young/old generations."""

    def __init__(self, young_threshold: int = 1000, old_threshold: int = 10000):
        self.young_threshold = young_threshold
        self.old_threshold = old_threshold
        self.young_gen: Set[int] = set()
        self.old_gen: Set[int] = set()
        self.objects: Dict[int, Any] = {}  # obj_id -> object
        self.headers: Dict[int, ObjectHeader] = {}  # obj_id -> header
        self.roots: Set[int] = set()  # GC roots
        self.stats = GCStats()
        self._lock = threading.RLock()
        self._next_obj_id = 1
        self._last_gc_young = time.time()
        self._last_gc_old = time.time()

    def allocate(self, obj: Any, size: int = 0) -> int:
        """Allocate a new object and return its ID."""
        with self._lock:
            obj_id = self._next_obj_id
            self._next_obj_id += 1

            header = ObjectHeader(
                obj_id=obj_id,
                size=max(size, 1),
                generation=0  # Start in young generation
            )

            self.objects[obj_id] = obj
            self.headers[obj_id] = header
            self.young_gen.add(obj_id)

            # Trigger GC if needed
            if len(self.young_gen) >= self.young_threshold:
                self.collect_young()

            return obj_id

    def add_root(self, obj_id: int) -> None:
        """Add a GC root."""
        with self._lock:
            self.roots.add(obj_id)

    def remove_root(self, obj_id: int) -> None:
        """Remove a GC root."""
        with self._lock:
            self.roots.discard(obj_id)

    def _mark_from_roots(self) -> Set[int]:
        """Mark all reachable objects from roots."""
        marked = set()
        stack = list(self.roots)

        while stack:
            obj_id = stack.pop()
            if obj_id in marked or obj_id not in self.objects:
                continue
            marked.add(obj_id)

            # Trace references (simplified - in practice would scan object fields)
            obj = self.objects.get(obj_id)
            if isinstance(obj, (list, tuple, set)):
                for item in obj:
                    if isinstance(item, int) and item in self.objects:
                        stack.append(item)
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(k, int) and k in self.objects:
                        stack.append(k)
                    if isinstance(v, int) and v in self.objects:
                        stack.append(v)

        return marked

    def collect_young(self) -> None:
        """Collect young generation."""
        start_time = time.time()
        with self._lock:
            logger.debug("Starting young generation GC...")

            # Mark phase
            marked = self._mark_from_roots()

            # Sweep young generation
            collected = []
            promoted = []

            for obj_id in list(self.young_gen):
                header = self.headers[obj_id]
                if obj_id not in marked:
                    # Collect unreachable object
                    collected.append(obj_id)
                    del self.objects[obj_id]
                    del self.headers[obj_id]
                else:
                    # Mark as live
                    header.marked = True
                    # Promote to old generation if survived enough collections
                    if header.generation < 1:  # Simple promotion rule
                        header.generation = 1
                        self.young_gen.remove(obj_id)
                        self.old_gen.add(obj_id)
                        promoted.append(obj_id)

            # Update stats
            self.stats.collections_young += 1
            self.stats.objects_collected += len(collected)
            self.stats.memory_freed += sum(self.headers[obj_id].size for obj_id in collected)
            self.stats.pause_time += time.time() - start_time
            self.stats.last_collection = time.time()
            self._last_gc_young = time.time()

            logger.debug(f"Young GC collected {len(collected)}, promoted {len(promoted)}")

    def collect_old(self) -> None:
        """Collect old generation (full GC)."""
        start_time = time.time()
        with self._lock:
            logger.debug("Starting old generation GC (full)...")

            # Mark phase
            marked = self._mark_from_roots()

            # Sweep old generation
            collected = []

            for obj_id in list(self.old_gen):
                header = self.headers[obj_id]
                if obj_id not in marked:
                    # Collect unreachable object
                    collected.append(obj_id)
                    del self.objects[obj_id]
                    del self.headers[obj_id]
                else:
                    # Reset mark for next cycle
                    header.marked = False

            # Update stats
            self.stats.collections_old += 1
            self.stats.objects_collected += len(collected)
            self.stats.memory_freed += sum(self.headers[obj_id].size for obj_id in collected)
            self.stats.pause_time += time.time() - start_time
            self.stats.last_collection = time.time()
            self._last_gc_old = time.time()

            logger.debug(f"Old GC collected {len(collected)}")

    def collect(self, generation: Optional[int] = None) -> None:
        """Trigger garbage collection."""
        if generation == 0 or generation is None:
            self.collect_young()
        if generation == 1 or generation is None:
            self.collect_old()

    def get_stats(self) -> Dict[str, Any]:
        """Get GC statistics."""
        with self._lock:
            return {
                "collections_young": self.stats.collections_young,
                "collections_old": self.stats.collections_old,
                "objects_collected": self.stats.objects_collected,
                "memory_freed": self.stats.memory_freed,
                "pause_time": self.stats.pause_time,
                "last_collection": self.stats.last_collection,
                "young_gen_size": len(self.young_gen),
                "old_gen_size": len(self.old_gen),
                "total_objects": len(self.objects),
            }


class ReferenceCounter:
    """Reference counting for immediate object cleanup."""

    def __init__(self):
        self.refs: Dict[int, int] = {}
        self._lock = threading.RLock()
        self._cleanup_callbacks: Dict[int, List[Callable]] = {}

    def add_reference(self, obj_id: int) -> None:
        """Add a reference to an object."""
        with self._lock:
            self.refs[obj_id] = self.refs.get(obj_id, 0) + 1

    def remove_reference(self, obj_id: int) -> bool:
        """Remove a reference. Returns True if object should be deleted."""
        with self._lock:
            if obj_id not in self.refs:
                return False
            self.refs[obj_id] -= 1
            if self.refs[obj_id] <= 0:
                del self.refs[obj_id]
                # Run cleanup callbacks
                if obj_id in self._cleanup_callbacks:
                    for callback in self._cleanup_callbacks[obj_id]:
                        try:
                            callback()
                        except Exception as e:
                            logger.error(f"Cleanup callback failed: {e}")
                    del self._cleanup_callbacks[obj_id]
                return True
            return False

    def set_cleanup_callback(self, obj_id: int, callback: Callable) -> None:
        """Set cleanup callback for when object is deleted."""
        with self._lock:
            if obj_id not in self._cleanup_callbacks:
                self._cleanup_callbacks[obj_id] = []
            self._cleanup_callbacks[obj_id].append(callback)

    def get_refcount(self, obj_id: int) -> int:
        """Get current reference count."""
        with self._lock:
            return self.refs.get(obj_id, 0)

    def stats(self) -> Dict[str, Any]:
        """Get reference counting statistics."""
        with self._lock:
            total_refs = sum(self.refs.values())
            return {
                "tracked_objects": len(self.refs),
                "total_references": total_refs,
                "avg_refcount": total_refs / len(self.refs) if self.refs else 0
            }


class MemoryManager:
    """Unified memory manager combining GC, arena allocation, and reference counting."""

    def __init__(self):
        self.gc = GenerationalGC()
        self.refcount = ReferenceCounter()
        self.arenas: Dict[int, Arena] = {}  # size -> Arena
        self._lock = threading.RLock()
        self._object_to_size: Dict[int, int] = {}

    def allocate_object(self, obj: Any, size: int = 0) -> int:
        """Allocate an object with GC tracking."""
        obj_id = self.gc.allocate(obj, size)
        self._object_to_size[obj_id] = max(size, 1)
        return obj_id

    def allocate_arena(self, object_size: int) -> Arena:
        """Get or create an arena for object size."""
        with self._lock:
            if object_size not in self.arenas:
                self.arenas[object_size] = Arena(object_size)
            return self.arenas[object_size]

    def add_reference(self, obj_id: int) -> None:
        """Add a reference (for refcounting)."""
        self.refcount.add_reference(obj_id)

    def remove_reference(self, obj_id: int) -> bool:
        """Remove a reference. Returns True if object was deleted."""
        return self.refcount.remove_reference(obj_id)

    def add_root(self, obj_id: int) -> None:
        """Add a GC root."""
        self.gc.add_root(obj_id)

    def remove_root(self, obj_id: int) -> None:
        """Remove a GC root."""
        self.gc.remove_root(obj_id)

    def collect_garbage(self, generation: Optional[int] = None) -> None:
        """Trigger garbage collection."""
        self.gc.collect(generation)

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        with self._lock:
            gc_stats = self.gc.get_stats()
            ref_stats = self.refcount.stats()
            arena_stats = {size: arena.stats() for size, arena in self.arenas.items()}

            return {
                "gc": gc_stats,
                "reference_counting": ref_stats,
                "arenas": arena_stats,
                "total_tracked_objects": len(self._object_to_size),
            }


# Global memory manager instance
memory_manager = MemoryManager()

# Convenience functions
def allocate(obj: Any, size: int = 0) -> int:
    """Allocate an object."""
    return memory_manager.allocate_object(obj, size)

def retain(obj_id: int) -> None:
    """Increase reference count."""
    memory_manager.add_reference(obj_id)

def release(obj_id: int) -> bool:
    """Decrease reference count, returns True if object freed."""
    return memory_manager.remove_reference(obj_id)

def gc_collect(generation: Optional[int] = None) -> None:
    """Trigger garbage collection."""
    memory_manager.collect_garbage(generation)

def get_memory_stats() -> Dict[str, Any]:
    """Get memory statistics."""
    return memory_manager.get_stats()