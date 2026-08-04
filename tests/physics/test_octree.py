from __future__ import annotations

import numpy as np
import pytest

from gravity.physics import build_octree


def _seeded_cloud(count: int = 257) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(20_260_806)
    positions = np.ascontiguousarray(rng.normal(size=(count, 3)), dtype=np.float64)
    masses = np.ascontiguousarray(rng.uniform(0.05, 2.0, size=count), dtype=np.float64)
    return positions, masses


def test_flat_tree_partitions_every_parent_and_preserves_spatial_bounds() -> None:
    positions, masses = _seeded_cloud()
    tree = build_octree(positions, masses, leaf_capacity=4, depth_limit=24)

    assert tree.node_count > tree.leaf_count > 1
    assert tree.counts[0] == positions.shape[0]
    for parent in range(tree.node_count):
        children = tree.children[parent]
        occupied = children[children >= 0]
        if occupied.size == 0:
            assert tree.counts[parent] <= tree.leaf_capacity
            continue
        assert np.sum(tree.counts[occupied]) == tree.counts[parent]
        assert tree.starts[occupied[0]] == tree.starts[parent]
        assert tree.starts[occupied[-1]] + tree.counts[occupied[-1]] == (
            tree.starts[parent] + tree.counts[parent]
        )
        for previous, following in zip(occupied[:-1], occupied[1:], strict=True):
            assert tree.starts[previous] + tree.counts[previous] == tree.starts[following]
        assert np.all(tree.depths[occupied] == tree.depths[parent] + 1)
        assert np.all(tree.half_sizes[occupied] == tree.half_sizes[parent] * 0.5)

    for node in range(tree.node_count):
        start = tree.starts[node]
        stop = start + tree.counts[node]
        node_positions = positions[tree.particle_order[start:stop]]
        tolerance = (
            32.0
            * np.finfo(np.float64).eps
            * max(
                1.0,
                float(np.max(np.abs(tree.centers[node]))),
                float(tree.half_sizes[node]),
            )
        )
        assert np.all(
            np.abs(node_positions - tree.centers[node]) <= tree.half_sizes[node] + tolerance
        )


def test_node_mass_and_center_of_mass_are_exact_bottom_up_aggregates() -> None:
    positions, masses = _seeded_cloud(113)
    tree = build_octree(positions, masses, leaf_capacity=3)
    assert tree.masses[0] == pytest.approx(float(np.sum(masses)), rel=2e-15)
    expected_center = np.sum(positions * masses[:, None], axis=0) / np.sum(masses)
    np.testing.assert_allclose(tree.centers_of_mass[0], expected_center, rtol=2e-15, atol=2e-15)

    for node in range(tree.node_count):
        occupied = tree.children[node][tree.children[node] >= 0]
        if occupied.size == 0:
            continue
        assert tree.masses[node] == pytest.approx(float(np.sum(tree.masses[occupied])), rel=2e-15)
        reconstructed = (
            np.sum(
                tree.centers_of_mass[occupied] * tree.masses[occupied, None],
                axis=0,
            )
            / tree.masses[node]
        )
        np.testing.assert_allclose(tree.centers_of_mass[node], reconstructed, rtol=2e-15)


def test_tree_is_deterministic_and_arrays_are_immutable() -> None:
    positions, masses = _seeded_cloud(80)
    first = build_octree(positions, masses)
    second = build_octree(positions, masses)
    for first_array, second_array in (
        (first.centers, second.centers),
        (first.half_sizes, second.half_sizes),
        (first.children, second.children),
        (first.starts, second.starts),
        (first.counts, second.counts),
        (first.depths, second.depths),
        (first.masses, second.masses),
        (first.centers_of_mass, second.centers_of_mass),
        (first.particle_order, second.particle_order),
        (first.inverse_order, second.inverse_order),
    ):
        assert np.array_equal(first_array, second_array)
        assert not first_array.flags.writeable
    with pytest.raises(ValueError):
        first.children[0, 0] = 1


def test_coincident_groups_stop_at_depth_limit_and_grow_node_storage_safely() -> None:
    unique = np.array(
        [
            [-1.0, -1.0, -1.0],
            [-1.0, 1.0, -1.0],
            [1.0, -1.0, 1.0],
            [1.0, 1.0, 1.0],
        ],
        dtype=np.float64,
    )
    positions = np.ascontiguousarray(np.repeat(unique, 2, axis=0))
    masses = np.ones(positions.shape[0], dtype=np.float64)
    initial_capacity = max(64, 2 * positions.shape[0] + 64 + 1)
    tree = build_octree(positions, masses, leaf_capacity=1, depth_limit=64)
    assert tree.node_count > initial_capacity
    assert tree.maximum_depth == 64
    deepest = tree.counts[tree.depths == 64]
    assert np.all(deepest == 2)
    assert tree.masses[0] == positions.shape[0]


def test_single_particle_tree_is_one_valid_leaf() -> None:
    positions = np.array([[3.0, -2.0, 9.0]], dtype=np.float64)
    masses = np.array([4.0], dtype=np.float64)
    tree = build_octree(positions, masses)
    assert tree.node_count == tree.leaf_count == 1
    assert tree.maximum_depth == 0
    assert tree.half_sizes[0] > 0.0
    np.testing.assert_array_equal(tree.centers_of_mass[0], positions[0])


@pytest.mark.parametrize(
    ("keyword", "value", "error"),
    [
        ("leaf_capacity", 0, ValueError),
        ("leaf_capacity", 65, ValueError),
        ("leaf_capacity", True, TypeError),
        ("depth_limit", 0, ValueError),
        ("depth_limit", 65, ValueError),
        ("depth_limit", 3.2, TypeError),
    ],
)
def test_tree_configuration_boundaries_are_rejected(
    keyword: str,
    value: object,
    error: type[Exception],
) -> None:
    positions = np.zeros((2, 3), dtype=np.float64)
    masses = np.ones(2, dtype=np.float64)
    with pytest.raises(error):
        build_octree(positions, masses, **{keyword: value})  # type: ignore[arg-type]
