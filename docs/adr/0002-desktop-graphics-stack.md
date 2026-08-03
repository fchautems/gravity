# ADR 0002: GLFW, ModernGL, and Dear ImGui Bundle

- Status: Accepted; package gate passed, reference-PC validation pending
- Date: 2026-08-03

## Context

The simulator needs a fluid 3D viewport, a game-like orbit camera, compact live
controls, and one batched draw for tens of thousands of points. The old
one-entity-per-particle Ursina design does not fit that workload.

A large retained-mode desktop framework would give native widgets but add a
second rendering abstraction and more context-integration risk. Building custom
controls directly in OpenGL would waste substantial effort.

## Decision

- GLFW creates the desktop window, OpenGL context, and input events.
- ModernGL owns modern OpenGL resources and batched rendering.
- Dear ImGui Bundle provides the immediate-mode control panel and styling.
- The base target is OpenGL 3.3 core.
- The particle field is a contiguous buffer rendered with one base draw call.
- Graphics remain on the main thread.

The integrated package gate selected:

- GLFW Python 2.10.2;
- ModernGL 5.12.0 with glcontext 3.0.0;
- Dear ImGui Bundle 1.92.801;
- PyOpenGL and PyOpenGL-accelerate 3.1.10 for the maintained pure-Python ImGui
  renderer backend only.

All provide CPython 3.12 Windows x86-64 wheels. Imports, lifecycle contracts,
the single-draw renderer, camera, and input capture are automated. Native
OpenGL context, driver, DPI, and visual feel remain the reference-PC gate.

## Consequences

The stack is well matched to a continuously rendered simulator and keeps UI and
3D drawing in one context. The visual style will be custom and cohesive rather
than native Windows chrome.

The application must explicitly handle DPI, input capture, GPU resource
lifecycle, and readable startup errors.

## Fallback

Step 3 begins with the smallest possible integrated window/UI/ModernGL test. If
Dear ImGui Bundle causes a reproducible installation or backend failure on the
reference PC, replace only the UI binding with a maintained Dear ImGui/GLFW
combination. Physics, scenario, snapshot, and rendering contracts do not change.

## Rejected alternatives

- Ursina entities: too much Python and scene-object overhead per particle.
- Matplotlib: not an interactive 3D renderer for this workload.
- A browser/WebGL V1: complicates local Python-worker integration and packaging.
- PySide6 + embedded ModernGL: polished widgets, but an unnecessary context
  integration layer for the first simulator build.
