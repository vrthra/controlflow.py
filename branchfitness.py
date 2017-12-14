#!/usr/bin/env python3

import pycfg
import math
import dexpr
import branchcov
from importlib.machinery import SourceFileLoader

class Fitness:
    def __init__(self, cfg, dom, postdom):
        self.cfg = cfg
        self.dom = dom
        self.postdom = postdom

    def init_cfg(self, filename):
        cfg, founder, last_node = pycfg.get_cfg(filename)
        self.cfg = dict(cfg)
        self.dom = pycfg.compute_dominator(self.cfg, start=founder, key='parents')
        self.postdom = pycfg.compute_dominator(self.cfg, start=last_node, key='children')

    def capture_coverage(self, fn, fsrc):
        self.cdata_arcs, self.source_code, self.branch_cov = branchcov.capture_coverage(fn, fsrc)


    def compute_fitness(self, path):
        def normalized(x): return x / (x + 1.0)
        self.path = path
        al = self.approach_level()
        bd = self.branch_distance()
        if bd == math.inf: return al
        return (al + normalized(bd))

    def print_dom(dom):
        for k in dom: print(k, dom[k])

    def approach_level(self):
        return self._approach_level(reversed(self.path))

    def target(self):
        return self.path[-1]

    def branch_distance(self):
        parents = self.cfg[self.target()]['parents']
        if parents:
            v = min(self._branch_distance(p, self.target(), set()) for p in parents)
            if v == math.inf:
                return 0
            else:
                return v
        else:
            return 0

    def compute_predicate_cost(self, parent, target):
        f,src,l = self.source_code[parent]
        ei = dexpr.DistInterpreter(l)
        v = ei.eval(src)
        return v

    def _branch_distance(self, parent, target, seen):
        seen = seen | {(parent, target)}
        parent_dict = self.cfg[parent]

        gparents = [gp for gp in parent_dict['parents'] if (gp, parent) not in seen] # TODO: filter out call sites

        # was the parent executed?
        if parent in self.branch_cov:
            # the parent was executed. Hence, if the target is executed
            # then there is no cost.
            if target in self.branch_cov[parent]:
                return 0

            # the target was not executed. Hence the flow diverged here.
            # do not attempt to compute predicate cost unless it is a conditional
            if len(self.cfg[parent]['children']) > 1 and 'calls' not in self.cfg[parent]:
                return self.compute_predicate_cost(parent, target)
            else:
                # not a conditional.
                return min(self._branch_distance(gp, parent, seen) for gp in gparents)

        else: # The parent was not executed. So go up the chain

            # if we can not go further up, we dont know how close we came
            if not gparents:
                return math.inf

            # go up the minimum chain.
            return min(self._branch_distance(gp, parent, seen) for gp in gparents)

    def a_control_dependent_on_b(self, a, b):
        # A has at least 2 successors in CFG
        if len(self.cfg[b]['children']) < 2: return False

        b_successors = self.cfg[b]['children']
        # B dominates A
        v1 = b in self.dom[a]
        # B is not post dominated by A
        v2 = a not in self.postdom[b]
        # there exist a successor for B that is post dominated by A
        v3 = any(a in self.postdom[s] for s in b_successors)
        return v1 and v2 and v3

    def _approach_level(self, path):
        if not path: return 0
        hd, *tl = path
        if not tl: return 0
        cost = 1 if self.a_control_dependent_on_b(hd, tl[0]) else 0
        return cost + self._approach_level(tl)

if __name__ == '__main__':
    import sys
    path = [int(i) for i in sys.argv[4:]]
    ffn = Fitness(*pycfg.compute_flow(sys.argv[1]))
    my_module = SourceFileLoader('', sys.argv[1]).load_module()
    fn = getattr(my_module, sys.argv[2])
    arg = sys.argv[3]
    ffn.capture_coverage(lambda: fn(arg), sys.argv[1])
    fitness = ffn.compute_fitness(path)
    print('Approach Level %d' % ffn.approach_level())
    print('Branch distance(target:%d): %d' % (ffn.target(), ffn.branch_distance()))
    print('Fitness: %f' % fitness)
