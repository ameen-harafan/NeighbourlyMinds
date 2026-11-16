"""
NeighbourlyMinds - Student 3
SVG colour extractor + digital contrast tester

This script:
1. Reads an SVG file.
2. Finds elements by SVG id, e.g. id="wall" and id="door-frame".
3. Extracts their fill/stroke colour.
4. Calculates W3C relative luminance and contrast ratio internally.
5. Displays an easier user-facing DIGITAL LUMINANCE DIFFERENCE percentage.

Important:
- The percentage shown here is NOT physical paint/material LRV.
- The badge still uses the W3C digital contrast ratio internally (3:1 boundary).
- Do not call this percentage "30% LRV", "physical luminance contrast", or
  "AS 1428.1 compliance".
"""

from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path

HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def normalise_hex(value: str) -> str:
    value = value.strip()
    if not HEX_RE.fullmatch(value):
        raise ValueError(f"Only 6-digit HEX colours are supported, got: {value!r}")
    return value.upper()


def parse_inline_style(style: str) -> dict[str, str]:
    """Convert 'fill:#fff;stroke:#000' style text into a dictionary."""
    result = {}
    for part in style.split(";"):
        if ":" in part:
            key, value = part.split(":", 1)
            result[key.strip()] = value.strip()
    return result


def get_element_colour(element: ET.Element, preferred=("fill", "stroke")) -> str:
    """
    Get a HEX colour from direct SVG attributes or inline style.

    Supported examples:
      fill="#F5F5F5"
      stroke="#505050"
      style="fill:#F5F5F5;stroke:#505050"
    """
    style_values = parse_inline_style(element.attrib.get("style", ""))

    for attribute in preferred:
        raw = element.attrib.get(attribute) or style_values.get(attribute)
        if raw and HEX_RE.fullmatch(raw.strip()):
            return normalise_hex(raw)

    raise ValueError(
        f'Element id="{element.attrib.get("id", "?")}" does not contain a supported '
        "6-digit HEX fill/stroke colour."
    )


def find_element_by_id(root: ET.Element, element_id: str) -> ET.Element:
    for element in root.iter():
        if element.attrib.get("id") == element_id:
            return element
    raise KeyError(f'SVG element id="{element_id}" was not found.')


def hex_to_rgb(hex_colour: str) -> tuple[int, int, int]:
    h = normalise_hex(hex_colour).lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def linearise_srgb(channel_8bit: int) -> float:
    c = channel_8bit / 255.0
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_colour: str) -> float:
    r8, g8, b8 = hex_to_rgb(hex_colour)
    r = linearise_srgb(r8)
    g = linearise_srgb(g8)
    b = linearise_srgb(b8)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def wcag_contrast_ratio(colour_1: str, colour_2: str) -> float:
    l1 = relative_luminance(colour_1)
    l2 = relative_luminance(colour_2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def digital_luminance_difference_percent(colour_1: str, colour_2: str) -> float:
    """
    User-facing 0-100 digital difference score.

    Because W3C relative luminance is in the range 0..1, the absolute luminance
    difference can be shown as a percentage:
        abs(L1 - L2) * 100

    0%   = identical relative luminance
    100% = maximum black-vs-white relative luminance difference

    This is a DIGITAL UX score, NOT physical LRV contrast.
    """
    l1 = relative_luminance(colour_1)
    l2 = relative_luminance(colour_2)
    return abs(l1 - l2) * 100.0


def badge_from_ratio(ratio: float, threshold: float = 3.0) -> str:
    return "Improved contrast" if ratio >= threshold else "Low contrast"


def extract_all_hex_colours(root: ET.Element) -> list[str]:
    """Useful diagnostic: return unique direct/inline HEX fill and stroke colours."""
    colours = []
    for element in root.iter():
        style = parse_inline_style(element.attrib.get("style", ""))
        for attr in ("fill", "stroke"):
            raw = element.attrib.get(attr) or style.get(attr)
            if raw and HEX_RE.fullmatch(raw.strip()):
                colour = normalise_hex(raw)
                if colour not in colours:
                    colours.append(colour)
    return colours


def evaluate_svg(svg_path: str, first_id: str = "wall", second_id: str = "door-frame"):
    tree = ET.parse(svg_path)
    root = tree.getroot()

    first_element = find_element_by_id(root, first_id)
    second_element = find_element_by_id(root, second_id)

    first_colour = get_element_colour(first_element)
    second_colour = get_element_colour(second_element)

    ratio = wcag_contrast_ratio(first_colour, second_colour)
    percentage = digital_luminance_difference_percent(first_colour, second_colour)
    badge = badge_from_ratio(ratio)

    return {
        "first_id": first_id,
        "first_colour": first_colour,
        "second_id": second_id,
        "second_colour": second_colour,
        "digital_contrast_percent": percentage,
        "wcag_ratio_internal": ratio,
        "badge": badge,
        "all_svg_colours": extract_all_hex_colours(root),
    }


def main():
    parser = argparse.ArgumentParser(description="Test digital contrast between two SVG elements.")
    parser.add_argument("svg_file", help="Path to the SVG file.")
    parser.add_argument("--first-id", default="wall", help='First SVG element id. Default: "wall"')
    parser.add_argument("--second-id", default="door-frame", help='Second SVG element id. Default: "door-frame"')
    parser.add_argument(
        "--show-internal-ratio",
        action="store_true",
        help="Also print the internal W3C ratio used by the badge.",
    )
    args = parser.parse_args()

    result = evaluate_svg(args.svg_file, args.first_id, args.second_id)

    print(f'{result["first_id"]}:  {result["first_colour"]}')
    print(f'{result["second_id"]}: {result["second_colour"]}')
    print(f'Digital contrast: {result["digital_contrast_percent"]:.2f}%')
    print(f'Badge: {result["badge"]}')

    if args.show_internal_ratio:
        print(f'Internal WCAG ratio: {result["wcag_ratio_internal"]:.2f}:1')

    print("SVG colours found:", ", ".join(result["all_svg_colours"]))
    print("Note: percentage is a digital luminance-difference score, not physical LRV.")


if __name__ == "__main__":
    main()
