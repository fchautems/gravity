from __future__ import annotations

from dataclasses import replace

import pytest

from gravity.core.experiment import (
    DEFAULT_BULGE_MASS,
    DEFAULT_CENTRAL_MASS,
    DEFAULT_DISK_MASS,
    MAX_EXPERIMENT_SEED,
    MAX_PARTICLE_COUNT,
    MIN_PARTICLE_COUNT,
    SCENARIO_CATALOG,
    ExperimentConfig,
    ScenarioKind,
    estimated_barnes_hut_load,
)


def test_catalogue_has_eight_stable_named_scenarios() -> None:
    assert SCENARIO_CATALOG == tuple(ScenarioKind)
    assert len(SCENARIO_CATALOG) == 8
    assert len({scenario.value for scenario in SCENARIO_CATALOG}) == 8
    assert all(scenario.french_name for scenario in SCENARIO_CATALOG)
    assert all(scenario.french_description for scenario in SCENARIO_CATALOG)


def test_default_experiment_is_the_published_spiral_setup() -> None:
    experiment = ExperimentConfig()
    assert experiment.scenario is ScenarioKind.SPIRAL_GALAXY
    assert experiment.particle_count == 10_000
    assert experiment.seed == 2_026_080_3
    assert experiment.disk_mass == DEFAULT_DISK_MASS
    assert experiment.bulge_mass == DEFAULT_BULGE_MASS
    assert experiment.central_mass == DEFAULT_CENTRAL_MASS
    assert experiment.uses_galaxy_components
    assert estimated_barnes_hut_load(experiment.particle_count) == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"scenario": "ring"}, TypeError),
        ({"particle_count": MIN_PARTICLE_COUNT - 1}, ValueError),
        ({"particle_count": MAX_PARTICLE_COUNT + 1}, ValueError),
        ({"particle_count": True}, TypeError),
        ({"seed": -1}, ValueError),
        ({"seed": MAX_EXPERIMENT_SEED + 1}, ValueError),
        ({"seed": 1.5}, TypeError),
        ({"disk_mass": 0.0}, ValueError),
        ({"bulge_mass": float("inf")}, ValueError),
        ({"central_mass": -0.01}, ValueError),
    ],
)
def test_invalid_experiment_boundaries_are_rejected(
    changes: dict[str, object],
    error: type[Exception],
) -> None:
    with pytest.raises(error):
        replace(ExperimentConfig(), **changes)


@pytest.mark.parametrize(
    "scenario",
    [ScenarioKind.HEAD_ON_COLLISION, ScenarioKind.OBLIQUE_COLLISION],
)
def test_dual_galaxy_scenarios_reserve_at_least_one_valid_galaxy_per_side(
    scenario: ScenarioKind,
) -> None:
    with pytest.raises(ValueError, match="at least 200"):
        ExperimentConfig(scenario=scenario, particle_count=199)
    assert ExperimentConfig(scenario=scenario, particle_count=200).particle_count == 200


def test_load_estimate_is_monotonic_and_validated() -> None:
    loads = [estimated_barnes_hut_load(value) for value in (100, 1_000, 10_000, 50_000)]
    assert loads == sorted(loads)
    assert loads[0] < 0.01
    assert loads[-1] > 5.0
    with pytest.raises(ValueError):
        estimated_barnes_hut_load(50_001)


def test_only_galaxy_based_scenarios_use_the_component_mass_controls() -> None:
    assert ExperimentConfig(ScenarioKind.SPIRAL_GALAXY).uses_galaxy_components
    assert ExperimentConfig(ScenarioKind.HEAD_ON_COLLISION).uses_galaxy_components
    assert ExperimentConfig(ScenarioKind.OBLIQUE_COLLISION).uses_galaxy_components
    assert not ExperimentConfig(ScenarioKind.RING).uses_galaxy_components
