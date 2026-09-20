"""Disjoint-set (Union-Find) data structure for address clustering."""

from __future__ import annotations

from collections import defaultdict
from typing import Generic, TypeVar

T = TypeVar("T")


class DisjointSet(Generic[T]):
    """Union-Find with path compression and union by rank."""

    def __init__(self) -> None:
        self.parent: dict[T, T] = {}
        self.rank: dict[T, int] = {}
        self.size: dict[T, int] = {}

    def add(self, item: T) -> None:
        """Register an item if not already present."""
        if item not in self.parent:
            self.parent[item] = item
            self.rank[item] = 0
            self.size[item] = 1

    def find(self, item: T) -> T:
        """Find the root representative of an item with path compression."""
        if item not in self.parent:
            self.add(item)
            return item

        # Path compression
        root = item
        while self.parent[root] != root:
            root = self.parent[root]

        curr = item
        while curr != root:
            nxt = self.parent[curr]
            self.parent[curr] = root
            curr = nxt

        return root

    def union(self, x: T, y: T) -> bool:
        """Merge the sets containing x and y. Returns True if sets were merged, False if already in same set."""
        root_x = self.find(x)
        root_y = self.find(y)

        if root_x == root_y:
            return False

        # Union by rank
        if self.rank[root_x] < self.rank[root_y]:
            self.parent[root_x] = root_y
            self.size[root_y] += self.size[root_x]
        elif self.rank[root_x] > self.rank[root_y]:
            self.parent[root_y] = root_x
            self.size[root_x] += self.size[root_y]
        else:
            self.parent[root_y] = root_x
            self.rank[root_x] += 1
            self.size[root_x] += self.size[root_y]

        return True

    def connected(self, x: T, y: T) -> bool:
        """Return whether x and y belong to the same component."""
        if x not in self.parent or y not in self.parent:
            return False
        return self.find(x) == self.find(y)

    def component_size(self, item: T) -> int:
        """Return the size of the component containing item."""
        root = self.find(item)
        return self.size.get(root, 1)

    def get_components(self) -> dict[T, list[T]]:
        """Return all disjoint components grouped by root representative."""
        components: dict[T, list[T]] = defaultdict(list)
        for item in self.parent:
            root = self.find(item)
            components[root].append(item)
        return dict(components)

    def count_components(self) -> int:
        """Return total number of disjoint sets."""
        roots = {self.find(item) for item in self.parent}
        return len(roots)

    def __len__(self) -> int:
        return len(self.parent)
