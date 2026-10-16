#include "CubicSplineInterpolator.hpp"
#include "NotAKnotInterpolator.hpp"
#include <memory>
extern "C" int evaluate_spline(int kind, const double *x, const double *y,
                               const double *queries, int count, double *output,
                               int refill)
{
    try {
        std::unique_ptr<Interpolator> spline;
        if (kind == 0) spline.reset(new CubicSplineInterpolator("candidate", 1));
        else spline.reset(new NotAKnotInterpolator("candidate", 1));
        spline->SetExtrapolation(true);
        if (refill) {
            for (int i=0; i<5; ++i) { double v=y[i]+5; spline->AddPoint(x[i], &v); }
            double prior;
            if (!spline->Interpolate(queries[0], &prior)) return 2;
            spline->Clear();
        }
        for (int i=0; i<5; ++i) spline->AddPoint(x[i], &y[i]);
        for (int i=0; i<count; ++i)
            if (!spline->Interpolate(queries[i], &output[i])) return 3;
        return 0;
    } catch (...) { return 1; }
}
