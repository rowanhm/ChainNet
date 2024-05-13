import random

from python.common.common import open_pickle, save_pickle, info
from python.common.global_variables import seed

random.seed(seed)

for dataset in ['dev', 'test']:
    labels = open_pickle(f'bin/parsing/output/{dataset}/labels/contextless_label.pkl')

    for wordform, labs in labels.items():
        for ls in labs:
            if ls[0] == 0:
                lab = random.choice([1,2])
                for i in range(1, len(ls)):
                    ls[i] = lab
            else:
                ls[0] = 0

    for wordform, labs in labels.items():
        for ls in labs:
            assert ls[0] == 0
            assert ls[1] in {1,2}

    save_pickle(f'bin/parsing/output/{dataset}/labels/contextless_label_reformed.pkl', labels)

info('Done')
