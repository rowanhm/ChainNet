import math
import random
from collections import defaultdict

from python.common.common import open_json, info, safe_lemma_from_key, open_pickle

rand = random.Random(10)


def partition(collection):
    if len(collection) == 1:
        yield [collection]
        return

    first = collection[0]
    for smaller in partition(collection[1:]):
        # insert `first` in each of the subpartition's subsets
        for n, subset in enumerate(smaller):
            yield smaller[:n] + [[first] + subset] + smaller[n + 1:]
        # put `first` in its own subset
        yield [[first]] + smaller


def cayleys(n):
    return int(math.pow(n, n - 2))


def tree_possibilities(n, k):
    num_trees = cayleys(n)
    num_edge_labellings = int(math.pow(k, n - 1))
    num_roots = n
    possibilities = num_roots * num_edge_labellings * num_trees
    return possibilities


def num_options(num_nodes, num_edge_labels=2):
    inner_cache = {}
    outer_cache = {}

    total_options = 0

    labelled_edges = list(range(num_nodes))

    for components in partition(labelled_edges):
        component_sizes = [len(c) for c in components]
        component_sizes.sort()

        code = '_'.join([str(s) for s in component_sizes])
        if code in outer_cache.keys():
            all_possibilities = outer_cache[code]
        else:
            assert len(component_sizes) > 0 and 0 not in component_sizes
            all_possibilities = 1
            for component_size in component_sizes:

                # if component_size == 1:
                #     possibilities = 1
                # else:
                # assert component_size > 1

                if component_size in inner_cache.keys():
                    possibilities = inner_cache[component_size]
                else:
                    possibilities = tree_possibilities(n=component_size, k=num_edge_labels)
                    inner_cache[component_size] = possibilities

                all_possibilities *= possibilities  # Each one can go with each other one

            outer_cache[code] = all_possibilities

        total_options += all_possibilities

    return total_options


info('Loading')
lemmas_to_senses_raw = open_json('bin/lemmas_to_senses.json')

info('Filtering monosemes')
lemmas_to_senses_filtered = {}
for lemma_id, sense_ids in lemmas_to_senses_raw.items():
    if len(sense_ids) >= 2:
        lemmas_to_senses_filtered[lemma_id] = sense_ids
info(f'{len(lemmas_to_senses_raw)} -> {len(lemmas_to_senses_filtered)} lemmas')
lemmas_to_senses = lemmas_to_senses_filtered

info('Filtering proper nouns')
# Takes care of e.g. 'Macedonia'
# (lemmas where every sense is an instance hypernym)
lemmas_to_senses_filtered = {}
for lemma_id, sense_ids in lemmas_to_senses.items():
    word = lemma_id.split(':')[0]

    # Check that at least one sense in not an instance_hypernym
    one_not_instance_hypernym = False
    one_lowercased = False
    for sense_id in sense_ids:
        wn_lemma = safe_lemma_from_key(word, sense_id)
        synset = wn_lemma.synset()
        instance_hypernyms = synset.instance_hypernyms()
        if len(instance_hypernyms) == 0:
            one_not_instance_hypernym = True
        form = wn_lemma.name()
        if form == form.lower():
            one_lowercased = True

        # Add it
        if one_lowercased and one_not_instance_hypernym:
            lemmas_to_senses_filtered[lemma_id] = sense_ids
            break

info(f'{len(lemmas_to_senses)} -> {len(lemmas_to_senses_filtered)} lemmas')
lemmas_to_senses = lemmas_to_senses_filtered

info('Filtering single letter wordforms')
lemmas_to_senses_filtered = {}
for lemma_id, sense_ids in lemmas_to_senses.items():
    word = lemma_id.split(':')[0]
    if len(word) > 1:
        lemmas_to_senses_filtered[lemma_id] = sense_ids
info(f'{len(lemmas_to_senses)} -> {len(lemmas_to_senses_filtered)} lemmas')
lemmas_to_senses = lemmas_to_senses_filtered

info('Filtering wordforms with hyphens or underscores')
lemmas_to_senses_filtered = {}
for lemma_id, sense_ids in lemmas_to_senses.items():
    if not ('_' in lemma_id or '-' in lemma_id):
        lemmas_to_senses_filtered[lemma_id] = sense_ids
info(f'{len(lemmas_to_senses)} -> {len(lemmas_to_senses_filtered)} lemmas')
lemmas_to_senses = lemmas_to_senses_filtered

info('Filtering words done so far')
done_words = set()
chainnet_data = open_pickle('bin/analysis/chainnet.pkl')
done_words = set(chainnet_data.keys())

info('Reformatting')
num_senses_to_lemmas_all = defaultdict(set)
for lemma_id, sense_ids in lemmas_to_senses_raw.items():
    wordform, pos, _ = lemma_id.split(':')
    if pos != 'noun':
        continue
    num_senses_to_lemmas_all[len(sense_ids)].add(wordform)

num_senses_to_lemmas_filtered = defaultdict(set)
for lemma_id, sense_ids in lemmas_to_senses.items():
    wordform, pos, _ = lemma_id.split(':')
    if pos != 'noun':
        continue
    num_senses_to_lemmas_filtered[len(sense_ids)].add(wordform)

num_senses_to_lemmas_done = defaultdict(set)
for word in done_words:
    num_senses = len(lemmas_to_senses[f'{word}:noun:1'])
    num_senses_to_lemmas_done[num_senses].add(word)

info('Printing')

total_senses_done = 0
total_words_done = 0
print('\\# senses & \\multicolumn{2}{c}{\\# possibilities} & \\multicolumn{4}{c}{\\# wordforms} \\\\ \\midrule')
for i in range(2, 11):
    lemmas = num_senses_to_lemmas_all[i]
    lemmas_done = num_senses_to_lemmas_done[i]
    assert len(lemmas_done.union(lemmas)) == len(lemmas)  # subset
    total_senses_done += i * len(lemmas_done)
    total_words_done += len(lemmas_done)
    if len(lemmas) == 0:
        continue

    num_possibilities = num_options(i)

    print(
        f'{"hphantom{$0$}" if i < 10 else ""}${i}$ & ${f"{num_possibilities:.2e}".replace("e+", "$ & $times 10^{")}}}$ & ${len(lemmas_done)}$ & / & ${len(lemmas)}$ & (${int(round(100 * len(lemmas_done) / len(lemmas)))}\\%$) \\\\'.replace(
            'times', '\\times').replace('hphantom', '\\hphantom'))

total_words_all = sum([len(s) for n, s in num_senses_to_lemmas_all.items() if n > 1 and n < 11])
total_senses_all = sum([n * len(s) for n, s in num_senses_to_lemmas_all.items() if n > 1 and n < 11])
print(f'{total_words_done}/{total_words_all} words with 2-10 senses done')
print(f'{total_senses_done}/{total_senses_all} senses of these total words done')
