import glob
import itertools
import os.path
import re
from collections import defaultdict

from sklearn.metrics import accuracy_score

from python.common.common import info, open_dict_csv
from python.datatypes.sense_label import SenseLabel
from python.u3_parsing.utils.evaluation_utils import permutation_test


def los(gold, predicted):
    pred_labels = []
    gold_labels = []
    for index, gold_anno in gold.items():
        predicted_anno = predicted[index]

        gold_label = gold_anno['label']
        predicted_label = predicted_anno['label']

        pred_labels.append(predicted_label)
        gold_labels.append(gold_label)
    return accuracy_score(y_true=gold_labels, y_pred=pred_labels)


def extract_undirected_connections(data, labelled):
    connections = set()
    for key, annotation in data.items():

        sense_1 = annotation['sense_id']
        head_index = int(annotation["head"])
        label = annotation['label']
        if head_index == 0:
            assert label == SenseLabel.PROTOTYPE.value
            sense_2 = 'ROOT'
        else:
            assert label != SenseLabel.PROTOTYPE.value
            head_key = f'{annotation["wordform_index"]}.{head_index}'
            head_annotation = data[head_key]
            assert head_annotation['wordform'] == annotation['wordform']
            sense_2 = head_annotation['sense_id']

        if labelled:
            connections.add((frozenset({sense_1, sense_2}), label))
        else:
            connections.add(frozenset({sense_1, sense_2}))

    return connections


def uas(gold, predicted, labelled):
    gold_connections = extract_undirected_connections(gold, labelled=labelled)
    predicted_connections = extract_undirected_connections(predicted, labelled=labelled)

    score = len(gold_connections.intersection(predicted_connections)) / len(gold_connections)
    return score


def uuas(gold, predicted):
    return uas(gold=gold, predicted=predicted, labelled=False)


def ulas(gold, predicted):
    return uas(gold=gold, predicted=predicted, labelled=True)


def format_perc(value):
    value = round(value, 2)
    value = "{:.2f}".format(value)
    value = value[2:]  # Remove 0.
    value = "${}$".format(value)
    return value

def reformat_data(data):
    indices = set()
    for d in data:
        index = d['index']
        assert index not in indices
        indices.add(index)
    return {d['index']: d for d in data}


for dataset in ['test']:

    info(f"Loading {dataset} predictions")

    gold_data = reformat_data(open_dict_csv(f'bin/parsing/predictions/{dataset}/gold_standard.csv'))

    predictions = {}
    predictions_alts = defaultdict(list)

    for file in glob.glob(f'bin/parsing/predictions/{dataset}/*.csv'):
        name = os.path.basename(file)[:-4]
        if name == 'gold_standard':
            continue

        data = reformat_data(open_dict_csv(file))

        if '_top' in name:
            name_fixed = name.replace('_top', '')
            name_fixed = re.sub(r'[0-9]', '', name_fixed)
            predictions_alts[name_fixed].append(data)
        else:
            assert set(data.keys()) == set(gold_data.keys())
            predictions[name] = data

    # Stuff needed for top_n
    all_wordform_indices = {d['wordform_index'] for d in gold_data.values()}

    for name, data in predictions.items():
        predictions_alts[name].append(data)

    info('Finding top_n predictions')
    for name, datas in predictions_alts.items():
        all_best_biaff_data = []
        for wf_index in all_wordform_indices:
            gold_filtered = {k: d for k, d in gold_data.items() if d['wordform_index'] == wf_index}
            best_score = float('-inf')
            best_biaff_data = None
            for baiff_data in datas:
                baiff_data_filtered = {k: d for k, d in baiff_data.items() if d['wordform_index'] == wf_index}
                if len(baiff_data_filtered) == 0:
                    continue
                assert len(baiff_data_filtered) == len(gold_filtered)

                local_score = uuas(gold=gold_filtered, predicted=baiff_data_filtered)
                if local_score > best_score:
                    best_score = local_score
                    best_biaff_data = baiff_data_filtered
            assert best_biaff_data is not None
            if len(gold_filtered) > 1:
                all_best_biaff_data.extend(best_biaff_data.values())
            else:
                default_filtered = {k: d for k, d in predictions[name].items() if d['wordform_index'] == wf_index}
                all_best_biaff_data.extend(default_filtered.values())

        reformed_biaff_data = reformat_data(all_best_biaff_data)
        predictions[name+'+n'] = reformed_biaff_data
        assert set(reformed_biaff_data.keys()) == set(gold_data.keys())

    info('Computing')
    output = {}
    for metric_name, metric in [('LOS', los), ('UUAS', uuas), ('ULAS', ulas)]:

        scores = {}
        significance = {}

        for model_name, predicted in predictions.items():
            score = metric(gold=gold_data, predicted=predicted)
            scores[model_name] = score

        for model_name_1, model_name_2 in itertools.combinations(predictions.keys(), 2):
            if ('+n' in model_name_1 and not '+n' in model_name_2) or ('+n' not in model_name_1 and '+n' in model_name_2):
                # One is +n one isn't
                if model_name_1.replace('+n', '') != model_name_2.replace('+n', ''):
                    # Different models
                    continue

            predicted_1 = predictions[model_name_1]
            predicted_2 = predictions[model_name_2]

            p = permutation_test(predicted_1, predicted_2, gold_data, metric, r=10000)
            significance[f'{model_name_1}/{model_name_2}'] = p

        output[metric_name] = (scores, significance)

    info('Printing')
    print('\n\\toprule\nModel & LOS & UUAS & ULAS \\\\ \midrule')
    for model in list(predictions.keys()):
        print(f"{model} & {format_perc(output['LOS'][0][model])} & {format_perc(output['UUAS'][0][model])} & {format_perc(output['ULAS'][0][model])} \\\\")
    print('\\bottomrule\n')

    info('Significant results (* = 0.05; ** = 0.01; *** = 0.001):')
    for metric_name, results in output.items():

        m = len(results[1])
        assert m == 9
        print(f'\n{metric_name} significance (m={m}):')
        for combo, p in results[1].items():
            rating = 0

            # Bonferroni corrections
            p *= (m/3)

            for alpha in [0.05, 0.01, 0.001]:
                if p <= alpha:
                    rating += 1

            model_1, model_2 = combo.split('/')
            if results[0][model_1] > results[0][model_2]:
                best = model_1
                worst = model_2
            else:
                best = model_2
                worst = model_1

            print(f'{best} > {worst} {"*"*rating if rating > 0 else "NOT SIGNIFICANT"} (p={p})')

info('Done')
