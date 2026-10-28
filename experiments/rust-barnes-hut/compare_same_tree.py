"""Same-tree Rust vs Numba force traversal. Run after cargo build --release."""
import ctypes
import json
import sys
import time
from pathlib import Path

import numpy as np
from gravity.physics.barnes_hut import BarnesHutSolver, _barnes_hut_acceleration_kernel

ROOT = Path(__file__).resolve().parent
LIBRARY = ROOT / "target" / "release" / ("gravity_rust_force_experiment.dll" if sys.platform == "win32" else "libgravity_rust_force_experiment.dylib" if sys.platform == "darwin" else "libgravity_rust_force_experiment.so")
PTR = ctypes.c_void_p
lib = ctypes.CDLL(str(LIBRARY))
fn = lib.gravity_bh_forces
fn.argtypes = [ctypes.c_size_t, ctypes.c_size_t] + [PTR] * 10 + [ctypes.c_double, ctypes.c_double, PTR]
fn.restype = None

def pointer(a):
    assert a.flags.c_contiguous
    return a.ctypes.data

def run(n):
    rng = np.random.default_rng(20260806)
    positions = np.ascontiguousarray(rng.normal(size=(n, 3)), dtype=np.float64)
    masses = np.ascontiguousarray(rng.uniform(0.5, 2.0, size=n), dtype=np.float64)
    solver = BarnesHutSolver()
    tree = solver.build_tree(positions, masses)
    out_numba = np.empty_like(positions)
    out_rust = np.empty_like(positions)
    accepted = np.empty(n, dtype=np.int64)
    direct = np.empty(n, dtype=np.int64)
    def numba():
        _barnes_hut_acceleration_kernel(
            positions, masses, tree.centers, tree.half_sizes, tree.children,
            tree.starts, tree.counts, tree.masses, tree.centers_of_mass,
            tree.particle_order, tree.inverse_order, solver.theta, 0.01,
            tree.depth_limit, out_numba, accepted, direct,
        )
    def rust():
        fn(n, tree.node_count, *map(pointer, (
            positions, masses, tree.half_sizes, tree.children, tree.starts,
            tree.counts, tree.masses, tree.centers_of_mass, tree.particle_order,
            tree.inverse_order,
        )), solver.theta, 0.01, pointer(out_rust))
    numba()
    rust()
    absolute_error = float(np.max(np.abs(out_numba - out_rust)))
    relative_error = float(np.linalg.norm(out_numba-out_rust) / max(np.linalg.norm(out_numba), 1e-30))
    if not np.allclose(out_numba, out_rust, rtol=1e-10, atol=1e-10):
        raise AssertionError(f"Rust/Numba mismatch n={n}: max_abs={absolute_error}")
    def median_ms(f):
        times = []
        for _ in range(7):
            t = time.perf_counter()
            f()
            times.append((time.perf_counter() - t)*1000)
        return float(np.median(times))
    return {"particles":n, "max_absolute_error":absolute_error,
            "relative_l2_error":relative_error, "numba_serial_ms":median_ms(numba),
            "rust_serial_ffi_ms":median_ms(rust)}

if __name__ == "__main__":
    print(json.dumps([run(n) for n in (1000, 5000, 10000)], indent=2))
