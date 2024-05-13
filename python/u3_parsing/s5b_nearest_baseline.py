from collections import defaultdict

import numpy as np
import torch

from python.common.common import open_pickle, info, save_pickle
import random
from scipy.sparse.csgraph import minimum_spanning_tree

from python.common.global_variables import seed

random.seed(seed)

sense_embs = open_pickle('bin/parsing/sensembert_embeddings.pkl')
vocab = open_pickle('bin/parsing/sense_vocabulary.pkl')


def get_heads(rooted_upper_tri_dist, cores):
    MST = minimum_spanning_tree(rooted_upper_tri_dist).toarray().astype(bool)
    connections = np.maximum(MST, MST.transpose())

    # BFS
    heads = {c: -1 for c in cores}
    queue = [q for q in cores]

    assert len(queue) > 0
    while queue:
        sense = queue.pop(0)
        sense_connections = [c - 1 for c in connections[sense + 1].nonzero()]

        assert len(sense_connections) == 1  # Since it returns a unitary tuple with a list
        sense_connections = sense_connections[0]

        children = [s for s in sense_connections if s not in heads.keys() and s != -1]
        for c in children:
            assert c not in heads.keys()
            heads[c] = sense
        queue.extend(children)

    assert len(heads) == num_senses

    heads_reindexed = [heads[i] + 1 for i in range(num_senses)]
    return heads_reindexed


for dataset in ['test', 'dev']:
    info('Loading data')

    labels_test = open_pickle(f'bin/parsing/output/{dataset}/labels/contextless_label.pkl')
    test = open_pickle(f'bin/parsing/data/{dataset}.pkl')

    #clusters = open_csv_as_dict('data/within_pos_clusters.csv', key_col='wn_sense', val_col='lemma')

    info('Processing')
    nearest_heads = defaultdict(list)

    for (wordform, senses, _, _) in test:

        labels = labels_test[wordform]
        num_senses = len(senses)

        # NN heads
        embeddings = []
        for sense in senses:
            embeddings.append(sense_embs[sense.item()])

        embeddings_torch = torch.tensor(np.array(embeddings))

        a = embeddings_torch.unsqueeze(0).repeat(num_senses,1,1)
        b = embeddings_torch.unsqueeze(1).repeat(1,num_senses,1)
        diff = a-b
        diff_sq = torch.mul(diff, diff)
        diff_sum = torch.sum(diff_sq, dim=-1)
        dist = torch.sqrt(diff_sum)

        # Check symettrical
        assert torch.all(dist.transpose(0, 1) == dist)
        upper_tri_dist = torch.triu(dist, diagonal=1)

        # Compute MST
        rooted_upper_tri_dist = torch.zeros(num_senses+1, num_senses+1)
        rooted_upper_tri_dist[1:, 1:] = upper_tri_dist
        cores = []
        for i, ls in enumerate(labels):
            assert len(set(ls)) == 1
            l = ls[0]
            assert l in {0, 1, 2}
            if l == 0:  # Core
                rooted_upper_tri_dist[0, i+1] = -1
                cores.append(i)
        assert len(cores) >= 1

        heads = get_heads(rooted_upper_tri_dist, cores)
        nearest_heads[wordform].append(heads)  # +1 to reindex

        gold_MST = minimum_spanning_tree(rooted_upper_tri_dist).toarray().astype(bool)
        gold_MST = np.maximum(gold_MST, gold_MST.transpose())

        for i, h in enumerate(heads):
            rooted_upper_tri_edit = rooted_upper_tri_dist.clone()
            cores_edit = [q for q in cores]

            if i in cores_edit:
                cores_edit = [c for c in cores_edit if c != i]
                assert rooted_upper_tri_edit[0, i+1] == -1
                rooted_upper_tri_edit[0, i+1] = 0
                if len(cores_edit) == 0:
                    new_core = random.choice([s for s in range(len(heads)) if s != i])
                    cores_edit = [new_core]
                    rooted_upper_tri_edit[0, new_core+1] = -1
            else:
                assert gold_MST[i+1, h]
                assert gold_MST[h, i+1]
                if i+1 < h:
                    rooted_upper_tri_edit[i+1, h] = 0
                else:
                    assert i+1 > h
                    rooted_upper_tri_edit[h, i+1] = 0

                # Check it is not left isolated
                rooted_upper_tri_edit = torch.max(rooted_upper_tri_edit, rooted_upper_tri_edit.t())
                if all(rooted_upper_tri_edit[:, i+1]) == 0:
                    # Add core connection
                    rooted_upper_tri_edit[0, i+1] = -1
                    cores_edit.append(i)
                rooted_upper_tri_edit = torch.triu(rooted_upper_tri_edit, diagonal=1)

            new_heads = get_heads(rooted_upper_tri_edit, cores_edit)
            nearest_heads[wordform].append(new_heads)

    info('Saving')
    save_pickle(f'bin/parsing/output/{dataset}/connections/neighbour_edge.pkl', nearest_heads)

