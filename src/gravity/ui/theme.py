"""Restrained space theme and DPI-aware default font setup."""

from __future__ import annotations

from imgui_bundle import imgui


def configure_theme(dpi_scale: float) -> None:
    """Configure font and layout before the ImGui renderer builds its atlas."""

    scale = max(1.0, min(float(dpi_scale), 2.0))
    imgui.get_io().set_ini_filename(None)
    font_config = imgui.ImFontConfig()
    font_config.size_pixels = 16.0 * scale
    imgui.get_io().fonts.add_font_default(font_config)

    imgui.style_colors_dark()
    style = imgui.get_style()
    style.scale_all_sizes(scale)
    style.window_rounding = 10.0 * scale
    style.frame_rounding = 6.0 * scale

    style.set_color_(imgui.Col_.text, (0.91, 0.94, 1.00, 1.00))
    style.set_color_(imgui.Col_.text_disabled, (0.52, 0.58, 0.70, 1.00))
    style.set_color_(imgui.Col_.window_bg, (0.030, 0.042, 0.076, 0.96))
    style.set_color_(imgui.Col_.border, (0.15, 0.23, 0.38, 0.75))
    style.set_color_(imgui.Col_.frame_bg, (0.075, 0.105, 0.175, 1.00))
    style.set_color_(imgui.Col_.frame_bg_hovered, (0.10, 0.17, 0.27, 1.00))
    style.set_color_(imgui.Col_.frame_bg_active, (0.12, 0.22, 0.35, 1.00))
    style.set_color_(imgui.Col_.button, (0.10, 0.30, 0.50, 1.00))
    style.set_color_(imgui.Col_.button_hovered, (0.13, 0.41, 0.68, 1.00))
    style.set_color_(imgui.Col_.button_active, (0.17, 0.50, 0.80, 1.00))
    style.set_color_(imgui.Col_.slider_grab, (0.24, 0.62, 0.92, 1.00))
    style.set_color_(imgui.Col_.slider_grab_active, (0.40, 0.76, 1.00, 1.00))
    style.set_color_(imgui.Col_.header, (0.08, 0.24, 0.40, 1.00))
    style.set_color_(imgui.Col_.header_hovered, (0.12, 0.35, 0.56, 1.00))
    style.set_color_(imgui.Col_.separator, (0.16, 0.25, 0.40, 1.00))
