# This file is the original (unmodified) limits.py from the oldcore
# please don't modify it, it's here for the reference
# see limits.py for more info

"""
Limits
======

Implemented according to the PhD thesis
http://www.cybertester.com/data/gruntz.pdf, which contains very thorough
descriptions of the algorithm including many examples.  We summarize here the
gist of it.


All functions are sorted according to how rapidly varying they are at infinity
using the following rules. Any two functions f and g can be compared using the
properties of L:

L=lim  log|f(x)| / log|g(x)|           (for x -> oo) 

We define >, < ~ according to::
    
    1. f > g .... L=+-oo 
    
        we say that:
        - f is greater than any power of g
        - f is more rapidly varying than g
        - f goes to infinity/zero faster than g
    
    
    2. f < g .... L=0 
    
        we say that:
        - f is lower than any power of g
    
    3. f ~ g .... L!=0,+-oo 
    
        we say that:
        - both f and g are bounded from above and below by suitable integral
          powers of the other


Examples
========
::
    2 < x < exp(x) < exp(x**2) < exp(exp(x))
    2 ~ 3 ~ -5
    x ~ x**2 ~ x**3 ~ 1/x ~ x**m ~ -x
    exp(x) ~ exp(-x) ~ exp(2x) ~ exp(x)**2 ~ exp(x+exp(-x))
    f ~ 1/f

So we can divide all the functions into comparability classes (x and x^2 belong
to one class, exp(x) and exp(-x) belong to some other class). In principle, we
could compare any two functions, but in our algorithm, we don't compare
anything below the class 2~3~-5 (for example log(x) is below this), so we set
2~3~-5 as the lowest comparability class. 

Given the function f, we find the list of most rapidly varying (mrv set)
subexpressions of it. This list belongs to the same comparability class. Let's
say it is {exp(x), exp(2x)}. Using the rule f ~ 1/f we find an element "w"
(either from the list or a new one) from the same comparability class which
goes to zero at infinity. In our example we set w=exp(-x) (but we could also
set w=exp(-2x) or w=exp(-3x) ...). We rewrite the mrv set using w, in our case
{1/w,1/w^2}, and substitute it into f. Then we expand f into a series in w::

    f = c0*w^e0 + c1*w^e1 + ... + O(w^en),        where e0<e1<...<en, c0!=0

but for x->oo, lim f = lim c0*w^e0, because all the other terms go to zero,
because w goes to zero faster than the ci and ei. So::

    for e0>0, lim f = 0
    for e0<0, lim f = +-oo   (the sign depends on the sign of c0)
    for e0=0, lim f = lim c0

We need to recursively compute limits at several places of the algorithm, but
as is shown in the PhD thesis, it always finishes.

Important functions from the implementation:

compare(a,b,x) compares "a" and "b" by computing the limit L.
mrv(e,x) returns the list of most rapidly varying (mrv) subexpressions of "e"
rewrite(e,Omega,x,wsym) rewrites "e" in terms of w
leadterm(f,x) returns the lowest power term in the series of f
mrv_leadterm(e,x) returns the lead term (c0,e0) for e
limitinf(e,x) computes lim e  (for x->oo)
limit(e,z,z0) computes any limit by converting it to the case x->oo

All the functions are really simple and straightforward except rewrite(), which
is the most difficult/complex part of the algorithm. When the algorithm fails,
the bugs are usually in the series expansion (i.e. in SymPy) or in rewrite.

This code is almost exact rewrite of the Maple code inside the Gruntz thesis.

"""

import sympy
from sympy import Basic, Add, Mul, Pow, Function, log, oo, Rational, exp, \
        Real, Order, Symbol
O = Order

def compare(a,b,x):
    """Returns "<" if a<b, "=" for a==b, ">" for a>b"""
    #use the sympy's broken limit as the starting point (bootstrapping) :)
    #c = limitinf(log(a)/log(b), x)
    c = (log(a)/log(b)).inflimit(x)
    if c == 0: 
        return "<"
    elif c in [oo,-oo]: 
        return ">"
    else: 
        return "="

def mrv(e, x):
    "Returns a python set of  most rapidly varying (mrv) subexpressions of 'e'"
    assert isinstance(e, Basic)
    if not e.has(x): 
        return set([])
    elif e == x: 
        return set([x])
    elif isinstance(e, Mul): 
        a, b = e.as_two_terms()
        return mrv_max(mrv(a,x), mrv(b,x), x)
    elif isinstance(e, Add): 
        a, b = e.as_two_terms()
        return mrv_max(mrv(a,x), mrv(b,x), x)
    elif isinstance(e, Pow):
        if e.exp.has(x):
            return mrv(exp(e.exp * log(e.base)), x)
        else:
            return mrv(e.base, x)
    elif isinstance(e, log): 
        return mrv(e[0], x)
    elif isinstance(e, exp): 
        if e[0].inflimit(x) in [oo,-oo]:
            return mrv_max(set([e]), mrv(e[0], x), x)
        else:
            return mrv(e[0], x)
    elif isinstance(e, Function): 
        if len(e) == 1:
            return mrv(e[0], x)
        #only functions of 1 argument currently implemented
        raise NotImplementedError("Functions with more arguments: '%s'" % e)
    raise NotImplementedError("Don't know how to calculate the mrv of '%s'" % e)

def mrv_max(f, g, x):
    """Computes the maximum of two sets of expressions f and g, which 
    are in the same comparability class, i.e. max() compares (two elements of)
    f and g and returns the set, which is in the higher comparability class
    of the union of both, if they have the same order of variation.
    """
    assert isinstance(f, set)
    assert isinstance(g, set)
    if f==set([]): return g
    elif g==set([]): return f
    elif f.intersection(g) != set([]): return f.union(g)
    elif x in f: return g
    elif x in g: return f

    c=compare(list(f)[0], list(g)[0], x)
    if c == ">": return f
    elif c == "<": return g
    else: 
        assert c == "="
        return f.union(g)

def rewrite(e,Omega,x,wsym):
    """e(x) ... the function
    Omega ... the mrv set
    wsym ... the symbol which is going to be used for w

    Returns the rewritten e in terms of w and log(w). See test_rewrite1()
    for examples and correct results.
    """
    assert isinstance(Omega, set)
    assert len(Omega)!=0
    #all items in Omega must be exponentials
    for t in Omega: assert isinstance(t, exp)
    def cmpfunc(a,b):
        #FIXME: this is really, really slow...
        return -cmp(len(mrv(a,x)), len(mrv(b,x)))
    #sort Omega (mrv set) from the most complicated to the simplest ones
    #the complexity of "a" from Omega: the length of the mrv set of "a"
    Omega = list(Omega)
    Omega.sort(cmp=cmpfunc)
    g=Omega[-1] #g is going to be the "w" - the simplest one in the mrv set
    sig = (sign(g[0], x) == 1) 
    if sig: wsym=1/wsym #if g goes to oo, substitute 1/w
    #O2 is a list, which results by rewriting each item in Omega using "w"
    O2=[]
    for f in Omega: 
        c=mrv_leadterm(f[0]/g[0], x)
        #the c is a constant, because both f and g are from Omega:
        assert c[1] == 0
        O2.append(exp((f[0]-c[0]*g[0]).expand())*wsym**c[0])
    #Remember that Omega contains subexpressions of "e". So now we find
    #them in "e" and substitute them for our rewriting, stored in O2
    f=e 
    for a,b in zip(Omega,O2):
        f=f.subs(a,b)

    #tmp.append("Omega=%s; O2=%s; w=%s; wsym=%s\n"%(Omega,O2,g,wsym))

    #finally compute the logarithm of w (logw). 
    logw=g[0]
    if sig: logw=-logw     #log(w)->log(1/w)=-log(w)
    return f, logw

def sign(e, x):
    """Returns a sign of an expression e(x) for x->oo.
    
        e >  0 ...  1
        e == 0 ...  0
        e <  0 ... -1
    """
    if isinstance(e, (Rational, Real)):
        return sympy.sign(e)
    elif not e.has(x):
        f= e.evalf()
        if f > 0:
            return 1
        else:
            return -1
    elif e == x: 
        return 1
    elif isinstance(e, Mul): 
        a,b = e.as_two_terms()
        return sign(a, x) * sign(b, x)
    elif isinstance(e, exp): 
        return 1 
    elif isinstance(e, Pow):
        if sign(e.base, x) == 1: 
            return 1
    elif isinstance(e, log): 
        return sign(e[0] -1, x)
    elif isinstance(e, Add):
        return sign(e.inflimit(x), x)
    raise "cannot determine the sign of %s"%e

def limitinf(e,x):
    """Limit e(x) for x-> oo"""
    if not e.has(x): return e #e is a constant
    c0,e0 = mrv_leadterm(e,x) 
    sig=sign(e0,x)
    if sig==1: return Rational(0) # e0>0: lim f = 0
    elif sig==-1: #e0<0: lim f = +-oo   (the sign depends on the sign of c0)
        #the leading term shouldn't be 0:
        assert sign(c0,x) != 0
        return sign(c0, x) * oo 
    elif sig==0: return limitinf(c0,x) #e0=0: lim f = lim c0

#@decorator(maketree)

def moveup(l, x):
    return [e.subs(x,exp(x)) for e in l]

def movedown(l, x):
    return [e.subs(x,log(x)) for e in l]

def subexp(e,sub):
    """Is "sub" a subexpression of "e"? """
    #we substitute some symbol for the "sub", and if the 
    #expression changes, the substitution was successful, thus the answer
    #is yes.
    return e.subs(sub, Symbol("x", dummy=True)) != e

def mrv_leadterm(e, x, Omega=[]):
    """Returns (c0, e0) for e."""
    if not e.has(x): return (e, 0)
    Omega = [t for t in Omega if subexp(e,t)]
    if Omega == []:
        Omega = mrv(e,x)
    if x in set(Omega):
        #move the whole omega up (exponentiate each term):
        Omega_up = set(moveup(Omega,x))
        e_up = moveup([e],x)[0]
        #calculate the lead term
        mrv_leadterm_up = mrv_leadterm(e_up, x, Omega_up)
        #move the result (c0, e0) down
        return tuple(movedown(mrv_leadterm_up, x))
    wsym = Symbol("w", dummy=True)
    f, logw=rewrite(e, set(Omega), x, wsym)
    series=f.expand().oseries(O(wsym**2, wsym))
    assert series!=0
    assert not isinstance(series,O)
    #print "sss1",series,type(series),f,n
    #series = series.removeO()
    #print "sss2",series,type(series)
    series=series.subs(log(wsym), logw)
    #print "sss3",series,type(series)
    return series.leadterm(wsym)

#@decorator(maketree)



class Limit2(Basic):
    
    mathml_tag = 'limit'

    def __init__(self,e,x,x0):
        Basic.__init__(self)
        self._args = list()
        self._args.append(self.sympify(e))
        self._args.append(self.sympify(x))
        self._args.append(self.sympify(x0))
        

    def __pretty__(self):
         e, x, t = [a.__pretty__() for a in (self.e,self.x,self.x0)]
         a = prettyForm('lim')
         a = prettyForm(*a.below('%s->%s' % (x, t)))
         a = prettyForm(*stringPict.next(a, e))
         return a
     
    def __latex__(self):
         return r"\lim_{%s \to %s}%s" % (self.x.__latex__(), \
                                                 self.x0.__latex__(), 
                                                 self.e.__latex__() )
                 
    @property
    def e(self):
        return self._args[0]
    
    @property
    def x(self):
        return self._args[1]
    
    @property
    def x0(self):
        return self._args[2]

    def doit(self):
        return limit(self.e,self.x,self.x0)
    
    def __mathml__(self):
        if self._mathml:
            return self._mathml
        import xml.dom.minidom
        dom = xml.dom.minidom.Document()
        x = dom.createElement("apply")
        x.appendChild(dom.createElement(self.mathml_tag))
        
        x_1 = dom.createElement('bvar')
        
        x_2 = dom.createElement('lowlimit')
        
        x.appendChild(x_1)
        x.appendChild(x_2)
        x.appendChild( self.e.__mathml__() )
        x.childNodes[1].appendChild( self.x.__mathml__() )
        x.childNodes[2].appendChild( self.x0.__mathml__() )
        self._mathml = x
        
        return self._mathml
            
def limit(e, z, z0, dir="+"):
    """
    Compute the limit of e(z) at the point z0. 

    z0 can be any expression, including oo and -oo.

    For dir="+" (default) it calculates the limit from the right
    (z->z0+) and for dir="-" the limit from the left (z->z0-). For infinite z0
    (oo or -oo), the dir argument doesn't matter.
    """
    if not isinstance(z, Symbol):
        raise NotImplementedError("Second argument must be a Symbol")

    #convert all limits to the limit z->oo
    elif z0 == oo:
        return limitinf(e, z)
    elif z0 == -oo:
        return limitinf(e.subs(z,-z), z)
    else:
        x = Symbol("x", dummy=True)
        if dir == "-":
            e0 = e.subs(z,z0-1/x)
        elif dir == "+":
            e0 = e.subs(z,z0+1/x)
        else:
            raise NotImplementedError("dir must be '+' or '-'")
        return limitinf(e0, x)
