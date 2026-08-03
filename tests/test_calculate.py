import math

import pytest

from calculate import MILES_PER_DEGREE_LATITUDE, generate_grid


def test_grid_has_one_point_per_cell():
    assert len(generate_grid(38.9, -77.0, grid_size=3)) == 9
    assert len(generate_grid(38.9, -77.0, grid_size=1)) == 1
    assert len(generate_grid(38.9, -77.0, grid_size=5)) == 25


def test_odd_grid_is_centered_on_the_origin():
    center = (38.9, -77.0)
    points = generate_grid(*center, grid_size=3, spacing_miles=1.5)

    assert any(
        math.isclose(lat, center[0]) and math.isclose(lng, center[1])
        for lat, lng in points
    )


def test_grid_is_symmetric_about_its_center():
    center_lat, center_lng = 38.9, -77.0
    points = generate_grid(center_lat, center_lng, grid_size=3, spacing_miles=1.5)

    mean_lat = sum(lat for lat, _ in points) / len(points)
    mean_lng = sum(lng for _, lng in points) / len(points)

    assert math.isclose(mean_lat, center_lat, abs_tol=1e-9)
    assert math.isclose(mean_lng, center_lng, abs_tol=1e-9)


def test_latitude_spacing_matches_requested_miles():
    spacing = 1.5
    points = generate_grid(38.9, -77.0, grid_size=3, spacing_miles=spacing)

    latitudes = sorted({round(lat, 9) for lat, _ in points})
    step_degrees = latitudes[1] - latitudes[0]

    assert math.isclose(
        step_degrees * MILES_PER_DEGREE_LATITUDE, spacing, rel_tol=1e-6
    )


def test_longitude_spacing_widens_with_latitude():
    """A degree of longitude covers fewer miles nearer the poles, so the same
    spacing in miles must translate to a larger degree step up north."""
    equator = generate_grid(0.0, 0.0, grid_size=3, spacing_miles=1.5)
    northern = generate_grid(60.0, 0.0, grid_size=3, spacing_miles=1.5)

    def lng_step(points):
        longitudes = sorted({round(lng, 9) for _, lng in points})
        return longitudes[1] - longitudes[0]

    assert lng_step(northern) > lng_step(equator)
    # cos(60°) = 0.5, so the step should be roughly twice as wide.
    assert math.isclose(lng_step(northern), lng_step(equator) * 2, rel_tol=1e-3)


@pytest.mark.parametrize("latitude", [89.999, -89.999, 90.0, -90.0])
def test_extreme_latitudes_do_not_blow_up(latitude):
    """cos(lat) approaches zero at the poles; the clamp must keep the
    longitude offset finite instead of dividing by ~0."""
    points = generate_grid(latitude, 0.0, grid_size=3, spacing_miles=1.5)

    assert len(points) == 9
    assert all(math.isfinite(lat) and math.isfinite(lng) for lat, lng in points)
