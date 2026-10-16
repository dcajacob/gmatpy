//$Id$
// GMAT Py modification, 2026-10-16: NASA algorithm retained with bounded
// lifecycle, validation, exact-root and reverse-communication repairs.
// Original attribution, public signatures and class layout are retained.
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
 * Defines a Brent-Dekker zero finder using bisection, linear interpolation,
 * and inverse quadratic interpolation to update a bracketed root estimate.
 *
 * NASA's interpolation/bisection formulas are retained. The inherited
 * cubic-spline bibliography described a different algorithm.
 */
//------------------------------------------------------------------------------


#ifndef BrentDekkerZero_hpp
#define BrentDekkerZero_hpp

#include "utildefs.hpp"

class GMATUTIL_API BrentDekkerZero
{
public:
   BrentDekkerZero();
   virtual ~BrentDekkerZero();
   BrentDekkerZero(const BrentDekkerZero &bdz);
   BrentDekkerZero&  operator=(const BrentDekkerZero &bdz);
   
   /// Initialize finite endpoints with a sign change or an exact endpoint zero.
   /// tolerance is a nonnegative absolute tolerance; a relative floor is added.
   void SetInterval(Real a0, Real b0, Real fa0, Real fb0, Real tolerance);
   /// Consume an evaluated point and return the next point to evaluate, or the
   /// best evaluated endpoint after convergence. First call may use either
   /// original endpoint. Invalid input raises a GMAT InterpolatorException.
   Real FindStep(Real lastStep, Real lastEval);
   /// Preserved convention: true means continue evaluating; false means done.
   bool CheckConvergence();
   
   // Method used to test the implementation
   Real TestDriver(Real aVal, Real bVal, Real tVal);
   
protected:
   // NASA workspace/layout retained: a/fa are the preceding evaluated point,
   // b/fb the best evaluated endpoint, c/fc its opposite bracket endpoint;
   // d/e are step history, p/q/r/s interpolation workspace, m half the bracket,
   // and tol the effective tolerance. A returned proposal is not stored as b
   // until its evaluation is consumed by FindStep.
   Real a;
   Real b;
   Real macheps;
   Real t;

   Real c;
   Real d;
   Real e;
   Real fa;
   Real fb;
   Real fc;
   Real tol;
   Real m;
   Real p;
   Real q;
   Real r;
   Real s;

   void SwapAC();
   void FindStepParameters();

   // Test function for the implementation
   Real TestFunction(Real value);
};

#endif /*BrentDekkerZero_hpp*/
