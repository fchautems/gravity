from __future__ import annotations

import numpy as np
import pytest

from gravity.physics import CompositeGravitySolver, ExactGravitySolver, PlummerPotential
from gravity.physics.potentials import _plummer_acceleration_kernel


def test_plummer_acceleration_and_enclosed_mass_match_closed_form() -> None:
    potential = PlummerPotential(mass=3.0, scale_radius=2.0)
    positions = np.array([[0.0, 0.0, 0.0], [3.0, 4.0, 0.0]], dtype=np.float64)
    actual = potential.acceleration(positions)
    scale = -3.0 / (25.0 + 4.0) ** 1.5
    expected = np.array([[0.0, 0.0, 0.0], [3.0 * scale, 4.0 * scale, 0.0]])
    np.testing.assert_allclose(actual, expected, rtol=2e-15, atol=0.0)
    np.testing.assert_allclose(
        potential.enclosed_mass(np.array([0.0, 5.0])),
        [0.0, 3.0 * 5.0**3 / 29.0**1.5],
        rtol=2e-15,
        atol=0.0,
    )


def test_plummer_compiled_and_python_kernels_agree() -> None:
    positions = np.array([[1.0, -2.0, 3.0], [-0.5, 0.4, 0.2]], dtype=np.float64)
    compiled = PlummerPotential(2.0, 0.7).acceleration(positions)
    interpreted = np.empty_like(compiled)
    _plummer_acceleration_kernel.py_func(positions, 2.0, 0.7**2, interpreted)
    np.testing.assert_array_equal(compiled, interpreted)


def test_potential_can_fill_or_add_to_an_existing_buffer() -> None:
    positions = np.array([[1.0, 0.0, 0.0], [0.0, 2.0, 0.0]], dtype=np.float64)
    potential = PlummerPotential(1.5, 0.5)
    expected = potential.acceleration(positions)
    output = np.full((2, 3), 4.0, dtype=np.float64)
    assert potential.acceleration(positions, output) is output
    np.testing.assert_array_equal(output, expected)
    output.fill(2.0)
    potential.add_acceleration(positions, output)
    np.testing.assert_allclose(output, 2.0 + expected, rtol=0.0, atol=2e-16)


def test_composite_solver_adds_external_field_without_changing_the_exact_solver() -> None:
    positions = np.array([[-1.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=np.float64)
    masses = np.array([0.5, 0.5], dtype=np.float64)
    exact = ExactGravitySolver()
    halo = PlummerPotential(1.0, 2.0)
    expected = exact.compute(positions, masses, 0.1) + halo.acceleration(positions)
    actual = CompositeGravitySolver(exact, (halo,)).compute(positions, masses, 0.1)
    np.testing.assert_allclose(actual, expected, rtol=2e-15, atol=0.0)


@pytest.mark.parametrize(
    ("mass", "scale", "error"),
    [
        (-1.0, 1.0, ValueError),
        (float("nan"), 1.0, ValueError),
        (1.0, 0.0, ValueError),
        (1.0, "bad", TypeError),
    ],
)
def test_invalid_potential_parameters_are_rejected(
    mass: object,
    scale: object,
    error: type[Exception],
) -> None:
    with pytest.raises(error):
        PlummerPotential(mass, scale)  # type: ignore[arg-type]


def test_potential_rejects_invalid_arrays_and_composite_fields() -> None:
    potential = PlummerPotential(1.0, 1.0)
    with pytest.raises(TypeError):
        potential.acceleration(np.zeros((2, 3), dtype=np.float32))  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="shape"):
        potential.acceleration(np.zeros((2, 2), dtype=np.float64))
    with pytest.raises(ValueError, match="overlap"):
        positions = np.zeros((2, 3), dtype=np.float64)
        potential.acceleration(positions, positions)
    with pytest.raises(ValueError, match="finite"):
        output = np.full((2, 3), np.nan)
        potential.add_acceleration(np.zeros((2, 3)), output)
    with pytest.raises(TypeError):
        CompositeGravitySolver(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        CompositeGravitySolver(ExactGravitySolver(), (object(),))  # type: ignore[arg-type]
