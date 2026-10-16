//$Id$
// GMAT Py modification, 2026-10-01: independently replaced the entire
// inherited root-finder implementation using inverse interpolation and
// bisection derived from Brent's published mathematics, under Apache-2.0.
// The old Numerical Recipes citation did not establish source provenance;
// no Numerical Recipes or other solver implementation was copied. Retained
// the public stepwise API and CheckConvergence's true-means-continue convention.
//------------------------------------------------------------------------------
//                            BrentDekkerZero
//------------------------------------------------------------------------------
// GMAT: General Mission Analysis Tool
//
// Copyright (c) 2002-2026 United States Government as represented by the
// Administrator of the National Aeronautics and Space Administration.
// All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License"); 
// You may not use this file except in compliance with the License. 
// You may obtain a copy of the License at:
// http://www.apache.org/licenses/LICENSE-2.0 
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either 
// express or implied.   See the License for the specific language
// governing permissions and limitations under the License.
//
// Developed jointly by NASA/GSFC and Thinking Systems, Inc. under contract
// NNG06CA54C
//
// Author: Darrel J. Conway, Thinking Systems, Inc.
// Created: 2009/04/10
//
/**
 * Implements a Brent-Dekker zero finder using bisection, linear interpolation,
 * and inverse quadratic interpolation to update a bracketed root estimate.
 *
 * Mathematical reference: R. P. Brent, An algorithm with guaranteed
 * convergence for finding a zero of a function, Computer Journal 14 (1971),
 * 422-425, sections 1-7; Algorithms for Minimization without Derivatives
 * (1973), chapter 4. New code implements the mathematics, not published code.
 */
//------------------------------------------------------------------------------


#include "BrentDekkerZero.hpp"
#include "InterpolatorException.hpp"
#include <algorithm>
#include <cmath>
#include <limits>

// GMAT Py 2026-10-15: Windows headers define min/max macros; this
// implementation needs the standard-library overloads in this translation unit.
#ifdef min
#undef min
#endif
#ifdef max
#undef max
#endif

namespace
{
   bool OppositeSigns(Real first, Real second)
   {
      // Test signs directly: multiplying function values can under/overflow.
      return std::signbit(first) != std::signbit(second);
   }

   Real HalfDifference(Real first, Real second)
   {
      // Subtract before halving to preserve subnormal-width brackets. For
      // large opposite signs, halve first to avoid overflowing the difference.
      const Real halfMaximum = std::numeric_limits<Real>::max() * 0.5;
      if (OppositeSigns(first, second) &&
          (std::fabs(first) > halfMaximum || std::fabs(second) > halfMaximum))
         return first * 0.5 - second * 0.5;
      return (first - second) * 0.5;
   }

   long double SecantEstimate(Real left, Real right, Real fLeft, Real fRight)
   {
      const long double scale = std::max(std::fabs(fLeft), std::fabs(fRight));
      const long double l = fLeft / scale;
      const long double r = fRight / scale;
      return right + (static_cast<long double>(left) - right) * r / (r - l);
   }

   long double InverseQuadraticEstimate(Real first, Real best, Real previous,
                                        Real fFirst, Real fBest, Real fPrevious)
   {
      // Regard x as a quadratic function of f. Evaluate its Lagrange basis at
      // f=0, using offsets about best to avoid summing large absolute epochs:
      // x(0)-best = sum_i (x_i-best) product_{j!=i} f_j/(f_i-f_j).
      // This generic interpolation construction is independently authored.
      const long double scale = std::max({std::fabs(fFirst), std::fabs(fBest),
                                          std::fabs(fPrevious)});
      const long double positions[3] = {first, best, previous};
      const long double values[3] = {fFirst / scale, fBest / scale, fPrevious / scale};
      long double displacement = 0.;
      for (Integer i = 0; i < 3; ++i)
      {
         if (i == 1)
            continue; // Its offset about best is zero.
         long double weight = 1.;
         for (Integer j = 0; j < 3; ++j)
            if (i != j)
            {
               const long double separation = values[i] - values[j];
               if (separation == 0.)
                  return std::numeric_limits<long double>::quiet_NaN();
               weight *= values[j] / separation;
            }
         displacement += (positions[i] - best) * weight;
      }
      return best + displacement;
   }
}

BrentDekkerZero::BrentDekkerZero() :
   a(0.), b(0.), macheps(1.0e-15), t(-1.), c(0.), d(0.), e(0.),
   fa(0.), fb(0.), fc(0.), tol(0.), m(0.), p(1.), q(0.), r(0.), s(0.)
{
}

BrentDekkerZero::~BrentDekkerZero() = default;
BrentDekkerZero::BrentDekkerZero(const BrentDekkerZero &other) = default;
BrentDekkerZero& BrentDekkerZero::operator=(const BrentDekkerZero &other) = default;

void BrentDekkerZero::SetInterval(Real first, Real second, Real fFirst,
                                 Real fSecond, Real tolerance)
{
   if (!std::isfinite(first) || !std::isfinite(second) ||
       !std::isfinite(fFirst) || !std::isfinite(fSecond) ||
       !std::isfinite(tolerance) || tolerance < 0.)
      throw InterpolatorException("BrentDekkerZero requires finite inputs and a nonnegative tolerance");
   if (fFirst != 0. && fSecond != 0. &&
       (first == second || !OppositeSigns(fFirst, fSecond)))
      throw InterpolatorException("BrentDekkerZero requires an interval that brackets a zero");

   a = first;
   b = second;
   fa = fFirst;
   fb = fSecond;
   t = tolerance;
   FindStepParameters();
   SwapAC();
}

Real BrentDekkerZero::FindStep(Real lastStep, Real lastEval)
{
   if (t < 0.)
      throw InterpolatorException("BrentDekkerZero requires SetInterval before FindStep");
   if (!std::isfinite(lastStep) || !std::isfinite(lastEval) ||
       lastStep < std::min(a, b) || lastStep > std::max(a, b))
      throw InterpolatorException("BrentDekkerZero requires a finite evaluation inside its current bracket");

   if (lastStep == a)
      fa = lastEval;
   else if (lastStep == b)
      fb = lastEval;
   else
   {
      // Retain evaluated history for inverse interpolation and step safeguards.
      const Real previousBest = b;
      const Real previousValue = fb;
      if (lastEval == 0. || OppositeSigns(fa, lastEval))
      {
         b = lastStep;
         fb = lastEval;
      }
      else
      {
         a = lastStep;
         fa = lastEval;
      }
      d = c;
      c = previousBest;
      fc = previousValue;
   }
   if (fa != 0. && fb != 0. && !OppositeSigns(fa, fb))
      throw InterpolatorException("BrentDekkerZero received values that no longer bracket a zero");
   FindStepParameters();
   if (!CheckConvergence())
      return b;

   long double estimate;
   if (fa != fb && fa != fc && fb != fc)
      estimate = InverseQuadraticEstimate(a, b, c, fa, fb, fc);
   else
      estimate = SecantEstimate(a, b, fa, fb);

   // Brent/Dekker safeguards: interpolation must remain within the bracket,
   // move at most three quarters of its width, and halve the relevant recent
   // movement. Otherwise bisect. p records whether the preceding proposal was
   // a bisection; c/d are the preceding two evaluated best points.
   const long double width = std::fabs(static_cast<long double>(a) - b);
   const long double movement = std::fabs(estimate - b);
   const long double recent = p != 0. ?
      std::fabs(static_cast<long double>(b) - c) :
      std::fabs(static_cast<long double>(c) - d);
   const bool interpolate = std::isfinite(estimate) &&
      estimate > std::min(a, b) && estimate < std::max(a, b) &&
      movement < 0.75L * width && movement < 0.5L * recent && recent > tol;
   p = interpolate ? 0. : 1.;
   if (!interpolate)
      estimate = static_cast<long double>(a) * 0.5L + static_cast<long double>(b) * 0.5L;

   // Make a representable minimum step toward the other bracket endpoint.
   if (std::fabs(estimate - b) < tol)
      estimate = static_cast<long double>(b) + (a > b ? tol : -tol);
   s = static_cast<Real>(estimate);
   if (s == b)
      s = std::nextafter(b, a);
   if (s <= std::min(a, b) || s >= std::max(a, b))
      s = a * 0.5 + b * 0.5;
   e = s - b;
   return s;
}

bool BrentDekkerZero::CheckConvergence()
{
   if (t < 0.)
      throw InterpolatorException("BrentDekkerZero requires SetInterval before CheckConvergence");
   // Historical API semantics: true requests another evaluation; false means
   // an evaluated endpoint is exact, the bracket is within tolerance, or no
   // floating-point number remains strictly inside it.
   return fb != 0. && std::fabs(m) > tol && std::nextafter(b, a) != a;
}

Real BrentDekkerZero::TestDriver(Real first, Real second, Real tolerance)
{
   SetInterval(first, second, TestFunction(first), TestFunction(second), tolerance);
   Real evaluated = b;
   while (CheckConvergence())
      evaluated = FindStep(evaluated, TestFunction(evaluated));
   return b;
}

void BrentDekkerZero::SwapAC()
{
   // Initialize interpolation history. Existing protected fields are retained
   // to preserve the class layout; q/r are unused legacy workspace.
   c = a;
   fc = fa;
   d = a;
   e = 0.;
   p = 1.;
   q = r = 0.;
   s = b;
}

void BrentDekkerZero::FindStepParameters()
{
   // b is always the best evaluated endpoint, a the opposite-sign endpoint.
   if (std::fabs(fa) < std::fabs(fb))
   {
      std::swap(a, b);
      std::swap(fa, fb);
   }
   tol = t + 2. * macheps * std::fabs(b);
   m = HalfDifference(a, b);
}

Real BrentDekkerZero::TestFunction(Real value)
{
   // Preserve the existing demonstration polynomial in Horner form.
   return ((3. * value - 1.) * value + 7.) * value - 6.;
}
