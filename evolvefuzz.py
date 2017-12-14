#!/usr/bin/env python
# Coverage-Guided Fuzzing

from grammarfuzz import expand_tree, init_tree, all_terminals

import random
import sys
import pycfg
import branchfitness
import math

cgi_grammar = {
    "$START": ["$STRING"],
    "$STRING": ["$CHARACTER", "$STRING$CHARACTER"],
    "$CHARACTER": ["$REGULAR_CHARACTER", "$PLUS", "$PERCENT"],
    "$REGULAR_CHARACTER": ["a", "b", "c", ".", ":", "!"], # actually more
    "$PLUS": ["+"],
    "$PERCENT": ["%$HEX_DIGIT$HEX_DIGIT"],
    "$HEX_DIGIT": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
                   "a", "b", "c", "d", "e", "f",
                   "?", # Invalid value
                  ]
}

### Our production framework

def all_children_are_terminals(tree):
    def _all_children_are_terminals(tree):
        (symbol, children) = tree
        for c in children:
            (_, grandchildren) = c
            if len(grandchildren) > 0:
                return False
        return True
    ret = _all_children_are_terminals(tree)
    # print("All children of " + repr(tree) + " are terminals: " + repr(ret))
    return ret

# The likelihood of an individual node to be replaced
MUTATION_RATIO = 0.1

# Apply a random mutation somewhere in the tree
def mutate(tree, grammar, max_symbols = 10):
    # print("Mutating " + all_terminals(tree) + "...")
    (symbol, children) = tree

    mutate_entire_subtree = (all_children_are_terminals(tree) or
                             random.random() < MUTATION_RATIO)

    if mutate_entire_subtree:
        new_children = None
    else:
        while True:
            child_to_be_mutated = int(random.random() * len(children))
            (_, grandchildren) = children[child_to_be_mutated]
            if len(grandchildren) != 0:
                break

        replacement_child = mutate(children[child_to_be_mutated],
                                   grammar, max_symbols)
        new_children = (children[:child_to_be_mutated] +
                        [replacement_child] +
                        children[child_to_be_mutated + 1:])

    new_tree = (symbol, new_children)
    # print("New tree: " + repr(new_tree))
    if new_children is None:
        new_tree = expand_tree(new_tree, grammar, max_symbols)

    # print("Mutating " + all_terminals(tree) + " to " + all_terminals(new_tree))
    return new_tree


### Computing the CFG

def find_path(cfg, cov_arcs, parent, seen):
    if parent == 0:
        return (1, [])
    ks = []
    for p in sorted(cfg[parent]['parents']):
        if p == parent: continue
        if p in seen: continue
        k = find_path(cfg, cov_arcs, p, seen | {parent})
        ks.append(k)
    val = (math.inf, [])
    if ks:
        val = min(ks)
    return (val[0]+1, val[1] + [parent])

cfg, dom, postdom = pycfg.compute_flow('example.py')
# Define the fitness of an individual term - by actually testing it
def branch_fitness(tree):
    import example
    term = all_terminals(tree)
    ffn = branchfitness.Fitness(cfg, dom, postdom)
    ffn.capture_coverage(lambda: example.cgi_decode(term), 'example.py')
    cov_arcs = {(i,j) for f,i,j,src,l in ffn.cdata_arcs}
    not_covered = set()
    covered = set()
    # now identify how bad we were
    for l in ffn.cfg:
        for p in ffn.cfg[l]['parents']:
            if (p, l) not in cov_arcs:
                not_covered.add((p, l))
            else:
                covered.add((p, l))

    s = 0
    seen = set()
    for p,l in not_covered:
        (n, path) = find_path(cfg, cov_arcs, p, seen | {p})
        val = ffn.compute_fitness(path + [l])
        s += val
    #print()
    return s


# Number of elements in our population
POPULATION_SIZE = 40

# How many of these to select for the next generation
SELECTION_SIZE = 20

# How many evolution cycles
EVOLUTION_CYCLES = 10

def produce(grammar, max_symbols = 10):
    return expand_tree(init_tree(), grammar, max_symbols)

# Create a random population
def population(grammar):
    pop = []
    while len(pop) < POPULATION_SIZE:
        tree = produce(grammar)
        if tree  not in pop: pop.append(tree)
    return [(tree, branch_fitness(tree)) for tree in pop]


def by_fitness(individual):
    """Sort by fitness"""
    (tree, fitness) = individual
    return fitness

# Evolve the set
def evolve(pop, grammar):
    # Sort population by fitness (lowest first)
    # and select the fittest individuals
    best_pop = sorted(pop, key=by_fitness)[:SELECTION_SIZE]

    # Breed
    offspring = []
    while len(offspring) + len(best_pop) < POPULATION_SIZE:
        (parent, parent_fitness) = random.choice(best_pop)
        child = mutate(parent, grammar)
        child_fitness = branch_fitness(child)

        if child_fitness >= parent_fitness:
            offspring.append((child, child_fitness))

    next_pop = best_pop + offspring
    return next_pop

# TODO: Not only check total lines covered, but _new_ lines covered

def print_population(pop):
    pop = sorted(pop, key=by_fitness)
    for (tree, fitness) in pop:
        print("%s\t%s" % (repr(fitness), all_terminals(tree)))
    return pop[0]

if __name__ == "__main__":
    grammar = cgi_grammar

    tree = produce(grammar)
    print("Tree: " + all_terminals(tree))
    print("Fitness: " + repr(branch_fitness(tree)))

    best = []
    for i in range(1,10):
        # Create a population
        print("Population:")
        pop = population(grammar)
        print_population(pop)
        p = pop
        for i in range(EVOLUTION_CYCLES):
            # Evolve the population
            print("Evolved:")
            pop = evolve(pop, grammar)
            p = print_population(pop)
            print()
        best.append(p)
    print_population(best)

