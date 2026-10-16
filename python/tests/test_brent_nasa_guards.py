"""Public behavior retained while returning to NASA's proposal formulas."""
import math

import pytest

from gmatpy import native_session


@pytest.mark.parametrize("endpoints", [(0., 2.), (2., 0.)])
@pytest.mark.parametrize("initial_endpoint", [0., 2.])
def test_either_original_endpoint_can_start_reverse_communication(endpoints, initial_endpoint):
    with native_session() as native:
        solver = native.BrentDekkerZero()
        first, second = endpoints
        solver.SetInterval(first, second, first*first - 2., second*second - 2., 1e-12)
        point = initial_endpoint
        for _ in range(200):
            point = solver.FindStep(point, point*point - 2.)
            if not solver.CheckConvergence():
                break
        else:
            pytest.fail("Root did not converge")
        assert point == pytest.approx(math.sqrt(2.), abs=3e-12, rel=0.)


def test_demo_driver_remains_linked_with_iteration_logging_disabled():
    with native_session() as native:
        point = native.BrentDekkerZero().TestDriver(0., 1., 1e-12)
        assert abs(3*point**3 - point**2 + 7*point - 6) < 1e-10
