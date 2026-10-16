"""Regression checks for the installed wheel's public stepwise root finder."""

import math

import pytest

from gmatpy import native_session


def _finish(solver, function, point):
    for _ in range(200):
        # The historical API returns true while another evaluation is needed.
        if not solver.CheckConvergence():
            return point
        point = solver.FindStep(point, function(point))
    pytest.fail("BrentDekkerZero failed to converge within 200 evaluations")


def test_exact_zero_returns_the_evaluated_point():
    with native_session() as gmat:
        solver = gmat.BrentDekkerZero()
        solver.SetInterval(0.0, 3.0, -1.0, 2.0, 1e-12)
        point = solver.FindStep(3.0, 2.0)
        assert point == 1.0
        assert solver.CheckConvergence()
        # Previously this zero evaluation could return an unevaluated midpoint
        # and then stop because the stored function value was zero.
        assert solver.FindStep(point, 0.0) == point
        assert not solver.CheckConvergence()


@pytest.mark.parametrize("root", [0.0, 2.0])
def test_exact_endpoint_root(root):
    with native_session() as gmat:
        solver = gmat.BrentDekkerZero()
        solver.SetInterval(0.0, 2.0, -root, 2.0 - root, 1e-12)
        assert not solver.CheckConvergence()
        assert solver.FindStep(2.0, 2.0 - root) == root


@pytest.mark.parametrize("endpoints", [(0.0, 2.0), (2.0, 0.0)])
def test_copy_preserves_pending_nonlinear_solve(endpoints):
    function = lambda x: x * x - 2.0
    first, second = endpoints
    with native_session() as gmat:
        solver = gmat.BrentDekkerZero()
        solver.SetInterval(first, second, function(first), function(second), 1e-12)
        point = solver.FindStep(second, function(second))
        copied = gmat.BrentDekkerZero(solver)
        # Copy construction must retain the bracket and interpolation history.
        following = solver.FindStep(point, function(point))
        copied_following = copied.FindStep(point, function(point))
        assert copied_following == following
        assert copied.CheckConvergence() == solver.CheckConvergence()
        expected = pytest.approx(math.sqrt(2.0), rel=0.0, abs=3e-12)
        assert _finish(solver, function, following) == expected
        assert _finish(copied, function, copied_following) == expected


def test_subnormal_bracket_keeps_the_representable_zero():
    tiny = math.ulp(0.0)
    with native_session() as gmat:
        solver = gmat.BrentDekkerZero()
        solver.SetInterval(-tiny, tiny, -tiny, tiny, 0.0)
        assert solver.CheckConvergence()
        point = solver.FindStep(tiny, tiny)
        assert point == 0.0
        assert solver.FindStep(point, 0.0) == 0.0
        assert not solver.CheckConvergence()


@pytest.mark.parametrize("interval, message", [
    ((0.0, 1.0, 1.0, 2.0, 1e-12), "brackets a zero"),
    ((0.0, 1.0, -1.0, 1.0, -1.0), "nonnegative tolerance"),
    ((0.0, 1.0, -1.0, math.inf, 1e-12), "finite inputs"),
])
def test_invalid_interval_maps_to_python_exception(interval, message):
    with native_session() as gmat:
        solver = gmat.BrentDekkerZero()
        with pytest.raises(gmat.APIException, match=message):
            solver.SetInterval(*interval)


def test_invalid_evaluation_maps_to_python_exception_and_solver_recovers():
    with native_session() as gmat:
        solver = gmat.BrentDekkerZero()
        with pytest.raises(gmat.APIException, match="SetInterval"):
            solver.CheckConvergence()
        solver.SetInterval(-1.0, 1.0, -1.0, 1.0, 1e-12)
        for point, value in ((2.0, 2.0), (0.0, math.nan)):
            with pytest.raises(gmat.APIException, match="finite evaluation inside"):
                solver.FindStep(point, value)
        assert solver.FindStep(1.0, 1.0) == 0.0
        assert solver.FindStep(0.0, 0.0) == 0.0
        assert not solver.CheckConvergence()
