"""Three-dimensional flat-array Barnes-Hut gravity solver."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, cast

import numpy as np
import numpy.typing as npt
from numba import njit, prange

from gravity.core.state import FloatArray
from gravity.physics.validation import (
    prepare_acceleration_output,
    validate_softening,
    validate_solver_inputs,
)

DEFAULT_THETA = 0.7
MIN_THETA = 0.3
MAX_THETA = 1.2
DEFAULT_LEAF_CAPACITY = 8
DEFAULT_MAX_DEPTH = 32
MIN_LEAF_CAPACITY = 1
MAX_LEAF_CAPACITY = 64
MIN_MAX_DEPTH = 1
MAX_MAX_DEPTH = 64
PARALLEL_PARTICLE_THRESHOLD = 2_048

type IntArray = npt.NDArray[np.int32]
type DepthArray = npt.NDArray[np.uint8]


def _bounded_real(value: float, name: str, lower: float, upper: float) -> float:
    try:
        converted = float(value)
    except (TypeError, ValueError) as error:
        raise TypeError(f"{name} must be a real number") from error
    if not math.isfinite(converted) or not lower <= converted <= upper:
        raise ValueError(f"{name} must be finite and between {lower} and {upper}")
    return converted


def _bounded_integer(value: int, name: str, lower: int, upper: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer")
    converted = int(value)
    if not lower <= converted <= upper:
        raise ValueError(f"{name} must be between {lower} and {upper}")
    return converted


@dataclass(frozen=True, slots=True)
class FlatOctree:
    """Immutable flat representation consumed directly by compiled traversal."""

    centers: FloatArray = field(repr=False)
    half_sizes: FloatArray = field(repr=False)
    children: IntArray = field(repr=False)
    starts: IntArray = field(repr=False)
    counts: IntArray = field(repr=False)
    depths: DepthArray = field(repr=False)
    masses: FloatArray = field(repr=False)
    centers_of_mass: FloatArray = field(repr=False)
    particle_order: IntArray = field(repr=False)
    inverse_order: IntArray = field(repr=False)
    leaf_capacity: int
    depth_limit: int

    def __post_init__(self) -> None:
        node_count = int(self.half_sizes.shape[0])
        particle_count = int(self.particle_order.shape[0])
        expected_shapes = {
            "centers": (node_count, 3),
            "children": (node_count, 8),
            "starts": (node_count,),
            "counts": (node_count,),
            "depths": (node_count,),
            "masses": (node_count,),
            "centers_of_mass": (node_count, 3),
            "inverse_order": (particle_count,),
        }
        arrays: dict[str, np.ndarray[Any, Any]] = {
            "centers": self.centers,
            "half_sizes": self.half_sizes,
            "children": self.children,
            "starts": self.starts,
            "counts": self.counts,
            "depths": self.depths,
            "masses": self.masses,
            "centers_of_mass": self.centers_of_mass,
            "particle_order": self.particle_order,
            "inverse_order": self.inverse_order,
        }
        if node_count < 1 or particle_count < 1:
            raise ValueError("an octree requires at least one node and particle")
        for name, expected in expected_shapes.items():
            if arrays[name].shape != expected:
                raise ValueError(f"{name} must have shape {expected}")
        for name, array in arrays.items():
            if not isinstance(array, np.ndarray) or not array.flags.c_contiguous:
                raise ValueError(f"{name} must be a C-contiguous NumPy array")
        for name in ("centers", "half_sizes", "masses", "centers_of_mass"):
            array = arrays[name]
            if array.dtype != np.float64 or not np.all(np.isfinite(array)):
                raise ValueError(f"{name} must contain finite float64 values")
        for name in ("children", "starts", "counts", "particle_order", "inverse_order"):
            if arrays[name].dtype != np.int32:
                raise TypeError(f"{name} must use int32")
        if self.depths.dtype != np.uint8:
            raise TypeError("depths must use uint8")
        if np.any(self.half_sizes < 0.0) or np.any(self.masses <= 0.0):
            raise ValueError("node sizes must be non-negative and node masses positive")
        if self.starts[0] != 0 or self.counts[0] != particle_count or self.depths[0] != 0:
            raise ValueError("root node must contain the complete particle range at depth zero")
        expected_order = np.arange(particle_count, dtype=np.int32)
        if not np.array_equal(np.sort(self.particle_order), expected_order):
            raise ValueError("particle_order must be a permutation")
        if not np.array_equal(self.particle_order[self.inverse_order], expected_order):
            raise ValueError("inverse_order does not invert particle_order")
        if np.any(self.children < -1) or np.any(self.children >= node_count):
            raise ValueError("children contain an invalid node index")
        if np.any(self.starts < 0) or np.any(self.counts < 1):
            raise ValueError("every node must own a non-empty particle range")
        if np.any(self.starts + self.counts > particle_count):
            raise ValueError("a node particle range exceeds particle_order")
        if int(np.max(self.depths)) > self.depth_limit:
            raise ValueError("tree exceeds its configured depth limit")
        for array in arrays.values():
            array.setflags(write=False)

    @property
    def node_count(self) -> int:
        return int(self.half_sizes.shape[0])

    @property
    def particle_count(self) -> int:
        return int(self.particle_order.shape[0])

    @property
    def leaf_mask(self) -> npt.NDArray[np.bool_]:
        return cast(npt.NDArray[np.bool_], np.all(self.children == -1, axis=1))

    @property
    def leaf_count(self) -> int:
        return int(np.count_nonzero(self.leaf_mask))

    @property
    def maximum_depth(self) -> int:
        return int(np.max(self.depths))


@dataclass(frozen=True, slots=True)
class BarnesHutStats:
    """Measurements from one complete tree rebuild and force evaluation."""

    particle_count: int
    node_count: int
    leaf_count: int
    maximum_depth: int
    tree_build_seconds: float
    force_seconds: float
    accepted_node_interactions: int
    direct_particle_interactions: int

    @property
    def total_seconds(self) -> float:
        return self.tree_build_seconds + self.force_seconds


@njit(cache=True, nogil=True)
def _build_topology_kernel(
    positions: FloatArray,
    leaf_capacity: int,
    depth_limit: int,
    node_capacity: int,
) -> tuple[
    FloatArray,
    FloatArray,
    IntArray,
    IntArray,
    IntArray,
    DepthArray,
    IntArray,
    IntArray,
    int,
]:
    particle_count = positions.shape[0]
    centers = np.empty((node_capacity, 3), dtype=np.float64)
    half_sizes = np.empty(node_capacity, dtype=np.float64)
    children = np.full((node_capacity, 8), -1, dtype=np.int32)
    starts = np.empty(node_capacity, dtype=np.int32)
    counts = np.empty(node_capacity, dtype=np.int32)
    depths = np.empty(node_capacity, dtype=np.uint8)
    particle_order = np.arange(particle_count, dtype=np.int32)
    scratch_order = np.empty(particle_count, dtype=np.int32)

    minimum_x = positions[0, 0]
    minimum_y = positions[0, 1]
    minimum_z = positions[0, 2]
    maximum_x = minimum_x
    maximum_y = minimum_y
    maximum_z = minimum_z
    for particle in range(1, particle_count):
        x = positions[particle, 0]
        y = positions[particle, 1]
        z = positions[particle, 2]
        minimum_x = min(minimum_x, x)
        minimum_y = min(minimum_y, y)
        minimum_z = min(minimum_z, z)
        maximum_x = max(maximum_x, x)
        maximum_y = max(maximum_y, y)
        maximum_z = max(maximum_z, z)

    centers[0, 0] = minimum_x * 0.5 + maximum_x * 0.5
    centers[0, 1] = minimum_y * 0.5 + maximum_y * 0.5
    centers[0, 2] = minimum_z * 0.5 + maximum_z * 0.5
    half_x = maximum_x * 0.5 - minimum_x * 0.5
    half_y = maximum_y * 0.5 - minimum_y * 0.5
    half_z = maximum_z * 0.5 - minimum_z * 0.5
    root_half_size = max(half_x, half_y, half_z)
    if root_half_size == 0.0:
        coordinate_scale = max(
            abs(centers[0, 0]),
            abs(centers[0, 1]),
            abs(centers[0, 2]),
            1.0,
        )
        root_half_size = coordinate_scale * np.finfo(np.float64).eps * 8.0
    half_sizes[0] = root_half_size
    starts[0] = 0
    counts[0] = particle_count
    depths[0] = 0

    node_count = 1
    node = 0
    octant_counts = np.empty(8, dtype=np.int32)
    offsets = np.empty(8, dtype=np.int32)
    cursors = np.empty(8, dtype=np.int32)
    while node < node_count:
        node_start = starts[node]
        node_particles = counts[node]
        node_depth = int(depths[node])
        child_half_size = half_sizes[node] * 0.5
        if node_particles <= leaf_capacity or node_depth >= depth_limit or child_half_size == 0.0:
            node += 1
            continue

        for octant in range(8):
            octant_counts[octant] = 0
        center_x = centers[node, 0]
        center_y = centers[node, 1]
        center_z = centers[node, 2]
        for offset in range(node_particles):
            particle = particle_order[node_start + offset]
            octant = 0
            if positions[particle, 0] >= center_x:
                octant |= 1
            if positions[particle, 1] >= center_y:
                octant |= 2
            if positions[particle, 2] >= center_z:
                octant |= 4
            octant_counts[octant] += 1

        occupied = 0
        next_offset = node_start
        for octant in range(8):
            offsets[octant] = next_offset
            cursors[octant] = next_offset
            next_offset += octant_counts[octant]
            if octant_counts[octant] > 0:
                occupied += 1
        if node_count + occupied > node_capacity:
            inverse_order = np.empty(particle_count, dtype=np.int32)
            return (
                centers,
                half_sizes,
                children,
                starts,
                counts,
                depths,
                particle_order,
                inverse_order,
                -1,
            )

        for offset in range(node_particles):
            particle = particle_order[node_start + offset]
            octant = 0
            if positions[particle, 0] >= center_x:
                octant |= 1
            if positions[particle, 1] >= center_y:
                octant |= 2
            if positions[particle, 2] >= center_z:
                octant |= 4
            destination = cursors[octant]
            scratch_order[destination] = particle
            cursors[octant] += 1
        for offset in range(node_particles):
            particle_order[node_start + offset] = scratch_order[node_start + offset]

        for octant in range(8):
            child_particles = octant_counts[octant]
            if child_particles == 0:
                continue
            child = node_count
            node_count += 1
            children[node, octant] = child
            centers[child, 0] = center_x + (child_half_size if octant & 1 else -child_half_size)
            centers[child, 1] = center_y + (child_half_size if octant & 2 else -child_half_size)
            centers[child, 2] = center_z + (child_half_size if octant & 4 else -child_half_size)
            half_sizes[child] = child_half_size
            starts[child] = offsets[octant]
            counts[child] = child_particles
            depths[child] = node_depth + 1
        node += 1

    inverse_order = np.empty(particle_count, dtype=np.int32)
    for ordered_index in range(particle_count):
        inverse_order[particle_order[ordered_index]] = ordered_index
    return (
        centers,
        half_sizes,
        children,
        starts,
        counts,
        depths,
        particle_order,
        inverse_order,
        node_count,
    )


@njit(cache=True, nogil=True)
def _aggregate_mass_kernel(
    positions: FloatArray,
    particle_masses: FloatArray,
    children: IntArray,
    starts: IntArray,
    counts: IntArray,
    particle_order: IntArray,
    node_count: int,
) -> tuple[FloatArray, FloatArray]:
    node_masses = np.empty(node_count, dtype=np.float64)
    centers_of_mass = np.empty((node_count, 3), dtype=np.float64)
    for node in range(node_count - 1, -1, -1):
        has_children = False
        total_mass = 0.0
        weighted_x = 0.0
        weighted_y = 0.0
        weighted_z = 0.0
        for octant in range(8):
            child = children[node, octant]
            if child < 0:
                continue
            has_children = True
            child_mass = node_masses[child]
            total_mass += child_mass
            weighted_x += child_mass * centers_of_mass[child, 0]
            weighted_y += child_mass * centers_of_mass[child, 1]
            weighted_z += child_mass * centers_of_mass[child, 2]
        if not has_children:
            start = starts[node]
            stop = start + counts[node]
            for ordered_index in range(start, stop):
                particle = particle_order[ordered_index]
                particle_mass = particle_masses[particle]
                total_mass += particle_mass
                weighted_x += particle_mass * positions[particle, 0]
                weighted_y += particle_mass * positions[particle, 1]
                weighted_z += particle_mass * positions[particle, 2]
        node_masses[node] = total_mass
        centers_of_mass[node, 0] = weighted_x / total_mass
        centers_of_mass[node, 1] = weighted_y / total_mass
        centers_of_mass[node, 2] = weighted_z / total_mass
    return node_masses, centers_of_mass


def build_octree(
    positions: FloatArray,
    masses: FloatArray,
    *,
    leaf_capacity: int = DEFAULT_LEAF_CAPACITY,
    depth_limit: int = DEFAULT_MAX_DEPTH,
) -> FlatOctree:
    """Build a deterministic octree, growing storage only for pathological inputs."""

    particle_count = validate_solver_inputs(positions, masses)
    safe_leaf_capacity = _bounded_integer(
        leaf_capacity,
        "leaf_capacity",
        MIN_LEAF_CAPACITY,
        MAX_LEAF_CAPACITY,
    )
    safe_depth_limit = _bounded_integer(
        depth_limit,
        "depth_limit",
        MIN_MAX_DEPTH,
        MAX_MAX_DEPTH,
    )
    node_capacity = max(64, 2 * particle_count + safe_depth_limit + 1)
    while True:
        (
            centers,
            half_sizes,
            children,
            starts,
            counts,
            depths,
            particle_order,
            inverse_order,
            node_count,
        ) = _build_topology_kernel(
            positions,
            safe_leaf_capacity,
            safe_depth_limit,
            node_capacity,
        )
        if node_count >= 0:
            break
        node_capacity *= 2
        if node_capacity > np.iinfo(np.int32).max:
            raise MemoryError("octree node storage exceeds the int32 index range")

    trimmed_children = children[:node_count].copy(order="C")
    node_masses, centers_of_mass = _aggregate_mass_kernel(
        positions,
        masses,
        trimmed_children,
        starts,
        counts,
        particle_order,
        node_count,
    )
    return FlatOctree(
        centers=centers[:node_count].copy(order="C"),
        half_sizes=half_sizes[:node_count].copy(order="C"),
        children=trimmed_children,
        starts=starts[:node_count].copy(order="C"),
        counts=counts[:node_count].copy(order="C"),
        depths=depths[:node_count].copy(order="C"),
        masses=np.ascontiguousarray(node_masses),
        centers_of_mass=np.ascontiguousarray(centers_of_mass),
        particle_order=np.ascontiguousarray(particle_order),
        inverse_order=np.ascontiguousarray(inverse_order),
        leaf_capacity=safe_leaf_capacity,
        depth_limit=safe_depth_limit,
    )


@njit(cache=True, nogil=True, inline="always")
def _accumulate_target(
    target: int,
    positions: FloatArray,
    particle_masses: FloatArray,
    centers: FloatArray,
    half_sizes: FloatArray,
    children: IntArray,
    starts: IntArray,
    counts: IntArray,
    node_masses: FloatArray,
    centers_of_mass: FloatArray,
    particle_order: IntArray,
    inverse_order: IntArray,
    theta: float,
    softening_squared: float,
    stack: IntArray,
) -> tuple[float, float, float, int, int]:
    target_x = positions[target, 0]
    target_y = positions[target, 1]
    target_z = positions[target, 2]
    ordered_target = inverse_order[target]
    acceleration_x = 0.0
    acceleration_y = 0.0
    acceleration_z = 0.0
    accepted_nodes = 0
    direct_particles = 0
    stack_size = 1
    stack[0] = 0

    while stack_size > 0:
        stack_size -= 1
        node = stack[stack_size]
        is_leaf = True
        for octant in range(8):
            if children[node, octant] >= 0:
                is_leaf = False
                break

        if is_leaf:
            start = starts[node]
            stop = start + counts[node]
            for ordered_index in range(start, stop):
                other = particle_order[ordered_index]
                if other == target:
                    continue
                dx = positions[other, 0] - target_x
                dy = positions[other, 1] - target_y
                dz = positions[other, 2] - target_z
                softened_squared_distance = dx * dx + dy * dy + dz * dz + softening_squared
                inverse_distance_cubed = 1.0 / (
                    softened_squared_distance * math.sqrt(softened_squared_distance)
                )
                scale = particle_masses[other] * inverse_distance_cubed
                acceleration_x += dx * scale
                acceleration_y += dy * scale
                acceleration_z += dz * scale
                direct_particles += 1
            continue

        dx = centers_of_mass[node, 0] - target_x
        dy = centers_of_mass[node, 1] - target_y
        dz = centers_of_mass[node, 2] - target_z
        squared_distance = dx * dx + dy * dy + dz * dz
        contains_target = starts[node] <= ordered_target < starts[node] + counts[node]
        width = 2.0 * half_sizes[node]
        if (
            not contains_target
            and squared_distance > 0.0
            and width < theta * math.sqrt(squared_distance)
        ):
            softened_squared_distance = squared_distance + softening_squared
            inverse_distance_cubed = 1.0 / (
                softened_squared_distance * math.sqrt(softened_squared_distance)
            )
            scale = node_masses[node] * inverse_distance_cubed
            acceleration_x += dx * scale
            acceleration_y += dy * scale
            acceleration_z += dz * scale
            accepted_nodes += 1
            continue

        for octant in range(7, -1, -1):
            child = children[node, octant]
            if child >= 0:
                stack[stack_size] = child
                stack_size += 1

    return (
        acceleration_x,
        acceleration_y,
        acceleration_z,
        accepted_nodes,
        direct_particles,
    )


@njit(cache=True, nogil=True)
def _barnes_hut_acceleration_kernel(
    positions: FloatArray,
    particle_masses: FloatArray,
    centers: FloatArray,
    half_sizes: FloatArray,
    children: IntArray,
    starts: IntArray,
    counts: IntArray,
    node_masses: FloatArray,
    centers_of_mass: FloatArray,
    particle_order: IntArray,
    inverse_order: IntArray,
    theta: float,
    softening_squared: float,
    depth_limit: int,
    output: FloatArray,
    accepted_counts: npt.NDArray[np.int64],
    direct_counts: npt.NDArray[np.int64],
) -> None:
    stack = np.empty(8 * (depth_limit + 1), dtype=np.int32)
    for target in range(positions.shape[0]):
        ax, ay, az, accepted, direct = _accumulate_target(
            target,
            positions,
            particle_masses,
            centers,
            half_sizes,
            children,
            starts,
            counts,
            node_masses,
            centers_of_mass,
            particle_order,
            inverse_order,
            theta,
            softening_squared,
            stack,
        )
        output[target, 0] = ax
        output[target, 1] = ay
        output[target, 2] = az
        accepted_counts[target] = accepted
        direct_counts[target] = direct


@njit(cache=True, nogil=True, parallel=True)
def _barnes_hut_acceleration_parallel_kernel(
    positions: FloatArray,
    particle_masses: FloatArray,
    centers: FloatArray,
    half_sizes: FloatArray,
    children: IntArray,
    starts: IntArray,
    counts: IntArray,
    node_masses: FloatArray,
    centers_of_mass: FloatArray,
    particle_order: IntArray,
    inverse_order: IntArray,
    theta: float,
    softening_squared: float,
    depth_limit: int,
    output: FloatArray,
    accepted_counts: npt.NDArray[np.int64],
    direct_counts: npt.NDArray[np.int64],
) -> None:
    for target in prange(positions.shape[0]):  # type: ignore[no-untyped-call, attr-defined]
        stack = np.empty(8 * (depth_limit + 1), dtype=np.int32)
        ax, ay, az, accepted, direct = _accumulate_target(
            target,
            positions,
            particle_masses,
            centers,
            half_sizes,
            children,
            starts,
            counts,
            node_masses,
            centers_of_mass,
            particle_order,
            inverse_order,
            theta,
            softening_squared,
            stack,
        )
        output[target, 0] = ax
        output[target, 1] = ay
        output[target, 2] = az
        accepted_counts[target] = accepted
        direct_counts[target] = direct


@dataclass(frozen=True, slots=True)
class BarnesHutSolver:
    """Approximate self-gravity with a rebuilt 3D monopole octree."""

    theta: float = DEFAULT_THETA
    leaf_capacity: int = DEFAULT_LEAF_CAPACITY
    depth_limit: int = DEFAULT_MAX_DEPTH
    parallel_threshold: int = PARALLEL_PARTICLE_THRESHOLD
    name: str = field(default="barnes-hut", init=False)
    last_stats: BarnesHutStats | None = field(default=None, init=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "theta",
            _bounded_real(self.theta, "theta", MIN_THETA, MAX_THETA),
        )
        object.__setattr__(
            self,
            "leaf_capacity",
            _bounded_integer(
                self.leaf_capacity,
                "leaf_capacity",
                MIN_LEAF_CAPACITY,
                MAX_LEAF_CAPACITY,
            ),
        )
        object.__setattr__(
            self,
            "depth_limit",
            _bounded_integer(
                self.depth_limit,
                "depth_limit",
                MIN_MAX_DEPTH,
                MAX_MAX_DEPTH,
            ),
        )
        object.__setattr__(
            self,
            "parallel_threshold",
            _bounded_integer(
                self.parallel_threshold,
                "parallel_threshold",
                1,
                np.iinfo(np.int32).max,
            ),
        )

    def build_tree(self, positions: FloatArray, masses: FloatArray) -> FlatOctree:
        """Expose the exact structure used by :meth:`compute` for validation."""

        return build_octree(
            positions,
            masses,
            leaf_capacity=self.leaf_capacity,
            depth_limit=self.depth_limit,
        )

    def compute(
        self,
        positions: FloatArray,
        masses: FloatArray,
        softening: float,
        output_buffer: FloatArray | None = None,
    ) -> FloatArray:
        particle_count = validate_solver_inputs(positions, masses)
        output = prepare_acceleration_output(
            positions,
            masses,
            particle_count,
            output_buffer,
        )
        safe_softening = validate_softening(softening)

        build_started = time.perf_counter()
        tree = self.build_tree(positions, masses)
        build_seconds = time.perf_counter() - build_started

        accepted_counts = np.empty(particle_count, dtype=np.int64)
        direct_counts = np.empty(particle_count, dtype=np.int64)
        force_started = time.perf_counter()
        kernel = (
            _barnes_hut_acceleration_parallel_kernel
            if particle_count >= self.parallel_threshold
            else _barnes_hut_acceleration_kernel
        )
        kernel(
            positions,
            masses,
            tree.centers,
            tree.half_sizes,
            tree.children,
            tree.starts,
            tree.counts,
            tree.masses,
            tree.centers_of_mass,
            tree.particle_order,
            tree.inverse_order,
            self.theta,
            safe_softening * safe_softening,
            tree.depth_limit,
            output,
            accepted_counts,
            direct_counts,
        )
        force_seconds = time.perf_counter() - force_started
        if not np.all(np.isfinite(output)):
            raise FloatingPointError("Barnes-Hut gravity produced a non-finite acceleration")
        object.__setattr__(
            self,
            "last_stats",
            BarnesHutStats(
                particle_count=particle_count,
                node_count=tree.node_count,
                leaf_count=tree.leaf_count,
                maximum_depth=tree.maximum_depth,
                tree_build_seconds=build_seconds,
                force_seconds=force_seconds,
                accepted_node_interactions=int(np.sum(accepted_counts)),
                direct_particle_interactions=int(np.sum(direct_counts)),
            ),
        )
        return output
