//! Experimental Barnes-Hut force traversal, matching gravity.physics.barnes_hut._accumulate_target.
//! Flat, row-major arrays: xyz positions/COM, 8 children per node.
//! Standalone Rust core; Python FFI and parallel scheduling deliberately excluded until validated.
#[derive(Clone, Copy)]
pub struct Tree<'a> {
    pub positions: &'a [f64],
    pub masses: &'a [f64],
    pub half_sizes: &'a [f64],
    pub children: &'a [i32],
    pub starts: &'a [i32],
    pub counts: &'a [i32],
    pub node_masses: &'a [f64],
    pub centers_of_mass: &'a [f64],
    pub particle_order: &'a [i32],
    pub inverse_order: &'a [i32],
}
#[derive(Default, Debug, Clone, Copy)]
pub struct Force {
    pub acceleration: [f64; 3],
    pub accepted_nodes: usize,
    pub direct_particles: usize,
}
pub fn accumulate_target(tree: &Tree<'_>, target: usize, theta: f64, softening_squared: f64) -> Force {
    let p = &tree.positions[target * 3..target * 3 + 3];
    let ordered_target = tree.inverse_order[target];
    let mut result = Force::default();
    let mut stack = vec![0usize];
    while let Some(node) = stack.pop() {
        let children = &tree.children[node * 8..node * 8 + 8];
        if children.iter().all(|&child| child < 0) {
            let start = tree.starts[node] as usize;
            let stop = start + tree.counts[node] as usize;
            for &other in &tree.particle_order[start..stop] {
                let other = other as usize;
                if other == target { continue; }
                let dx = tree.positions[other * 3] - p[0];
                let dy = tree.positions[other * 3 + 1] - p[1];
                let dz = tree.positions[other * 3 + 2] - p[2];
                let d2 = dx * dx + dy * dy + dz * dz + softening_squared;
                let scale = tree.masses[other] / (d2 * d2.sqrt());
                result.acceleration[0] += dx * scale;
                result.acceleration[1] += dy * scale;
                result.acceleration[2] += dz * scale;
                result.direct_particles += 1;
            }
            continue;
        }
        let dx = tree.centers_of_mass[node * 3] - p[0];
        let dy = tree.centers_of_mass[node * 3 + 1] - p[1];
        let dz = tree.centers_of_mass[node * 3 + 2] - p[2];
        let d2 = dx * dx + dy * dy + dz * dz;
        let contains_target = tree.starts[node] <= ordered_target
            && ordered_target < tree.starts[node] + tree.counts[node];
        if !contains_target && d2 > 0.0 && 2.0 * tree.half_sizes[node] < theta * d2.sqrt() {
            let softened = d2 + softening_squared;
            let scale = tree.node_masses[node] / (softened * softened.sqrt());
            result.acceleration[0] += dx * scale;
            result.acceleration[1] += dy * scale;
            result.acceleration[2] += dz * scale;
            result.accepted_nodes += 1;
            continue;
        }
        // Python pushes children 7..0; LIFO visits them 0..7.
        for &child in children.iter().rev() {
            if child >= 0 { stack.push(child as usize); }
        }
    }
    result
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn two_particles_single_leaf() {
        let tree = Tree {
            positions: &[0.,0.,0., 2.,0.,0.], masses: &[1.,3.],
            half_sizes: &[2.], children: &[-1; 8], starts: &[0], counts: &[2],
            node_masses: &[4.], centers_of_mass: &[1.5,0.,0.],
            particle_order: &[0,1], inverse_order: &[0,1],
        };
        let a = accumulate_target(&tree, 0, 0.7, 0.);
        let b = accumulate_target(&tree, 1, 0.7, 0.);
        assert!((a.acceleration[0] - 0.75).abs() < 1e-12);
        assert!((b.acceleration[0] + 0.25).abs() < 1e-12);
        assert_eq!(a.direct_particles, 1);
    }
}

#[no_mangle]
pub unsafe extern "C" fn gravity_bh_forces(
    n: usize, nodes: usize,
    positions: *const f64, masses: *const f64,
    half_sizes: *const f64, children: *const i32,
    starts: *const i32, counts: *const i32,
    node_masses: *const f64, centers_of_mass: *const f64,
    particle_order: *const i32, inverse_order: *const i32,
    theta: f64, softening_squared: f64,
    output: *mut f64,
) {
    let tree = Tree {
        positions: std::slice::from_raw_parts(positions, n*3),
        masses: std::slice::from_raw_parts(masses, n),
        half_sizes: std::slice::from_raw_parts(half_sizes, nodes),
        children: std::slice::from_raw_parts(children, nodes*8),
        starts: std::slice::from_raw_parts(starts, nodes),
        counts: std::slice::from_raw_parts(counts, nodes),
        node_masses: std::slice::from_raw_parts(node_masses, nodes),
        centers_of_mass: std::slice::from_raw_parts(centers_of_mass, nodes*3),
        particle_order: std::slice::from_raw_parts(particle_order, n),
        inverse_order: std::slice::from_raw_parts(inverse_order, n),
    };
    let out = std::slice::from_raw_parts_mut(output, n*3);
    for target in 0..n {
        let f = accumulate_target(&tree, target, theta, softening_squared);
        out[target*3..target*3+3].copy_from_slice(&f.acceleration);
    }
}

#[no_mangle]
pub unsafe extern "C" fn gravity_bh_forces_parallel(
    n: usize, nodes: usize,
    positions: *const f64, masses: *const f64,
    half_sizes: *const f64, children: *const i32,
    starts: *const i32, counts: *const i32,
    node_masses: *const f64, centers_of_mass: *const f64,
    particle_order: *const i32, inverse_order: *const i32,
    theta: f64, softening_squared: f64,
    output: *mut f64,
) {
    use rayon::prelude::*;
    let tree = Tree {
        positions: std::slice::from_raw_parts(positions, n*3),
        masses: std::slice::from_raw_parts(masses, n),
        half_sizes: std::slice::from_raw_parts(half_sizes, nodes),
        children: std::slice::from_raw_parts(children, nodes*8),
        starts: std::slice::from_raw_parts(starts, nodes),
        counts: std::slice::from_raw_parts(counts, nodes),
        node_masses: std::slice::from_raw_parts(node_masses, nodes),
        centers_of_mass: std::slice::from_raw_parts(centers_of_mass, nodes*3),
        particle_order: std::slice::from_raw_parts(particle_order, n),
        inverse_order: std::slice::from_raw_parts(inverse_order, n),
    };
    let out = std::slice::from_raw_parts_mut(output, n*3);
    out.par_chunks_mut(3).enumerate().for_each(|(target, chunk)| {
        let f = accumulate_target(&tree, target, theta, softening_squared);
        chunk.copy_from_slice(&f.acceleration);
    });
}
