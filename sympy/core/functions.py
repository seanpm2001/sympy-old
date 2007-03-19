"""This module provides an abstract class Function, as well as some mathematical
functions that use Function as its base class. 
"""

import hashing
from basic import Basic
from numbers import Rational, Real
import decimal

class Function(Basic):
    """Abstract class representing a mathematical function. 
    It is the base class for common fuctions such as exp, log, sin, tan, etc.
    """
    
    def __init__(self, arg):
        Basic.__init__(self)
        self.arg = self.sympify(arg)
        
    def hash(self):
        if self.mhash: 
            return self.mhash.value
        self.mhash = hashing.mhash()
        self.mhash.addstr(str(type(self)))
        self.mhash.addint(self.arg.hash())
        return self.mhash.value
    
    def diff(self, sym):
        return (self.derivative()*self.arg.diff(sym))
    
    def derivative(self):
        return Derivative(self,self.arg)
    
    def subs(self, old, new):
        e = Basic.subs(self,old,new)
        #if e==self:
        if e.isequal(self):
            return (type(self)(self.arg.subs(old,new)))
        else:
            return e
        
    def print_sympy(self):
        f = "%s(%s)"
        return f%(self.getname(),self.arg.print_sympy())

    def print_tex(self):
        f = "%s(%s)"
        return f%(self.getname_tex(),self.arg.print_tex())

    def print_pretty(self):
        from symbol import Symbol
        result = self.arg.print_pretty()
        if isinstance(self.arg, Symbol):
            return result.left(self.getname(), ' ')
        else:
            return result.parens().left(self.getname())

    def getname_tex(self):
        return r"{\rm %s}"%self.getname()
    
    def series(self, sym, n):
        from power import pole_error
        from symbol import Symbol
        try:
            return Basic.series(self,sym,n)
        except pole_error:
            pass
        #this only works, if arg(0) -> 0, otherwise we are in trouble
        arg = self.arg.series(sym,n)
        l = Symbol("l",dummy=True)
        #the arg(0) goes to z0
        z0 = arg.subs(log(sym),l).subs(sym,0)
        w = Symbol("w",True)
        e = type(self)(w)
        if arg.has(sym):
            e = e.series(w,n)
        e = e.subs(w,arg-z0)

        #this only works for exp 
        #generally, the problem is with expanding around other point
        #than arg == 0.
        assert isinstance(self,exp)
        e= (exp(z0)*e).expand().subs(l,log(sym))
        return e.expand()
    
    def evalf(self, precision=28):
        """
        Evaluate the current function to a real number.
        
        @param precision: the precision used in the calculations, 
        @type precision: C{int}
        @return: Real number
        
        """
        if not self.arg.isnumber():
            raise ValueError 
        raise NotImplementedError

class exp(Function):
    """Return e raised to the power of x
    """ 
    
    def getname(self):
        return "exp"
        
    def derivative(self):
        return exp(self.arg)
        
    def expand(self):
        return exp(self.arg.expand())
        
    def eval(self):
        arg = self.arg
        if isinstance(arg,Rational) and arg.iszero():
            return Rational(1)
        if isinstance(arg,log):
            return arg.arg
        return self

    def evalc(self):
        from numbers import I
        from addmul import Mul
        #we will need to move sin,cos to core
        from sympy.modules import cos,sin
        x,y = self.arg.get_re_im()
        return exp(x)*cos(y)+I*exp(x)*sin(y)
    
    def evalf(self, precision=28):
        if not self.arg.isnumber():
            raise ValueError 
        x = Real(self.arg) # argument to decimal (full precision)
        decimal.getcontext().prec = precision + 2
        i, lasts, s, fact, num = 0, 0, 1, 1, 1
        while s != lasts:
            lasts = s    
            i += 1
            fact *= i
            num *= x     
            s += num / fact   
        decimal.getcontext().prec = precision - 2        
        return +s

class log(Function):
    """Return the natural logarithm (base e) of x
    """
    
    def getname(self):
        return "log"
        
    def derivative(self):
        return Rational(1)/self.arg
        
    def eval(self):
        from addmul import Mul
        from power import Pow
        arg=self.arg
        if isinstance(arg,Rational) and arg.isone():
            return Rational(0)
        elif isinstance(arg,exp):
            return arg.arg
        elif isinstance(arg,Mul):
            a,b = arg.getab()
            return log(a)+log(b)
        elif isinstance(arg,Pow):
            return arg.exp * log(arg.base)
        return self
        
    def evalf(self):
        import math
        return math.log(self.arg.evalf())
        
    def series(self,sym,n):
        from numbers import Rational
        from power import pole_error
        try:
            return Basic.series(self,sym,n)
        except pole_error:
            pass
        arg=self.arg.series(sym,n)
        #write arg as=c0*w^e0*(1+Phi)
        #log(arg)=log(c0)+e0*log(w)+log(1+Phi)
        #plus we expand log(1+Phi)=Phi-Phi**2/2+Phi**3/3...
        w = sym
        c0,e0 = arg.leadterm(w)
        Phi=(arg/(c0*w**e0)-1).expand()
        if c0.isnumber():
            assert c0.evalf()>0
        e=log(c0)+e0*log(w)
        for i in range(1,n+1):
            e+=(-1)**(i+1) * Phi**i /i
        return e

ln = log
    
class abs_(Function):
    """Return the absolute value of x"""
    
    
    def eval(self):
        from addmul import Mul,Add
        from symbol import Symbol
        from numbers import I
        
        arg = self.arg
        if arg.isnumber() or (isinstance(arg, Symbol) and arg.real):
            return (arg*arg.conjugate()).expand()**Rational(1,2)
        elif isinstance(arg, Mul):
            _t = arg.getab()[0]
            if _t.isnumber() and _t < 0:
                return abs(-self.arg)
        elif isinstance(arg, Add):
            b,a = arg.getab()
            if isinstance(a, Symbol) and a.real:
                if isinstance(b, Mul):
                    a,b=b.getab()
                    if a == I:
                        if isinstance(b, Symbol) and b.real:
                            return (arg*arg.conjugate()).expand()**Rational(1,2)
        return self
        
    def evalf(self):
        if self.arg.isnumber():
            return self.eval()
        else:
            raise ValueError
        
    def derivative(self):
        return sign(self.arg)
    
    def getname(self):
        return "abs"
    
    def series(self):
        pass
    
    def x__eq__(self, a):
        #FIXME: currently this does not work
        # here we are checking for function equality, like in
        # abs(x) == abs(-x)
        if isinstance(a, abs_): 
            if a.arg**2 == self.arg**2:
                return true
            else:
                return False
        raise ArgumentError("Wrong function arguments")
    
class sign(Function):
    
    def getname(self):
        return "sign"
    
    def eval(self):
        if self.arg.isnumber():
            if self.arg < 0:
                return Rational(-1)
            elif self.arg == 0:
                return Rational(0)
            else:
                return Rational(1)
        return self
            
    def evalf(self, precision=28):
        if isnumber(self.arg):
            return self.eval()
        else:
            raise ArgumentError
        
    def derivative(self):
        return Rational(0)
    

class Derivative(Basic):

    def __init__(self,f,x):
        Basic.__init__(self)
        self.f=self.sympify(f)
        self.x=self.sympify(x)

    def doit(self):
        return self.f.diff(self.x)

    def hash(self):
        if self.mhash: 
            return self.mhash.value
        self.mhash = hashing.mhash()
        self.mhash.addstr(str(type(self)))
        self.mhash.addint(self.f.hash())
        self.mhash.addint(self.x.hash())
        return self.mhash.value

    def diff(self,x):
        return Derivative(self,x)

    def print_sympy(self):
        if isinstance(self.f,Function):
            return "%s'(%r)"%(self.f.getname(),self.f.arg)
        else:
            return "(%r)'"%self.f

    def print_tex(self):
        if isinstance(self.f,Function):
            return r"{\rm %s}'(%s)"%(self.f.getname(),self.f.arg.print_tex())
        else:
            return "(%s)'"%self.f.print_tex()
