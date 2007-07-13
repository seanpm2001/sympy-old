"""
This module contains common special functions such
as trigonometric functions, orthogonal polynomials, the gamma function,
and so on.
"""

from factorials import factorial, factorial2, rising_factorial, \
    falling_factorial, binomial, gamma, lower_gamma, upper_gamma
from orthogonal_polynomials import legendre, legendre_zero, \
    chebyshev, chebyshev_zero
from zeta_functions import bernoulli, zeta