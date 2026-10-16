//$Id$
//------------------------------------------------------------------------------
//                            CubicSplineInterpolator
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
// number S-67573-G
//
// Author: Darrel J. Conway, Thinking Systems, Inc.
// Created: 2003/12/02
//
/**
 * Implements a natural cubic spline by solving the second-derivative
 * continuity equations and evaluating each interval as a cubic polynomial.
 */
// GMAT Py modification, 2026-10-01: independently replaced the inherited
// Numerical Recipes-based BuildSplines and Estimate routines using the
// mathematical equations documented below, under Apache-2.0. Public buffer,
// descending-knot, natural-endpoint, and extrapolation behavior is retained.
// Rebuild after every buffer load so Clear/refill cannot reuse stale curvature;
// coincident knots now fail validation before any division by zero.
// GMAT Py modification, 2026-10-16: evaluate in normalized interval coordinates
// and return stored values at exact knots, avoiding endpoint cancellation and
// overflow from forming an unscaled cubic coefficient on very short intervals.
//------------------------------------------------------------------------------


#include "CubicSplineInterpolator.hpp"
#include "MessageInterface.hpp"
#include <cmath>

//#define DUMP_SPLINE_POINTS

//---------------------------------
//  public methods
//---------------------------------

//------------------------------------------------------------------------------
//  CubicSplineInterpolator(const std::string &name, Integer dim)
//------------------------------------------------------------------------------
/**
 * Constructs cubic spline interpolator (default constructor).
 * 
 * @param <name> Name for this interpolator.
 * @param <dim>  The dimension of the vector that is interpolated.
 */
//------------------------------------------------------------------------------
CubicSplineInterpolator::CubicSplineInterpolator(const std::string &name,
                                                 Integer dim) :
   Interpolator        (name, "CubicSplineInterpolator", dim),
   lastX               (-9.9999e75)
{
   bufferSize = 5;
   requiredPoints = 5;
   Integer i;
   for (i = 0; i < bufferSize; ++i)
   {
      x[i]  = -9.9999e75;
      y[i]  = NULL;
      y2[i] = NULL;
   }
}


//------------------------------------------------------------------------------
//  ~CubicSplineInterpolator()
//------------------------------------------------------------------------------
/**
 * Destroys cubic spline interpolator (destructor).
 */
//------------------------------------------------------------------------------
CubicSplineInterpolator::~CubicSplineInterpolator()
{
   CleanupArrays();
}


//------------------------------------------------------------------------------
//  CubicSplineInterpolator(const CubicSplineInterpolator &csi)
//------------------------------------------------------------------------------
/**
 * Constructs cubic spline interpolator, based on another (copy constructor).
 * 
 * @param csi The original that is being copied.
 */
//------------------------------------------------------------------------------
CubicSplineInterpolator::CubicSplineInterpolator
                                          (const CubicSplineInterpolator &csi) :
   Interpolator       (csi),
   lastX              (csi.lastX)
{
   Integer i;
   for (i = 0; i < bufferSize; ++i)
   {
      x[i]  = -9.9999e75;
      y[i]  = NULL;
      y2[i] = NULL;
   }
}


//------------------------------------------------------------------------------
//  CubicSplineInterpolator& operator=(const CubicSplineInterpolator &csi)
//------------------------------------------------------------------------------
/**
 * Sets this cubic spline interpolator to match another (assignment operator).
 * 
 * @param csi The original that is being copied.
 * 
 * @return A reference to the copy (aka *this).
 */
//------------------------------------------------------------------------------
CubicSplineInterpolator& CubicSplineInterpolator::operator=
                                            (const CubicSplineInterpolator &csi)
{
   if (&csi == this)
      return *this;

   CleanupArrays();
   
   CopyArrays(csi);
   lastX = csi.lastX;
   return *this;
}


//------------------------------------------------------------------------------
//  bool Interpolate(const Real ind, Real *results)
//------------------------------------------------------------------------------
/**
 * Perform the interpolation.
 * 
 * This method is the core interface for the cubic spline interpolation.  It 
 * calls protected methods to build the splines and to estimate the state at the
 * input value of the independent parameter (ind).
 * 
 * @param ind       The value of the independent parameter.
 * @param results   Data structure for the estimates.
 * 
 * @return true on success, false on failure.
 */
//------------------------------------------------------------------------------
bool CubicSplineInterpolator::Interpolate(const Real ind, Real *results)
{
   if (pointCount < requiredPoints)
      throw InterpolatorException("ERROR - CublicSplineInterpolator: " +
         GmatStringUtil::ToString(requiredPoints, 1) + " points "
         "are required for interpolation, but only " +
         GmatStringUtil::ToString(pointCount, 1) + " were provided.\n");
        
   bool retval = BuildSplines();
   if (retval)
      retval = Estimate(ind, results);
      
   #ifdef DUMP_SPLINE_POINTS
      MessageInterface::ShowMessage("Cubic spline data points:\n");
      
      Real increment = (x[bufferSize - 1] - x[0]) / 100.0, xval;
      Real *dumpData = new Real[dimension];
      for (Integer i = 0; i <= 100; ++i)
      {
         xval = x[0] + i * increment;
         Estimate(xval, dumpData);
         MessageInterface::ShowMessage("   %.12lf", xval);
         for (Integer j = 0; j < dimension; ++j)
            MessageInterface::ShowMessage("   %.12lf", dumpData[j]);
         MessageInterface::ShowMessage("\n");
      } 
      
      delete [] dumpData;   
   #endif

   return retval;
}


//---------------------------------
//  protected methods
//---------------------------------


//------------------------------------------------------------------------------
//  void AllocateArrays()
//------------------------------------------------------------------------------
/**
 * Allocates spline buffers and calls the base method to build the ring buffer.  
 */
//------------------------------------------------------------------------------
void CubicSplineInterpolator::AllocateArrays()
{
   Interpolator::AllocateArrays();

   Integer i;
   for (i = 0; i < bufferSize; ++i)
   {
      y[i]  = new Real[dimension];
      y2[i] = new Real[dimension];
   }
    
   latestPoint = -1;
}


//------------------------------------------------------------------------------
//  void CleanupArrays()
//------------------------------------------------------------------------------
/**
 * Frees the memory used by the spline buffer and calls the base method to 
 * manage the ring buffer.
 */
//------------------------------------------------------------------------------
void CubicSplineInterpolator::CleanupArrays()
{
   Integer i = 0;
   if (y2[i]) {
      for (i = 0; i < bufferSize; ++i)
      {
         delete [] y[i];
         y[i] = NULL;
         delete [] y2[i];
         y2[i] = NULL;
      }
   }
    
   Interpolator::CleanupArrays();
}


//------------------------------------------------------------------------------
//  void CopyArrays(const Interpolator &i)
//------------------------------------------------------------------------------
/**
 * Copies the ring buffer from one Interpolator to this one.  
 * 
 * @param i The Interpolator that supplies the data copied to this one.
 */
//------------------------------------------------------------------------------
void CubicSplineInterpolator::CopyArrays(const CubicSplineInterpolator &i)
{
   Interpolator::CopyArrays(i);
   Integer j;
   for (j = 0; j < bufferSize; ++j)
   {
      x[j] = i.x[j];
      memcpy( y[j],  i.y[j], dimension*sizeof(Real));
      memcpy(y2[j], i.y2[j], dimension*sizeof(Real));
   }
}


//------------------------------------------------------------------------------
//  bool BuildSplines()
//------------------------------------------------------------------------------
/**
 * Uses the data in the ring buffer to build the cubic splines.
 * 
 * The new implementation follows directly from interpolation of the knot
 * values and continuity of the first and second derivatives. If M[i] is the
 * second derivative at knot i, h[i] = x[i+1]-x[i], and s[i] is the secant slope,
 * each interior row is
 *
 *   h[i-1] M[i-1] + 2(h[i-1]+h[i]) M[i] + h[i] M[i+1]
 *     = 6(s[i]-s[i-1]).
 *
 * The natural endpoint conditions set M[0] = M[4] = 0, leaving a three-row
 * tridiagonal system. Gaussian elimination and back substitution solve that
 * system independently for each dependent variable. No implementation from
 * Numerical Recipes or another spline library was copied.
 * 
 * @return true on success, false on failure.
 */
//------------------------------------------------------------------------------
bool CubicSplineInterpolator::BuildSplines()
{
   Integer i, j;
   Real widths[4], diagonal[3], rhs[3];
    
   // Set x and y from the ring buffer
   LoadArrays();

   // Recompute the small three-row system. The final knot alone cannot identify
   // a spline: Clear/refill can retain it while changing the other knots or y.
    
   // Check monotonicity -- the spline algorithm requires it.  I could throw an
   // exception here, but the calling code might prefer to drop back to an
   // alternative interpolator (e.g. a linear interpolator) or to generate more
   // densely packed data for the buffer if the cubic spline fails at this
   // stage.
   for (i = 1; i < 5; ++i)
   {
      if (dataIncreases)
      {
         if (x[i] <= x[i-1]) {
            return false;
         }
      }
      else
      {
         if (x[i] >= x[i-1])
         {
            return false;
         }
      }
   }
   for (i = 0; i < 4; ++i)
      widths[i] = x[i+1] - x[i];
    
   // Loop through the dependent variables
   for (j = 0; j < dimension; ++j)
   {
      for (i = 0; i < 3; ++i)
      {
         diagonal[i] = 2.0 * (widths[i] + widths[i+1]);
         rhs[i] = 6.0 * ((y[i+2][j] - y[i+1][j]) / widths[i+1]
            - (y[i+1][j] - y[i][j]) / widths[i]);
         if (i > 0)
         {
            const Real factor = widths[i] / diagonal[i-1];
            diagonal[i] -= factor * widths[i];
            rhs[i] -= factor * rhs[i-1];
         }
      }
      y2[0][j] = 0.0;
      y2[4][j] = 0.0;
      y2[3][j] = rhs[2] / diagonal[2];
      for (i = 1; i >= 0; --i)
      {
         y2[i+1][j] = (rhs[i] - widths[i+1] * y2[i+2][j]) / diagonal[i];
      }
   }
   lastX = x[4];
    
   return true;
}


//------------------------------------------------------------------------------
//  void LoadArrays(void)
//------------------------------------------------------------------------------
/**
 * Use the ring buffer to load the arrays used to build the splines.
 */
//------------------------------------------------------------------------------
void CubicSplineInterpolator::LoadArrays(void)
{
   Integer i, j, start = 0;
   Real sign = (dataIncreases ? 1.0 : -1.0);
   Real temp = sign * independent[0];

   for (i = 1; i < bufferSize; ++i)
   {
      if (sign*independent[i] < temp)
      {
         start = i;
         temp = sign*independent[i];
      }
   }
    
   for (i = 0; i < bufferSize; ++i, ++start)
   {
      if (start == bufferSize)
         start = 0;
      x[i] = independent[start];
      for (j = 0; j < dimension; ++j)
         y[i][j] = dependent[start][j];
   }
}


//------------------------------------------------------------------------------
//  bool Estimate(const Real ind, Real *results)
//------------------------------------------------------------------------------
/**
 * Perform the estimation using the information from the splines.  
 * 
 * This method is invoked after calling BuildSplines(), using the input 
 * parameters from the Interpolate() method. Let t and u be the distances from
 * the left and right knots divided by the interval width, so t+u=1. The linear
 * blend u*yLeft+t*yRight has zero curvature. The correction
 *
 *   -t*u*((1+u)*h*h*MLeft + (1+t)*h*h*MRight)/6
 *
 * vanishes at both endpoints and supplies the prescribed second derivatives.
 * Scale each second derivative by h twice before forming this correction;
 * no coefficient proportional to M/h is required. Exact knots return their
 * stored values without polynomial arithmetic.
 * 
 * @param ind       The value of the independent parameter.
 * @param results   Data structure for the estimates.
 * 
 * @return true on success, false on failure.
 */
//------------------------------------------------------------------------------
bool CubicSplineInterpolator::Estimate(const Real ind, Real *results)
{
   Integer i, kl = -1, kh;
   Real h;

   // First find the spline we want -- for GMAT, this is more likely to be the
   // last one, so we'll start at the end and work backwards
   for (i = 3; i >= 0; --i)
   {
      if (dataIncreases)
      {
         if ((x[i] <= ind) && (x[i+1] >= ind))
         {
            kl = i;
            break;
         }
      }
      else
      {
         if ((x[i] >= ind) && (x[i+1] <= ind))
         {
            kl = i;
            break;
         }
      }
   }
   if (kl == -1)       // Calls for extrapolation rather than interpolation
   {
      if (allowExtrapolation)
         kl = 0;
      else 
         return false;
   }
        
   kh = kl + 1;
   h = x[kh] - x[kl];
   if (h == 0)
      return false;       // Coincident points are not allowed
    
   if (ind == x[kl] || ind == x[kh])
   {
      const Integer knot = (ind == x[kl] ? kl : kh);
      for (i = 0; i < dimension; ++i)
         results[i] = y[knot][i];
      return true;
   }

   const Real t = (ind - x[kl]) / h;
   const Real u = (x[kh] - ind) / h;
    
   // Finally, evaluate the spline!
   for (i = 0; i < dimension; ++i)
   {
      // A linear segment needs no curvature arithmetic. Use normalized
      // coordinates when finite: dividing a tiny change in y by a large h
      // can underflow the physical slope. Anchor at the nearer endpoint to
      // retain a small endpoint value. For a coordinate overflow during
      // distant extrapolation, the physical slope can still give a finite
      // result when the changes in x and y have compensating scales.
      if (y2[kl][i] == 0.0 && y2[kh][i] == 0.0)
      {
         if (y[kl][i] == y[kh][i])
            results[i] = y[kl][i];
         else if (std::isfinite(t) && std::isfinite(u))
            results[i] = (t <= u ?
               y[kl][i] + t * (y[kh][i] - y[kl][i]) :
               y[kh][i] + u * (y[kl][i] - y[kh][i]));
         else
         {
            const Real slope = (y[kh][i] - y[kl][i]) / h;
            results[i] = y[kl][i] + (ind - x[kl]) * slope;
         }
         continue;
      }
      const Real leftCurvature = (y2[kl][i] * h) * h;
      const Real rightCurvature = (y2[kh][i] * h) * h;
      const Real weightedCurvature =
         ((1.0 + u) * leftCurvature + (1.0 + t) * rightCurvature) / 6.0;
      // Apply the curvature scale before multiplying the two coordinates;
      // t*u alone can overflow during otherwise finite extrapolation.
      const Real correction = -(weightedCurvature * t) * u;
      // Anchor the linear part at the nearer endpoint to retain small distances
      // near either knot, and preserve constant values during extrapolation.
      const Real linear = (t <= u ?
         y[kl][i] + t * (y[kh][i] - y[kl][i]) :
         y[kh][i] + u * (y[kl][i] - y[kh][i]));
      results[i] = linear + correction;
   }
    
   return true;
}

//------------------------------------------------------------------------------
//  GmatBase* Clone() const
//------------------------------------------------------------------------------
/**
 * This method returns a clone of the CubicSplineInterpolator.
 *
 * @return clone of the CubicSplineInterpolator.
 */
//------------------------------------------------------------------------------
Interpolator* CubicSplineInterpolator::Clone() const
{
   return (new CubicSplineInterpolator(*this));
}
