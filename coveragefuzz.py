#!/usr/bin/env python
# Coverage-Guided Fuzzing

from grammarfuzz import expand_tree, init_tree, all_terminals

import random
import sys
import branchfitness

cgi_grammar = {
    "$START": ["$STRING"],
    "$STRING": ["$CHARACTER", "$STRING$CHARACTER"],
    "$CHARACTER": ["$REGULAR_CHARACTER", "$PLUS", "$PERCENT"],
    "$REGULAR_CHARACTER": ["a", "b", "c", ".", ":", "!"], # actually more
    "$PLUS": ["+"],
    "$PERCENT": ["%$HEX_DIGIT$HEX_DIGIT"],
    "$HEX_DIGIT": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
                   "a", "b", "c", "d", "e", "f",
                   "?" # Invalid value
                  ]
}


### Program to test
import example

### Our production framework

# Return the number of nodes
def number_of_nodes(tree):
    (symbol, children) = tree
    n = 1
    for c in children:
        n += number_of_nodes(c)
    return n

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


### Computing coverage

# Where we store the coverage
coverage = {}

# Now, some dynamic analysis
def traceit(frame, event, arg):
    global coverage
    if event == "line":
        lineno = frame.f_lineno
        # print("Line", lineno, frame.f_locals)
        coverage[lineno] = True
    return traceit

ffn = branchfitness.Fitness('example.py')
cfg = ffn.cfg

def branch_fitness(tree):
    import example
    term = all_terminals(tree)
    #path = [33, 34, 35, 47]
    path = [34, 36, 46, 47]
    ffn.capture_coverage(lambda: example.cgi_decode(term))

    arcs = [ (i,j) for f,i,j,src,l in ffn.cdata_arcs]
    not_covered = set()
    covered = set()
    for l in cfg:
        for p in cfg[l]['parents']:
            if (p, l) not in arcs:
                not_covered.add((p, l))
            else:
                covered.add((p, l))
    print(not_covered) 
    val = ffn.compute_fitness(path)
    return val

# Define the fitness of an individual term - by actually testing it
def coverage_fitness(tree):
    term = all_terminals(tree)

    # Set up the tracer
    global coverage
    coverage = {}
    trace = sys.gettrace()
    sys.settrace(traceit)

    # Run the function under test
    result = example.cgi_decode(term)

    # Turn off the tracer
    sys.settrace(trace)

    # Simple approach:
    # The term with the highest coverage gets the highest fitness
    return len(coverage.keys())



# Number of elements in our population
POPULATION_SIZE = 20

# How many of these to select for the next generation
SELECTION_SIZE = 10

# How many evolution cycles
EVOLUTION_CYCLES = 10

def produce(grammar, max_symbols = 10):
    # Create an initial derivation tree
    tree = init_tree()
    # print(tree)

    # Expand all nonterminals
    tree = expand_tree(tree, grammar, max_symbols)
    # print(tree)

    # Return the tree
    return tree

# Create a random population
def population(grammar):
    pop = []
    while len(pop) < POPULATION_SIZE:
        # Create a random individual
        tree = produce(grammar)

        # Determine its fitness (by running the test, actually)
        fitness = branch_fitness(tree)

        # Add it to the population
        if (tree, fitness) not in pop:
            pop.append((tree, fitness))

    return pop


def by_fitness(individual):
    (tree, fitness) = individual
    return fitness

# Evolve the set
def evolve(pop, grammar):
    # Sort population by fitness (highest first)
    best_pop = sorted(pop, key=by_fitness, reverse=True)


    # Select the fittest individuals
    best_pop = best_pop[:SELECTION_SIZE]

    # Breed
    offspring = []
    while len(offspring) + len(best_pop) < POPULATION_SIZE:
        (parent, parent_fitness) = random.choice(best_pop)
        child = mutate(parent, grammar)
        child_fitness = branch_fitness(child)

        if child_fitness >= parent_fitness:
            offspring.append((child, child_fitness))

    next_pop = best_pop + offspring

    # Keep it sorted
    next_pop = sorted(next_pop, key=by_fitness, reverse=True)

    return next_pop

# TODO: Not only check total lines covered, but _new_ lines covered

def print_population(pop):
    for (tree, fitness) in pop:
        print(all_terminals(tree) + " " + repr(fitness))

if __name__ == "__main__":
    grammar = cgi_grammar

    tree = produce(grammar)
    print("Tree: " + all_terminals(tree))
    print("Fitness: " + repr(branch_fitness(tree)))

    # Create a population
    print("Population:")
    pop = population(grammar)
    pop = sorted(pop, key=by_fitness, reverse=True)
    print_population(pop)

    for i in range(EVOLUTION_CYCLES):
        # Evolve the population
        print("Evolved:")
        next_pop = evolve(pop, grammar)
        print_population(next_pop)
        pop = next_pop


