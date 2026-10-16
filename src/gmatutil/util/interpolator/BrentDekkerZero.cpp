//$Id$
// GMAT Py modification, 2026-10-16: retain NASA's interpolation/bisection
// algorithm with initialized/copyable state, validated reverse communication,
// exact evaluated-root returns and quiet headless operation.
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
 * Implements NASA's Brent-Dekker interpolation/bisection algorithm.
 * The inherited cubic-spline bibliography described a different algorithm;
 * it is not evidence that replacement of this solver was required.
 */
//------------------------------------------------------------------------------

#include "BrentDekkerZero.hpp"
#include "InterpolatorException.hpp"
#include "MessageInterface.hpp"
#include <cmath>
#include <limits>

// Windows headers may define these macros; the finite-width helper uses max().
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
      return std::signbit(first) != std::signbit(second);
   }

   Real HalfDifference(Real first, Real second)
   {
      const Real halfMaximum = std::numeric_limits<Real>::max() * 0.5;
      if (OppositeSigns(first, second) &&
          (std::fabs(first) > halfMaximum || std::fabs(second) > halfMaximum))
         return first * 0.5 - second * 0.5;
      return (first - second) * 0.5;
   }
}

BrentDekkerZero::BrentDekkerZero() :
   a(0.), b(0.), macheps(1.0e-15), t(-1.), c(0.), d(0.), e(0.),
   fa(0.), fb(0.), fc(0.), tol(0.), m(0.), p(0.), q(0.), r(0.), s(0.)
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
   SwapAC();
   FindStepParameters();
}

Real BrentDekkerZero::FindStep(Real lastStep, Real lastEval)
{
   if (t < 0.)
      throw InterpolatorException("BrentDekkerZero requires SetInterval before FindStep");
   if (!std::isfinite(lastStep) || !std::isfinite(lastEval) ||
       lastStep < std::fmin(b, c) || lastStep > std::fmax(b, c))
      throw InterpolatorException("BrentDekkerZero requires a finite evaluation inside its current bracket");

   // b/c are evaluated bracket endpoints. The first call may repeat either
   // original endpoint; do not overwrite the opposite endpoint when it does.
   if (lastStep == b)
      fb = lastEval;
   else if (lastStep == c)
   {
      fc = lastEval;
      if (a == c)
         fa = lastEval;
   }
   else
   {
      b = lastStep;
      fb = lastEval;
      if (fb != 0. && fc != 0. && !OppositeSigns(fb, fc))
         SwapAC();
   }
   if (fb != 0. && fc != 0. && !OppositeSigns(fb, fc))
      throw InterpolatorException("BrentDekkerZero received values that no longer bracket a zero");
   FindStepParameters();
   if (!CheckConvergence())
      return b;

   if ((fabs(e) < tol) || (fabs(fa) <= fabs(fb)))
   {
      #ifdef DEBUG_ZERO_FINDER
         MessageInterface::ShowMessage("   |e|(%.12lf) < tol(%.12lf)? %s\n",
               e, tol, ((fabs(e) < tol) ? "true" : "false"));
         MessageInterface::ShowMessage("   |fa|(%.12lf) < |fb|(%.12lf)? %s\n",
               fa, fb, ((fabs(fa) <= fabs(fb)) ? "true" : "false"));
      #endif
      d = e = m;
   }
   else
   {
      s = fb / fa;
      if (a == c)
      {
         // Linear interpolation
         #ifdef DEBUG_ZERO_FINDER
            MessageInterface::ShowMessage("   Using Linear Interp\n");
         #endif
         p = 2 * m * s;
         q = 1 - s;
      }
      else
      {
         // Inverse quadratic interpolation
         #ifdef DEBUG_ZERO_FINDER
            MessageInterface::ShowMessage("   Using Inverse Q Interp\n");
         #endif
         q = fa / fc;
         r = fb / fc;
         p = s * (2.0 * m * q * (q - r) - (b - a) * (r - 1));
         q = (q - 1) * (r - 1) * (s - 1);
      }

      if (p > 0.0)
         q = -q;
      else
         p = -p;
      s = e;
      e = d;

      if ((2.0 * p < (3.0 * m * q - fabs(tol * q))) &&
          (p < fabs(0.5 * s * q)))
         d = p / q;
      else
         d = e = m;
   }

   a = b;
   fa = fb;

   // Keep b at the evaluated point until the next reverse-communication call.
   // NASA advanced b before checking an exact-zero evaluation, which could
   // report convergence while returning an unevaluated different point.
   Real proposal = b;
   if (fabs(d) > tol)
      proposal += d;
   else
      proposal += m > 0. ? tol : -tol;
   if (!std::isfinite(proposal) || proposal <= std::fmin(b, c) ||
       proposal >= std::fmax(b, c))
      proposal = b + m;
   if (proposal == b)
      proposal = std::nextafter(b, c);
   return proposal;
}

bool BrentDekkerZero::CheckConvergence()
{
   if (t < 0.)
      throw InterpolatorException("BrentDekkerZero requires SetInterval before CheckConvergence");
   return fabs(m) > tol && fb != 0. && std::nextafter(b, c) != c;
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
   c = a;
   fc = fa;
   d = e = b - a;
}

void BrentDekkerZero::FindStepParameters()
{
   if (fabs(fc) < fabs(fb))
   {
      a = b;
      b = c;
      c = a;
      fa = fb;
      fb = fc;
      fc = fa;
   }
   tol = 2.0 * macheps * fabs(b) + t;
   m = HalfDifference(c, b);
}

// TestDriver needs this definition even when iteration logging is disabled.
Real BrentDekkerZero::TestFunction(Real x)
{
   return 3.0 * x * x * x - x * x + 7.0 * x - 6.0;
}
