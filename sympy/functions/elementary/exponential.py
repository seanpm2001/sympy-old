
from sympy.core.basic import Basic, S, cache_it, cache_it_immutable
from sympy.core.function import DefinedFunction, Apply, Lambda

class Exp(DefinedFunction):

    nofargs = 1

    def fdiff(self, argindex=1):
        if argindex == 1:
            return self
        else:
            raise ArgumentIndexError(self, argindex)

    def inverse(self, argindex=1):
        return S.Log

    def _eval_apply(self, arg):
        arg = Basic.sympify(arg)

        if isinstance(arg, Basic.Number):
            if isinstance(arg, Basic.NaN):
                return S.NaN
            elif isinstance(arg, Basic.Zero):
                return S.One
            elif isinstance(arg, Basic.One):
                return S.Exp1
            elif isinstance(arg, Basic.Infinity):
                return S.Infinity
            elif isinstance(arg, Basic.NegativeInfinity):
                return S.Zero
        elif isinstance(arg, Basic.ApplyLog):
            return arg.args[0]
        elif isinstance(arg, Basic.Mul):
            coeff = arg.as_coefficient(S.Pi*S.ImaginaryUnit)

            if coeff is not None:
                if isinstance(2*coeff, Basic.Integer):
                    cst_table = {
                        0 : S.One,
                        1 : S.ImaginaryUnit,
                        2 : S.NegativeOne,
                        3 : -S.ImaginaryUnit,
                    }

                    return cst_table[int(2*coeff) % 4]

        if isinstance(arg, Basic.Add):
            args = arg[:]
        else:
            args = [arg]

        included, excluded = [], []

        for arg in args:
            coeff, terms = arg.as_coeff_terms()

            if isinstance(coeff, Basic.Infinity):
                excluded.append(coeff**Basic.Mul(*terms))
            else:
                coeffs, log_term = [coeff], None

                for term in terms:
                    if isinstance(term, Basic.ApplyLog):
                        if log_term is None:
                            log_term = term.args[0]
                        else:
                            log_term = None
                            break
                    elif term.is_comparable:
                        coeffs.append(term)
                    else:
                        break

                if log_term is not None:
                    excluded.append(log_term**Basic.Mul(*coeffs))
                else:
                    included.append(arg)

        if excluded:
            return Basic.Mul(*(excluded+[self(Basic.Add(*included))]))

    def _eval_apply_evalf(self, arg):
        arg = arg.evalf()

        if isinstance(arg, Basic.Number):
            return arg.exp()

    @cache_it_immutable
    def taylor_term(self, n, x, *previous_terms):
        if n<0: return S.Zero
        if n==0: return S.One
        x = Basic.sympify(x)
        if previous_terms:
            p = previous_terms[-1]
            if p is not None:
                return p * x / n
        return x**n/Basic.Factorial()(n)

class ApplyExp(Apply):

    def _eval_expand_complex(self, *args):
        re, im = self.args[0].as_real_imag()
        exp, cos, sin = S.Exp(re), S.Cos(im), S.Sin(im)
        return exp * cos + S.ImaginaryUnit * exp * sin

    #def precedence(self):
    #    b, e = self.as_base_exp()
    #    if e.is_negative: return 50 # same as default Mul
    #    return 70

    #def tostr(self, level=0):
    #    p = self.precedence
    #    b, e = self.as_base_exp()
    #    if e.is_negative:
    #        r = '1/%s(%s)' % (self.func, -self.args[0])
    #    else:
    #        r = '%s(%s)' % (self.func, self.args[0])
    #    if p <= level:
    #        return '(%s)' % (r)
    #    return r

    def _eval_conjugate(self):
        return self.func(self.args[0].conjugate())

    def as_base_exp(self):
        #return Basic.Exp1(), self.args[0]
        coeff, terms = self.args[0].as_coeff_terms()
        return self.func(Basic.Mul(*terms)), coeff

    def as_coeff_terms(self, x=None):
        arg = self.args[0]
        if x is not None:
            c,f = arg.as_coeff_factors(x)
            return self.func(c), [self.func(a) for a in f]
        if isinstance(arg, Basic.Add):
            return S.One, [self.func(a) for a in arg]
        return S.One,[self]

    def _eval_subs(self, old, new):
        if self==old: return new
        arg = self.args[0]
        o = old
        if isinstance(old, Basic.Pow): # handle (exp(3*log(x))).subs(x**2, z) -> z**(3/2)
            old = S.Exp(old.exp * S.Log(old.base))
        if isinstance(old, ApplyExp):
            b,e = self.as_base_exp()
            bo,eo = old.as_base_exp()
            if b==bo:
                return new ** (e/eo) # exp(2/3*x*3).subs(exp(3*x),y) -> y**(2/3)
            if isinstance(arg, Basic.Add): # exp(2*x+a).subs(exp(3*x),y) -> y**(2/3) * exp(a)
                # exp(exp(x) + exp(x**2)).subs(exp(exp(x)), w) -> w * exp(exp(x**2))
                oarg = old.args[0]
                new_l = []
                old_al = []
                coeff2,terms2 = oarg.as_coeff_terms()
                for a in arg:
                    a = a.subs(old, new)
                    coeff1,terms1 = a.as_coeff_terms()
                    if terms1==terms2:
                        new_l.append(new**(coeff1/coeff2))
                    else:
                        old_al.append(a.subs(old, new))
                if new_l:
                    new_l.append(self.func(Basic.Add(*old_al)))
                    r = Basic.Mul(*new_l)
                    return r
        old = o
        return Apply._eval_subs(self, old, new)

    def _eval_is_real(self):
        return self.args[0].is_real
    def _eval_is_positive(self):
        if self.args[0].is_real:
            return True
    def _eval_is_bounded(self):
        arg = self.args[0]
        if arg.is_unbounded:
            if arg.is_negative: return True
            if arg.is_positive: return False
        if arg.is_bounded:
            return True
        if arg.is_real:
            return False
    def _eval_is_zero(self):
        return isinstance(self.args[0], Basic.NegativeInfinity)

    def _eval_power(b, e):
        return b.func(b.args[0] * e)

    def _eval_oseries(self, order):
        arg = self.args[0]
        x = order.symbols[0]
        if not Basic.Order(1,x).contains(arg): # singularity
            arg0 = arg.as_leading_term(x)
            d = (arg-arg0).limit(x, S.Zero)
            if not isinstance(d, Basic.Zero):
                return S.Exp(arg)
        else:
            arg0 = arg.limit(x, S.Zero)
        o = order * S.Exp(-arg0)
        return self._compute_oseries(arg-arg0, o, S.Exp.taylor_term, S.Exp) * S.Exp(arg0)

    def _eval_as_leading_term(self, x):
        arg = self.args[0]
        if isinstance(arg, Basic.Add):
            return Basic.Mul(*[S.Exp(f).as_leading_term(x) for f in arg])
        arg = self.args[0].as_leading_term(x)
        if Basic.Order(1,x).contains(arg):
            return S.One
        return S.Exp(arg)

    def _eval_expand_basic(self, *args):
        arg = self.args[0].expand()
        if isinstance(arg, Basic.Add):
            expr = 1
            for x in arg:
                expr *= self.func(x).expand()
            return expr
        return self.func(arg)

class Log(DefinedFunction):

    nofargs = (1,2)
    is_comparable = True

    def fdiff(self, argindex=1):
        if argindex == 1:
            s = Basic.Symbol('x', dummy=True)
            return Lambda(s**(-1), s)
        else:
            raise ArgumentIndexError(self, argindex)

    def inverse(self, argindex=1):
        return S.Exp

    def _eval_apply(self, arg, base=None):
        if base is not None:
            base = Basic.sympify(base)

            if not isinstance(base, Basic.Exp1):
                return self(arg)/self(base)

        arg = Basic.sympify(arg)

        if isinstance(arg, Basic.Number):
            if isinstance(arg, Basic.Zero):
                return S.NegativeInfinity
            elif isinstance(arg, Basic.One):
                return S.Zero
            elif isinstance(arg, Basic.Infinity):
                return S.Infinity
            elif isinstance(arg, Basic.NegativeInfinity):
                return S.Infinity
            elif isinstance(arg, Basic.NaN):
                return S.NaN
            elif arg.is_negative:
                return S.Pi * S.ImaginaryUnit + self(-arg)
        elif isinstance(arg, Basic.Exp1):
            return S.One
        elif isinstance(arg, ApplyExp) and arg.args[0].is_real:
            return arg.args[0]
        elif isinstance(arg, Basic.Pow):
            if isinstance(arg.exp, Basic.Number) or \
               isinstance(arg.exp, Basic.NumberSymbol):
                return arg.exp * self(arg.base)
        elif isinstance(arg, Basic.Mul) and arg.is_real:
            return Basic.Add(*[self(a) for a in arg])
        elif not isinstance(arg, Basic.Add):
            coeff = arg.as_coefficient(S.ImaginaryUnit)

            if coeff is not None:
                if isinstance(coeff, Basic.Infinity):
                    return S.Infinity
                elif isinstance(coeff, Basic.NegativeInfinity):
                    return S.Infinity
                elif isinstance(coeff, Basic.Rational):
                    if coeff.is_nonnegative:
                        return S.Pi * S.ImaginaryUnit * S.Half + self(coeff)
                    else:
                        return -S.Pi * S.ImaginaryUnit * S.Half + self(-coeff)

    def as_base_exp(self):
        return S.Exp, S.NegativeOne

    def _eval_apply_evalf(self, arg):
        arg = arg.evalf()

        if isinstance(arg, Basic.Number):
            return arg.log()

    def _calc_apply_positive(self, x):
        if x.is_positive and x.is_unbounded: return True

    def _calc_apply_unbounded(self, x):
        return x.is_unbounded

    @cache_it_immutable
    def taylor_term(self, n, x, *previous_terms): # of log(1+x)
        if n<0: return S.Zero
        x = Basic.sympify(x)
        if n==0: return x
        if previous_terms:
            p = previous_terms[-1]
            if p is not None:
                return (-n) * p * x / (n+1)
        return (1-2*(n%2)) * x**(n+1)/(n+1)

class ApplyLog(Apply):

    def _eval_expand_complex(self, *args):
        re, im = self.args[0].as_real_imag()
        return S.Log(S.Sqrt(re) + S.Sqrt(im)) + \
               S.ImaginaryUnit * S.Arg(self.args[0])

    def _eval_is_real(self):
        return self.args[0].is_positive

    def _eval_is_bounded(self):
        arg = self.args[0]
        if arg.is_infinitesimal:
            return False
        return arg.is_bounded

    def _eval_is_positive(self):
        arg = self.args[0]
        if arg.is_positive:
            if arg.is_unbounded: return True
            if arg.is_infinitesimal: return False
            if isinstance(arg, Basic.Number):
                return arg>1

    def _eval_is_zero(self):
        # XXX This is not quite useless. Try evaluating log(0.5).is_negative
        #     without it. There's probably a nicer way though.
        return isinstance(self.args[0], Basic.One)

    def as_numer_denom(self):
        n, d = self.args[0].as_numer_denom()
        if isinstance(d, Basic.One):
            return self.func(n), d
        return (self.func(n) - self.func(d)).as_numer_denom()

    # similar code must be added to other functions with have singularites
    # in their domains eg. cot(), tan() ...
    def _eval_oseries(self, order):
        arg = self.args[0]
        x = order.symbols[0]
        ln = S.Log
        use_lt = not Basic.Order(1,x).contains(arg)
        if not use_lt:
            arg0 = arg.limit(x, 0)
            use_lt = isinstance(arg0, Basic.Zero)
        if use_lt: # singularity
            # arg = (arg / lt) * lt
            lt = arg.as_leading_term(x)
            a = (arg/lt).expand()
            return ln(lt) + ln(a).oseries(order)
        # arg -> arg0 + (arg - arg0) -> arg0 * (1 + (arg/arg0 - 1))
        z = (arg/arg0 - 1)
        return self._compute_oseries(z, order, ln.taylor_term, lambda z: ln(1+z)) + ln(arg0)

    def _eval_as_leading_term(self, x):
        arg = self.args[0].as_leading_term(x)
        if isinstance(arg, Basic.One):
            return (self.args[0] - 1).as_leading_term(x)
        return self.func(arg)

    def _eval_expand_basic(self, *args):
        arg = self.args[0]
        if isinstance(arg, Basic.Mul) and arg.is_real:
            expr = 0
            for x in arg:
                expr += self.func(x).expand()
            return expr
        elif isinstance(arg, Basic.Pow):
            if isinstance(arg.exp, Basic.Number) or \
               isinstance(arg.exp, Basic.NumberSymbol):
                return arg.exp * self.func(arg.base).expand()
        return self

# MrvLog is used by limit.py
class MrvLog(Log):
    pass

class ApplyMrvLog(ApplyLog):

    def subs(self, old, new):
        old = Basic.sympify(old)
        if old==self.func:
            arg = self.args[0]
            new = Basic.sympify(new)
            return new(arg.subs(old, new))
        return self
#

Basic.singleton['exp'] = Exp
Basic.singleton['log'] = Log
Basic.singleton['ln'] = Log
