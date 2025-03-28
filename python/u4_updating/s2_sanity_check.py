from collections import defaultdict

from python.common.common import open_dict_csv
from nltk.corpus import wordnet as wn

assert wn.get_version() == '3.0'
edges = open_dict_csv('data/working_files/chainnet_edges.tsv')
virtuals = open_dict_csv('data/working_files/chainnet_virtuals.tsv')

# Virtual checks
virtual_sense_ids = {v['sense_id'] for v in virtuals}
assert len(virtual_sense_ids) == len(virtuals), "Repeat entries with the same sense ID (chainnet_virtuals.tsv)"
virtual_sense_ids_to_wordform = {v['sense_id']: v['wordform'] for v in virtuals}
origin_senses = [v['origin_sense_id'] for v in virtuals if v['origin_sense_id'] != ""]
assert all([v['definition'] != "" for v in virtuals]), "Definition(s) missing in chainnet_virtuals.tsv"
for s1 in origin_senses:
    assert len([s2 for s2 in origin_senses if s2 == s1]) == 2, f'Split sense {s1} does not have two components in chainnet_virtuals.tsv'

# Basic checks
to_senses = set()
wordforms = set()
for i, edge in enumerate(edges):
    wordforms.add(edge['wordform'])
    assert edge['label'] in {'metaphor', 'metonymy'}, f"Edge label {edge['label']} invalid; must read \'metaphor\' or \'metonymy\' (line {i+2} of chainnet_edges.tsv)"

    for sense_id in ['from_sense_id', 'to_sense_id']:
        if '%V' not in edge[sense_id] and '%M' not in edge[sense_id]:
            to_sense = wn.lemma_from_key(edge[sense_id])
            assert to_sense.name().lower() == edge['wordform'], f"Sense {edge[sense_id]} is not a sense of \'{edge['wordform']}\' (line {i+2} of chainnet_edges.tsv)"
        else:
            assert edge[sense_id] in virtual_sense_ids_to_wordform.keys()
            assert edge['wordform'] == virtual_sense_ids_to_wordform[edge[sense_id]], f"Virtual sense {edge[sense_id]} given inconsistent wordform label in chainnet_virtuals.tsv and chainnet_edges.tsv"
            virtual_sense_ids.discard(edge[sense_id])

    assert edge['to_sense_id'] not in to_senses, f"Sense {edge['to_sense_id']} has two incoming edges (repeat on line {i+2} of chainnet_edges.tsv)"
    to_senses.add(edge['to_sense_id'])

assert len(virtual_sense_ids) == 0, f"Virtual sense IDs in chainnet_virtuals.tsv that do not appear in chainnet_edges.tsv: {virtual_sense_ids}"


def is_valid_forest(edges):
    # Build adjacency list and in-degree count
    graph = defaultdict(set)
    in_degree = defaultdict(int)
    nodes = set()

    for a, b in edges:
        if b in graph[a]:  # Prevent duplicate edges
            continue
        graph[a].add(b)
        in_degree[b] += 1
        nodes.add(a)
        nodes.add(b)

    # Find roots (nodes with in-degree 0)
    roots = {node for node in nodes if in_degree[node] == 0}

    if not roots:
        return False  # No roots means there is a cycle

    visited = set()

    # DFS to check for cycles and connectivity
    def dfs(node):
        if node in visited:
            return False  # Cycle detected
        visited.add(node)
        for neighbor in graph[node]:
            if not dfs(neighbor):
                return False
        return True

    # Check each tree separately
    for root in roots:
        if not dfs(root):
            return False

    # Ensure all nodes are visited (no disconnected cycles)
    return len(visited) == len(nodes)

# Forest check
for wordform in wordforms:
    edge_subset = [(e['from_sense_id'], e['to_sense_id']) for e in edges if e['wordform'] == wordform]
    assert is_valid_forest(edge_subset), f"Wordform \'{wordform}\' is not a valid forest structure"

print('PASSED')