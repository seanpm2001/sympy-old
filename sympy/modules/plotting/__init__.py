import sys
import os
try:
    libdir = os.path.abspath(os.path.dirname(__file__))
    sys.path.insert(0, libdir)
except:
    pass

from cartesian import CartesianFunction
from polar import PolarFunction
from parametric import ParametricFunction

from plot import Plot
