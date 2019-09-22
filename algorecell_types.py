

__version__ = "0.1"

import pandas as pd
import pydot

from colomoto_jupyter import IN_IPYTHON
if IN_IPYTHON:
    from IPython.display import display

class _SymbolicType(object):
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
    def __init__(self, partial_state):
        super().__init__(partial_state)
    def _repr_pretty_(self, p, cycle):
        p.text("{}({})".format(self.__class__.__name__, self.repr_args()))
    def repr_args(self, sep=", "):
        return sep.join(["{}={}".format(k,v) \
                for k,v in sorted(self.args[0].items())])
    def get_edge_label(self, compact=True):
        if compact:
            return "{}({})".format(self.__class__.__name__[0], len(self.args[0]))
        return "{}({})".format(self.__class__.__name__[0], self.repr_args())
    def __hash__(self):
        return hash(repr(self))
    def __eq__(self, p2):
        return repr(self) == repr(p2)

class PermanentPerturbation(_Perturbation):
    pass

class TemporaryPerturbation(_Perturbation):
    pass

class ReleasePerturbation(_Perturbation):
    pass

class InstantaneousPerturbation(_Perturbation):
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

    @property
    def aliases(self):
        return pd.DataFrame(self.__aliases).T

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

