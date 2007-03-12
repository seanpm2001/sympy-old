class AutomaticEvaluationType(type):
    def __call__(self,*args,**kwargs):
        if kwargs.has_key("evaluate"):
            evaluate = kwargs["evaluate"]
            del kwargs["evaluate"]
        else:
            evaluate = True
        obj=type.__call__(self,*args,**kwargs)
        if evaluate: return obj.eval()
        else: return obj

outputType="sympy" #sympy, pretty

class Basic(object):
    
    __metaclass__ = AutomaticEvaluationType
    
    def __init__(self):
        self.mhash = 0
        
    def __repr__(self):
        return str(self)

    def __str__(self):
        if outputType == "sympy":
            return self.print_sympy()
        elif outputType == "pretty":
            return str(self.print_pretty())
        else:
            raise NotImplementedError("Unknown outputType=%s"%outputType)
    
    def __neg__(self):
        from numbers import Rational
        return self._domul(Rational(-1),self)
        
    def __pos__(self):
        return self
        
    def __add__(self,a):
        return self._doadd(self, a)
   
    def __float__(self):
        return float(self.evalf())
 
    def __abs__(self):
        """Returns the absolute value of self. 
        
        Example usage: 
          >>> from sympy import *
          >>> abs(1+2*I)
          5^(1/2)
          >>> x = Symbol('x')
          >>> abs(-x)
          abs(x)
        """
        from functions import abs_
        return abs_(self)
        
    def __radd__(self,a):
        return self._doadd(a, self)
        
    def __sub__(self,a):
        return self._doadd(self, -a)
        
    def __rsub__(self,a):
        return self._doadd(a, -self)
        
    def __mul__(self,a):
        try:
            a=self.sympify(a)
        except:
            return a.__rmul__(self)
        return self._domul(self, a)
        
    def __rmul__(self,a):
        return self._domul(a, self)
        
    def __div__(self,a):
        from numbers import Rational
        return self._domul(self,self._dopow(a,Rational(-1)))
        
    def __rdiv__(self,a):
        from numbers import Rational
        return self._domul(self.sympify(self) ** Rational(-1), self.sympify(a))
        
    def __pow__(self,a):
        return self._dopow(self, a)
        
    def __rpow__(self,a):
        return self._dopow(a, self)
        
    def __eq__(self,a):
        return self.isequal(self.sympify(a))
        
    def __ne__(self,a):
        return not self.__eq__(a)
        
    def __lt__(self,a):
        from sympy.core.numbers import Real
        if _isnumber(self) and _isnumber(a): 
            return self.evalf() < Real(a).evalf()
        else:
            raise NotImplementedError("'<' not supported.")
        
    def __gt__(self,a):
        from numbers import Real
        if _isnumber(self) and _isnumber(a): 
            return self.evalf() > Real(a).evalf()
        else:
            raise NotImplementedError("'<' not supported.")
        
    @staticmethod
    def _doadd(a,b):
        from addmul import Add
        return Add(Basic.sympify(a), Basic.sympify(b))

    @staticmethod
    def _domul(a, b):
        from addmul import Mul
        return Mul(Basic.sympify(a), Basic.sympify(b))

    @staticmethod
    def _dopow(a, b):
        from addmul import Pow
        return Pow(Basic.sympify(a), Basic.sympify(b))

    def eval(self):
        """Returns canonical form of myself. 
        
        The eval() method should alway return a new object (following the
        general rule of not changing)
        
        """
        return self
   
    def evalf(self):
        raise ValueError
 
    @staticmethod
    def sympify(a):
        """for "a" int, returns Rational(a), for "a" float returns real, 
        otherwise "a" (=it's a Basic subclass)."""
        import decimal
        from numbers import Rational, Real
        
        if isinstance(a,int) or isinstance(a, long):
            return Rational(a)
        elif isinstance(a,(float, decimal.Decimal)):
            return Real(a)
        else:
            assert isinstance(a,Basic)
            return a
        
    def hash(self):
        if self.mhash: 
            return self.mhash.value
        self.mhash = hashing.mhash()
        self.mhash.addstr(str(type(self)))
        
    def isequal(self,a):
        return self.hash() == (self.sympify(a)).hash()
        
    @staticmethod
    def cmphash(a,b):
        return _sign(a.hash()-b.hash())
        
    def diffn(self,sym,n):
        while n:
            self = self.diff(sym)
            n -= 1
        return self
        
    def series(self,sym,n):
        from numbers import Rational
        from symbol import Symbol
        from functions import log
        w=Symbol("l",dummy=True)
        f = self.subs(log(sym),-w)
        e = f.subs(sym,Rational(0))
        fact = Rational(1)
        for i in range(1,n+1):
            fact *= Rational(i)
            f = f.diff(sym)
            e += f.subs(sym,Rational(0))*(sym**i)/fact
        e=e.subs(w,-log(sym))
        return e
        
    def subs(self,old,new):
        if self.isequal(old):
            return self.sympify(new)
        else:
            return self
            
    def has(self,sub):
        from symbol import Symbol
        n = Symbol("dummy")
        return self.subs(sub,n)!=self
        
    def leadterm(self,x):
        """Returns the leading term c0*x^e0 of the power series 'self' in x
        with the lowest power of x in a form (c0,e0)
        """
        
        from numbers import Rational
        from power import Pow
        from addmul import Add,Mul
        from symbol import Symbol
        def domul(x):
            if len(x) > 1:
                return Mul(x)
            return x[0]
        
        def extract(t,x):
            """Parses "t(x)", which is expected to be in the form c0*x^e0,
            and returns (c0,e0). It raises an exception, if "t(x)" is not
            in this form.
            """
            if not t.has(x):
                return t,Rational(0)
            if isinstance(t,Pow):
                return  Rational(1),  t.exp
            elif isinstance(t,Symbol):
                return  Rational(1),  Rational(1)
            assert isinstance(t,Mul)
            for i,a in enumerate(t.args):
                if a.has(x):
                    if isinstance(a,Pow):
                        return  domul(t.args[:i] + t.args[i+1:]),  a.exp
                    if isinstance(a,Symbol):
                        return  domul(t.args[:i] + t.args[i+1:]),  Rational(1)
                    assert False
            return t,s.Rational(0)
        if not isinstance(self,Add):
            return extract(self,x)
        lowest = [0,(Rational(10)**10)]
        l=Symbol("l",dummy=True)
        from functions import log
        for t in self.args:
            t2 = extract(t.subs(log(x),-l),x)
            if (lowest[1] - t2[1]).evalf()>0:
                lowest=t2
            elif t2[1] == lowest[1]:
                lowest=((lowest[0] + t2[0]),lowest[1])
        return lowest[0].subs(l,-log(x)), lowest[1].subs(l,-log(x))
        
    def ldegree(self,sym):
        """Returns the lowest power of the sym
        """
        return self.leadterm(sym)[1]
        
    def expand(self):
        return self

    def conjugate(self):
        """Returns a  complex conjugate of self. 
        
        Note: this implementeation assumes that all Symbols are real,
        so we just need to change the sign at "i".
        """
        from numbers import I
        return self.subs(I,-I)

    def sqrt(self):
        """Returns square root of self."""
        from numbers import Rational
        return (self**(Rational(1)/2))

    def bounded(self):
        """Is "self" bounded for all possible values of symbols?
        
        Generally not, but sin(x) and cos(x) are.
        """
        return False

    def commutative(self):
        """All subclasses of Basic are commutative by default"""
        return True

    @staticmethod
    def muleval(x,y):
        """See
        http://groups.google.com/group/sympy/browse_thread/thread/aadbef6e2a4ae335

        Try to simplify x*y. You can either return a simplified expression
        or None.
        
        
        """
        return None

    @staticmethod
    def addeval(x,y):
        """
        Try to simplify x+y in this order. You can either return a simplified
        expression or None.
        
        """
        return None

    def isnumber(self):
        """Return True if self is a number. False otherwise. 
        """
        
        try:
            self.evalf()
            # if self has symbols it will raise
            # an exception, which we will catch
            # and return False
            return True
        except ValueError:
            return False

    def print_sympy(self):
        """The canonical sympy representation"""
        return str(type(self))

    def print_pretty(self):
        """The pretty printing"""
        raise NotImplementedError("Pretty printing not implemented for %s"
                %self.__class__.__name__)
        
    def print_tree(self):
        """The canonical tree representation"""
        return str(self)

    def ispoly(self,x):
        from power import Pow
        from numbers import Rational, Number
        from addmul import Add,Mul
        from symbol import Symbol
        #if not isinstance(x, Symbol):
        #    d=Symbol("d",dummy=True)
        #    e=self.subs(x,d)
        #    if e.has(x):
        #        return False
        #    print e,x
        #    return e.ispoly(d)
        if not self.has(x):
            #print 'yoooo'
            return True
        if isinstance(self,Number):
            return True
        if self==x:
            return True
        if isinstance(self,Pow):
            if isinstance(self.exp, Rational) and self.exp.isinteger():
                if int(self.exp)>0 and self.base.ispoly(x):
                    return True
        if isinstance(self,Add):
            a,b = self.getab()
            return a.ispoly(x) and b.ispoly(x)
        if isinstance(self,Mul):
            a,b = self.getab()
            return a.ispoly(x) and b.ispoly(x)
        return False

def _isnumber(x):
    #don't use this function. Use x.isnumber() instead
    from numbers import Number
    from basic import Basic
    from decimal import Decimal
    if isinstance(x, (Number, int, float, long, Decimal)):
        return True
    assert isinstance(x, Basic)
    return x.isnumber()

def _sign(x):
    """Return the sign of x, that is, 
    1 if x is positive, 0 if x == 0 and -1 if x is negative
    """
    if x < 0: return -1
    elif x==0: return 0
    else: return 1
