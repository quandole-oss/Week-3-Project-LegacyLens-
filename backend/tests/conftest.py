"""Shared test fixtures for LegacyLens backend tests."""

import pytest

# Sample LAPACK-style Fortran source for testing the chunker
SAMPLE_FORTRAN_F77 = """\
*> \\brief <b> DGESV computes the solution to system of linear equations A * X = B</b>
*
*  =========== DOCUMENTATION ===========
*
*  Purpose
*  =======
*
*  DGESV computes the solution to a real system of linear equations
*     A * X = B,
*  where A is an N-by-N matrix and X and B are N-by-NRHS matrices.
*
*  Arguments
*  =========
*
*  N       (input) INTEGER
*          The number of linear equations.
*
*  Further Details
*  ===============
*
*  Based on LAPACK routine from Univ. of Tennessee.
*
*  =====================================================================
      SUBROUTINE DGESV( N, NRHS, A, LDA, IPIV, B, LDB, INFO )
*
*     .. Scalar Arguments ..
      INTEGER            INFO, LDA, LDB, N, NRHS
*     ..
*     .. Array Arguments ..
      INTEGER            IPIV( * )
      DOUBLE PRECISION   A( LDA, * ), B( LDB, * )
*     ..
*
*     .. External Subroutines ..
      EXTERNAL           DGETRF, DGETRS, XERBLA
*     ..
*     .. Intrinsic Functions ..
      INTRINSIC          MAX
*     ..
*     Compute LU factorization
      CALL DGETRF( N, N, A, LDA, IPIV, INFO )
*     Solve system
      CALL DGETRS( 'No transpose', N, NRHS, A, LDA, IPIV, B, LDB,
     $             INFO )
      RETURN
*
*     End of DGESV
*
      END SUBROUTINE DGESV
"""

SAMPLE_FORTRAN_DOUBLE_STAR = """\
**  Purpose
**  =======
**
**  DLANGE returns the value of the one norm.
**
**  Arguments
**  =========
**
**  NORM    (input) CHARACTER*1
**          The type of norm.
**
      FUNCTION DLANGE( NORM, M, N, A, LDA, WORK )
      DOUBLE PRECISION   DLANGE
      CHARACTER          NORM
      INTEGER            M, N, LDA
      DOUBLE PRECISION   A( LDA, * ), WORK( * )
      DLANGE = 0.0D0
      RETURN
      END FUNCTION DLANGE
"""

SAMPLE_FORTRAN_NO_ROUTINES = """\
C     This is a data file with no routines
C     Just some comment lines
      DATA X / 1.0, 2.0, 3.0 /
      DATA Y / 4.0, 5.0, 6.0 /
"""


@pytest.fixture
def sample_fortran_f77():
    return SAMPLE_FORTRAN_F77


@pytest.fixture
def sample_fortran_double_star():
    return SAMPLE_FORTRAN_DOUBLE_STAR


SAMPLE_FORTRAN_WITH_COMMON = """\
*  Purpose
*  =======
*
*  Routine with COMMON blocks and INCLUDEs.
*
      SUBROUTINE FOOBAR( N )
      INTEGER N
      COMMON /WORK/ TEMP(100)
      COMMON /PARAMS/ TOL, MAXITER
      INCLUDE 'lapack.inc'
      INCLUDE 'blas.inc'
      TEMP(1) = TOL
      RETURN
      END SUBROUTINE FOOBAR
"""


@pytest.fixture
def sample_fortran_no_routines():
    return SAMPLE_FORTRAN_NO_ROUTINES


@pytest.fixture
def sample_fortran_with_common():
    return SAMPLE_FORTRAN_WITH_COMMON
