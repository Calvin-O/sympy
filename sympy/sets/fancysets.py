from sympy import (Dummy, S, symbols, Lambda, pi, Basic, sympify, ask, Q, Min,
        Max)
from sympy.functions.elementary.integers import floor, ceiling
from sympy.functions.elementary.complexes import sign
from sympy.core.compatibility import iterable
from sympy.core.sets import Set, Interval, FiniteSet, Intersection
from sympy.core.singleton import Singleton, S
from sympy.solvers import solve
oo = S.Infinity

class Naturals(Set):
    """
    Represents the Natural Numbers. The Naturals are available as a singleton
    as S.Naturals

    Examples
    ========

        >>> from sympy import S, Interval
        >>> 5 in S.Naturals
        True
        >>> iterable = iter(S.Naturals)
        >>> print iterable.next()
        1
        >>> print iterable.next()
        2
        >>> print iterable.next()
        3
        >>> S.Naturals.intersect(Interval(0, 10))
        {1, 2, 3, 4, 5, 6, 7, 8, 9, 10}
    """

    __metaclass__ = Singleton
    is_iterable = True

    def _intersect(self, other):
        if other.is_Interval:
            return Intersection(S.Integers, other, Interval(1, oo))
        return None

    def _contains(self, other):
        if ask(Q.positive(other)) and ask(Q.integer(other)):
            return True
        return False

    def __iter__(self):
        i = S(1)
        while True:
            yield i
            i = i + 1

    @property
    def _inf(self):
        return S.One

    @property
    def _sup(self):
        return oo

class Integers(Set):
    """
    Represents the Integers. The Integers are available as a singleton
    as S.Integers

    Examples
    ========

        >>> from sympy import S, Interval
        >>> 5 in S.Naturals
        True
        >>> iterable = iter(S.Integers)
        >>> print iterable.next()
        0
        >>> print iterable.next()
        1
        >>> print iterable.next()
        -1
        >>> print iterable.next()
        2

        >>> S.Integers.intersect(Interval(-4, 4))
        {-4, -3, -2, -1, 0, 1, 2, 3, 4}
    """

    __metaclass__ = Singleton
    is_iterable = True

    def _intersect(self, other):
        if other.is_Interval:
            s = FiniteSet(range(ceiling(other.left), floor(other.right) + 1))
            return s.intersect(other) # take out endpoints if open interval
        return None

    def _contains(self, other):
        if ask(Q.integer(other)):
            return True
        return False

    def __iter__(self):
        yield S.Zero
        i = S(1)
        while True:
            yield i
            yield -i
            i = i + 1

    @property
    def _inf(self):
        return -oo

    @property
    def _sup(self):
        return oo

class TransformationSet(Set):
    """
    A set that is a transformation of another through some algebraic expression

    Examples
    --------
    >>> from sympy import Symbol, S, TransformationSet, FiniteSet, Lambda

    >>> x = Symbol('x')
    >>> N = S.Naturals
    >>> squares = TransformationSet(Lambda(x, x**2), N) # {x**2 for x in N}
    >>> 4 in squares
    True
    >>> 5 in squares
    False

    >>> FiniteSet(0, 1, 2, 3, 4, 5, 6, 7, 9, 10).intersect(squares)
    {1, 4, 9}

    >>> square_iterable = iter(squares)
    >>> for i in range(4):
    ...     square_iterable.next()
    1
    4
    9
    16
    """
    def __new__(cls, lamda, base_set):
        return Basic.__new__(cls, lamda, base_set)

    lamda    = property(lambda self: self.args[0])
    base_set = property(lambda self: self.args[1])

    def __iter__(self):
        already_seen = set()
        for i in self.base_set:
            val = self.lamda(i)
            if val in already_seen:
                continue
            else:
                already_seen.add(val)
                yield val

    def _is_multivariate(self):
        return len(self.lamda.variables) > 1

    def _contains(self, other):
        L = self.lamda
        if self._is_multivariate():
            solns = solve([expr - val for val, expr in zip(other, L.expr)],
                    L.variables)
        else:
            solns = solve(L.expr - other, L.variables[0])

        for soln in solns:
            try:
                if soln in self.base_set:           return True
            except TypeError:
                if soln.evalf() in self.base_set:   return True
        return False

    @property
    def is_iterable(self):
        return self.base_set.is_iterable

class Range(Set):
    """
    Represents a range of integers.

    Examples
    ========

        >>> from sympy import Range
        >>> Range(5) # 0 to 5
        {0, 1, 2, 3, 4}
        >>> Range(10, 15) # 10 to 15
        {10, 11, 12, 13, 14}
        >>> Range(10, 20, 2) # 10 to 20 in steps of 2
        {10, 12, 14, 16, 18}
        >>> Range(20, 10, -2)
        {20, 18, 16, 14, 12} # 20 to 10 backward in steps of 2

    """

    is_iterable = True

    def __new__(cls, *args):
        s = slice(*args)
        start = s.start or 0
        stop  = s.stop
        step  = s.step  or 1

        start, stop, step = map(sympify, (start, stop, step))
        if not all(ask(Q.integer(x)) for x in (start, stop, step)):
            raise ValueError("Inputs to Range must be Integer Valued\n"+
                    "Use TransformationSets of Ranges for other cases")

        s = Basic.__new__(cls, start, stop, step)

        if len(s) == 0:
            return S.EmptySet

        return s

    start = property(lambda self : self.args[0])
    stop  = property(lambda self : self.args[1])
    step  = property(lambda self : self.args[2])

    def _intersect(self, other):
        if other.is_Interval:
            osup = other.sup
            oinf = other.inf
            # if other is [0, 10) we can only go up to 9
            if osup.is_integer and other.right_open:
                osup -= 1
            if oinf.is_integer and other.left_open:
                oinf += 1

            # Take the most restrictive of the bounds set by the two sets
            # round inwards
            inf = ceiling(Max(self.inf, oinf))
            sup = floor(Min(self.sup, osup))
            # walk forward until we reach a step point
            while(inf not in self):
                inf += 1

            return Range(inf, sup, self.step)

        if other == S.Naturals:
            return self._intersect(Interval(1, oo))

        if other == S.Integers:
            return self

        return None

    def _contains(self, other):
        return (other >= self.inf and other <= self.sup and
                ask(Q.integer((self.start - other)/self.step)))

    def __iter__(self):
        i = self.start
        s = sign(self.step)
        while(s*i < s*self.stop):
            yield i
            i = i + self.step

    def __len__(self):
        return ceiling((self.stop - self.start)/self.step)

    def _ith_element(self, i):
        return self.start + i * self.step

    @property
    def _last_element(self):
        return self._ith_element(len(self) - 1)

    @property
    def _inf(self):
        return Min(self.start, self._last_element)

    @property
    def _sup(self):
        return Max(self.start, self._last_element)