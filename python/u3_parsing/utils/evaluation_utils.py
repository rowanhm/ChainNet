# evaluation scripts
import random
from collections import defaultdict

from python.common.common import info
from python.common.global_variables import seed

random.seed(seed)


def shuffle(predictions_1, predictions_2):
    assert len(predictions_1) == len(predictions_2)
    word_indices_to_keys = defaultdict(set)
    for key in predictions_1.keys():
        assert key in predictions_2.keys()
        word_index = key.split('.')[0]
        word_indices_to_keys[word_index].add(key)

    shuffled_1 = {}
    shuffled_2 = {}
    for keys in word_indices_to_keys.values():
        flip = random.getrandbits(1)
        for key in keys:
            if flip:
                shuffled_1[key] = predictions_2[key]
                shuffled_2[key] = predictions_1[key]
            else:
                shuffled_1[key] = predictions_1[key]
                shuffled_2[key] = predictions_2[key]

    return shuffled_1, shuffled_2

def eval_diff(predictions_1, predictions_2, truth, metric):
    model_1_result = metric(truth, predictions_1)
    model_2_result = metric(truth, predictions_2)
    observed_difference = abs(model_1_result - model_2_result)
    return observed_difference


def permutation_test(predictions_1, predictions_2, truth, metric, r=1000):
    info(f'Performing a permutation test with r={r} iterations')
    observed_difference = eval_diff(predictions_1, predictions_2, truth, metric)

    s = 0  # s is number of times the difference is greater that observed

    for i in range(r):
        if i+1 % (r//5) == 0:
            info(f'On iteration {i+1}/{r}')

        shuffled_1, shuffled_2 = shuffle(predictions_1, predictions_2)

        shuffled_difference = eval_diff(shuffled_1, shuffled_2, truth, metric)

        if shuffled_difference >= observed_difference:
            s += 1

    p = (s + 1) / (r + 1)
    return p
