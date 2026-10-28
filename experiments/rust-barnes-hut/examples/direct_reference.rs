use gravity_rust_force_experiment::{accumulate_target, Tree};
use std::time::Instant;

fn main() {
    for &n in &[1000usize, 5000, 10000] {
        let mut positions = Vec::with_capacity(3*n);
        for i in 0..n {
            let t = i as f64 * 2.399963229728653;
            let r = ((i as f64 + 0.5)/(n as f64)).sqrt();
            positions.extend_from_slice(&[r*t.cos(), r*t.sin(), (i % 97) as f64 / 97.0]);
        }
        let masses = vec![1.0; n];
        // Single-leaf reference workload only; not a Barnes-Hut benchmark.
        let children = [-1i32; 8];
        let order: Vec<i32> = (0..n as i32).collect();
        let tree = Tree {
            positions: &positions, masses: &masses,
            half_sizes: &[1.], children: &children,
            starts: &[0], counts: &[n as i32],
            node_masses: &[n as f64], centers_of_mass: &[0.,0.,0.],
            particle_order: &order, inverse_order: &order,
        };
        let start = Instant::now();
        let mut checksum = 0.0;
        for target in 0..n {
            let force = accumulate_target(&tree, target, 0.7, 0.01);
            checksum += force.acceleration[0];
        }
        println!("rust_direct_reference particles={n} elapsed_ms={:.3} checksum={checksum:.9}", start.elapsed().as_secs_f64()*1000.0);
    }
}
