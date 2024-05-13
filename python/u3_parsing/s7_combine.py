from collections import defaultdict

from bidict import bidict

from python.common.common import open_pickle, info, save_csv
from python.common.global_variables import EDGE_TYPE_MAP

for dataset in ['test', 'dev']:

    test = open_pickle(f'bin/parsing/data/{dataset}.pkl')
    vocab = open_pickle('bin/parsing/sense_vocabulary.pkl')

    edge_map_rev = bidict(EDGE_TYPE_MAP).inv

    for combined_name, edge_name, label_name in [('gold_standard', 'gold_standard_edge', 'gold_standard_label'),
                                                 ('contextless_nearest', 'neighbour_edge', 'contextless_label_reformed'),
                                                 ('biaffine', 'biaffine_edge', 'biaffine_label'),
                                                 ('random', 'random_edge', 'random_label')]:

        info(f'Processing {combined_name}')

        all_labels = open_pickle(f'bin/parsing/output/{dataset}/labels/{label_name}.pkl')
        all_heads = open_pickle(f'bin/parsing/output/{dataset}/connections/{edge_name}.pkl')

        combined = defaultdict(list)

        for j, (wordform, sense_nums, _, _) in enumerate(test):

            senses = [vocab.inv[s.item()] for s in sense_nums]

            labels = all_labels[wordform]
            heads = all_heads[wordform]

            # Check shape
            assert len(heads[0]) == len(senses) == len(labels)
            assert all([len(l) == len(senses)+1 for l in labels])

            # Repackage heads
            labels = [[l[h] for l, h in zip(labels, local_heads)] for local_heads in heads]

            # Check cores correct
            for (ls, hs) in zip(labels, heads):
                for l, h in zip(ls, hs):
                    if h == 0:
                        # Core
                        assert l == 0
                    else:
                        # Connections
                        assert h > 0
                        assert l in {1, 2}

            for n, (ls, hs) in enumerate(zip(labels, heads)):
                assert len(senses) == len(ls) == len(hs)
                for i, (sense, label, head) in enumerate(zip(senses, ls, hs)):
                    combined[n].append({
                        'index': f'{j+1}.{i+1}',
                        'wordform': wordform,
                        'wordform_index': j+1,
                        'sense_id': sense,
                        'sense_index': i+1,
                        'label': edge_map_rev[label],
                        'head': head,
                    })

        for n, comb in combined.items():
            if n == 0:
                save_csv(f'bin/parsing/predictions/{dataset}/{combined_name}.csv', comb)
            else:
                save_csv(f'bin/parsing/predictions/{dataset}/{combined_name}_top{n}.csv', comb)
