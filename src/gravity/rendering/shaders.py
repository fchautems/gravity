"""OpenGL 3.3 shaders for the single-draw particle field."""

VERTEX_SHADER = """
#version 330 core

uniform mat4 u_mvp;
uniform float u_point_scale;

in vec3 in_position;
in vec4 in_color_size;

out vec3 particle_color;
out float particle_strength;

void main() {
    float radius = length(in_position.xz);
    vec4 clip_position = u_mvp * vec4(in_position, 1.0);
    gl_Position = clip_position;

    float perspective_scale = clamp(19.0 / max(5.0, clip_position.w), 0.62, 2.3);
    gl_PointSize = clamp(in_color_size.w * u_point_scale * perspective_scale, 1.0, 16.0);
    particle_color = in_color_size.rgb;
    particle_strength = clamp(1.15 - radius * 0.025, 0.68, 1.15);
}
"""

FRAGMENT_SHADER = """
#version 330 core

in vec3 particle_color;
in float particle_strength;

out vec4 fragment_color;

void main() {
    vec2 centered = gl_PointCoord * 2.0 - vec2(1.0);
    float radius = length(centered);
    if (radius > 1.0) {
        discard;
    }

    float core = pow(max(0.0, 1.0 - radius), 1.55);
    float edge = smoothstep(1.0, 0.55, radius);
    float alpha = (0.22 * edge + 0.82 * core) * particle_strength;
    vec3 luminous_color = particle_color * (0.80 + 0.95 * core);
    fragment_color = vec4(luminous_color, alpha);
}
"""
