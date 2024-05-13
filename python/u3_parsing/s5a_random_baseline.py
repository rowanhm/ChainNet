from collections import defaultdict

import numpy as np

from python.common.common import open_pickle, info, save_pickle
import random

from python.common.global_variables import seed

random.seed(seed)

info('Loading data')
for dataset in 'dev', 'test':

    test = open_pickle(f'bin/parsing/data/{dataset}.pkl')
    sense_embs = open_pickle('bin/parsing/sensembert_embeddings.pkl')
    vocab = open_pickle('bin/parsing/sense_vocabulary.pkl')

    info('Processing')
    random_labels = {}
    random_heads = defaultdict(list)

    labels = [1, 2]

    for (wordform, senses, _, _) in test:

        num_senses = len(senses)

        # Random labels:
        label_matrix = np.zeros([num_senses,num_senses+1]).astype(int)
        for i in range(num_senses):
            for j in range(num_senses):
                if i != j:
                    label_matrix[i, j+1] = random.choice(labels)
        random_labels[wordform] = label_matrix

        # Random heads
        possible_heads = list(range(-1, num_senses))
        local_heads = []
        for i, s in enumerate(senses):
            head = random.choice([p for p in possible_heads if p != i])
            assert head != i
            local_heads.append(head)

        # make sure one core
        # if 0 not in local_heads:
        #     local_heads[random.choice(range(len(local_heads)))] = 0
        # assert 0 in local_heads

        random_heads[wordform].append([h+1 for h in local_heads])

        for i in range(len(local_heads)):
            local_heads_copy = [l for l in local_heads]
            new_head = random.choice([p for p in possible_heads if p != i])
            assert new_head != i
            local_heads_copy[i] = new_head
            random_heads[wordform].append([h+1 for h in local_heads_copy])

    info('Saving')
    save_pickle(f'bin/parsing/output/{dataset}/connections/random_edge.pkl', random_heads)
    save_pickle(f'bin/parsing/output/{dataset}/labels/random_label.pkl', random_labels)

