"""
This module implements generic types for representing predictions for
the control of attractors in Boolean and multivalued networks, with
various visualization methods.

It accounts for instantaneous, temporary, and permanent perturbations, as well
as sequential reprogramming strategies.

Typically, a method computing reprogramming strategies returns an object of
class :py:class:`.ReprogrammingStrategies`, from which can be extracted and
visualized the set of identified strategies.
"""

import pandas as pd
import pydot

from colomoto_jupyter import IN_IPYTHON
if IN_IPYTHON:
    from IPython.display import display

class _SymbolicType(object):
    """
    Abstract class of a symbolic type with list of arguments.

    Implements a generic `repr` method.
    """
    def __init__(self, *args):
        self.args = args
    def repr_args(self):
        return ", ".join(map(repr, self.args))
    def _repr_pretty_(self, p, cycle):
        if cycle:
            p.text("...")
            return
        with p.group(4, "{}(".format(self.__class__.__name__), ")"):
            for i, a in enumerate(self.args):
                if i:
                    p.text(", ")
                p.pretty(a)
    def __repr__(self):
        return "{}({})".format(self.__class__.__name__,
                self.repr_args())

class _Perturbation(_SymbolicType):
    """
    Abstract class for representing a perturbation.
    """
    def __init__(self, partial_state):
        """
        :param dict[str,int] partial_state: effect of the perturbation, which
            assigns states to components
        """
        super().__init__(partial_state)
    def _repr_pretty_(self, p, cycle):
        p.text("{}({})".format(self.__class__.__name__, self.repr_args()))
    def repr_args(self, sep=", "):
        return sep.join(["{}={}".format(k,v) \
                for k,v in sorted(self.args[0].items())])
    def get_edge_label(self, compact=True):
        """
        label to use for the perturbation edge in the graph representation

        :param bool compact: `True` requests a short label
        """
        if compact:
            return "{}({})".format(self.__class__.__name__[0], len(self.args[0]))
        return "{}({})".format(self.__class__.__name__[0], self.repr_args())
    def __hash__(self):
        return hash(repr(self))
    def __eq__(self, p2):
        return repr(self) == repr(p2)

class PermanentPerturbation(_Perturbation):
    """
    A permanent perturbation locks the specified components forever (mutation).
    """
    pass

class TemporaryPerturbation(_Perturbation):
    """
    A temporary perturbation locks the specified components until having reached
    an attractor, or until a :py:class:`.ReleasePerturbation`.
    """
    pass

class ReleasePerturbation(_Perturbation):
    """
    A release perturbation unlocks given components subject to a prior
    :py:class:`.TemporaryPerturbation`.
    """
    pass

class InstantaneousPerturbation(_Perturbation):
    """
    An instantaneous perturbation modifies the states of the components and is
    immediatly released.
    """
    pass

class _Strategy(_SymbolicType):
    iarg_from = None
    def _repr_pretty_(self, p, cycle):
        p.breakable(sep="")
        super()._repr_pretty_(p, cycle)

    def fill_graph(self, g, target, compact):
        start = self.make_start_node()
        if not g.get_node(start.get_name()):
            g.add_node(start)
        p = self.perturbation()
        s = self.next()
        if s:
            target = s.fill_graph(g, target, compact)
        edge = pydot.Edge(start, target, label=p.get_edge_label(compact))
        edge.set_fontsize(10)
        edge.set_labeltooltip(repr(p))
        g.add_edge(edge)
        return start

    def perturbation_sequence(self):
        ps = (self.perturbation(),)
        s = self.next()
        if s:
            ps = ps + s.perturbation_sequence()
        return ps

class FromAny(_Strategy):
    def make_start_node(self):
        n = pydot.Node("any", label="")
        n.set_tooltip(self.__class__.__name__[4:])
        n.set_shape("circle")
        n.set_style("dotted")
        return n
    def perturbation(self):
        return self.args[0]
    def next(self):
        if len(self.args) > 1:
            return self.args[1]

class FromState(_Strategy):
    def make_start_node(self):
        n = pydot.Node(self.args[0])
        n.set_tooltip(self.__class__.__name__[4:])
        return n
    def perturbation(self):
        return self.args[1]
    def next(self):
        if len(self.args) > 2:
            return self.args[2]

class FromCondition(FromState):
    pass

class FromSteadyState(FromState):
    def make_start_node(self):
        n = super().make_start_node()
        n.set_style("filled")
        n.set_shape("box")
        return n

class FromOneInLimitCycle(FromState):
    def make_start_node(self):
        n = super().make_start_node()
        n.set_style("dashed")
        return n


class ReprogrammingStrategies(object):
    def __init__(self):
        self.__d = []
        self.__aliases = {}
        self.__autoaliases = {}

    @property
    def aliases(self):
        return pd.DataFrame(self.__aliases).T

    def autoalias(self, pattern, state):
        h = tuple(sorted(state.items()))
        reg = self.__autoaliases.get(pattern)
        if not reg:
            reg = self.__known_alias[pattern] = {}
        a = reg.get(h)
        if not a:
            a = pattern.format(len(reg))
            reg[h] = a
            self.register_alias(a, state)
        return a

    def register_alias(self, name, state):
        self.__aliases[name] = state

    def add(self, s, **props):
        self.__d.append((s, props))

    def _repr_pretty_(self, p, cycle):
        p.pretty([a[0] for a in self.__d])

    def as_graph(self, compact=False):
        g = pydot.Dot("")
        g.set_rankdir("LR")
        target = pydot.Node("target")
        target.set_shape("Mdiamond")
        target.set_style("filled")
        target.set_fillcolor("palegreen")
        target.set_tooltip("")
        g.add_node(target)
        for a in self.__d:
            a[0].fill_graph(g, target, compact)
        return g

    def as_table(self):
        #TODO: support multi-valued
        l = set()
        for a in self.__d:
            mods = {}
            for p in a[0].perturbation_sequence():
                for n, v in p.args[0].items():
                    assert v == 0 or v == 1, "Only Boolean values are supported"
                    if n not in mods:
                        mods[n] = set()
                    mods[n].add(v)
            l.add(frozenset([(n,frozenset(vs)) for n,vs in mods.items()]))
        def fmt(vs):
            if len(vs) == 1:
                return str(list(vs)[0])
            return '*' #set(vs)
        l = [dict([(n, fmt(vs)) for n, vs in mods]) for mods in sorted(l)]
        df = pd.DataFrame(l).fillna('')
        if not l: # empty
            return df
        df.sort_index(axis=1, inplace=True)
        df.sort_values(list(df.columns), inplace=True)
        df.reset_index(drop=True, inplace=True)
        df = df.style.set_table_styles([
            dict(selector="th",props=[
                ("border-right", "1px solid black"),
                ]),
            {"selector": "td", "props": [
                    ("border-right", "1px solid black"),
                    ("min-width", "2em")]},
            dict(selector="th.col_heading",
                props=[("writing-mode", "vertical-lr"),
                    ("transform", "rotateZ(180deg)"),
                    ("vertical-align", "top"),
                    ("border-bottom", "1px solid black"),
                    ("text-orientation", "mixed")])])
        def colorize(val):
            if val == "0":
                return "color: black; background-color: lime"
            if val == "1":
                return "color: black; background-color: red"
            if val == "*":
                return "color: black; background-color: yellow"
            return ""
        df = df.applymap(colorize)
        return df

    def perturbations(self):
        ps = set()
        for a in self.__d:
            ps.add(a[0].perturbation_sequence())
        return ps

if IN_IPYTHON:
    try:
        ip = get_ipython()
        svg_formatter = ip.display_formatter.formatters["image/svg+xml"]
        svg_formatter.for_type(pydot.Dot, lambda g: g.create_svg().decode())
    except:
        pass

