import glob
import os
import random
from collections import defaultdict

import torch
from torch.utils.data import DataLoader

from python.common.common import open_pickle, info, save_pickle
from python.common.global_variables import BATCH_SIZE, seed, device
from python.u3_parsing.models.edge.biaffine_edge import BiaffineEdge
from python.u3_parsing.utils.training_utils import simple_collate_fn, initialise_model

random.seed(seed)
torch.manual_seed(seed=seed)

def get_lengths(lst):
    return [len(item) for item in lst]


embeddings = open_pickle('bin/parsing/sensembert_embeddings.pkl')

for dataset in ['test', 'dev']:
    info(f'Processing predictions on {dataset}')
    data = open_pickle(f'bin/parsing/data/{dataset}.pkl')
    test_loader = DataLoader(data, batch_size=BATCH_SIZE, shuffle=False, collate_fn=simple_collate_fn)

    info('Getting gold labels')
    senses = []
    gold_heads = []
    gold_labels = []
    words = []
    for batch_data in test_loader:

        (wordforms, sense_sets, all_heads, all_labels) = batch_data
        sense_sets = torch.nn.utils.rnn.pad_sequence(sense_sets, padding_value=-1, batch_first=True)

        lengths = [len(h) for h in all_heads]

        for s, num_senses in zip(sense_sets, lengths):
            senses.append(s[:num_senses].tolist())

        gold_heads.extend([h.tolist() for h in all_heads])
        gold_labels.extend([l.tolist() for l in all_labels])
        assert all([w not in words for w in wordforms])
        words.extend(wordforms)


    heads = defaultdict(list)
    labels = defaultdict(list)

    for fp in glob.iglob('bin/parsing/models/*.pth'):
        model_name = os.path.basename(fp)[:-4]

        info(f'Computing {model_name} predictions')
        model = initialise_model(model_name, embeddings)

        model.load_state_dict(torch.load(fp, map_location=device))
        model.eval()

        # Processing
        for batch_data in test_loader:

            (wordforms, sense_sets, all_heads, all_labels) = batch_data

            if isinstance(model, BiaffineEdge):
                batch_heads, batch_labels = model.predict(batch_data, top_n=True)
            else:
                batch_heads, batch_labels = model.predict(batch_data)

            heads[model_name].extend(batch_heads)
            labels[model_name].extend(batch_labels)

    info('Checking alignment')
    correct_lengths = get_lengths(senses)

    assert get_lengths(gold_labels) == correct_lengths
    assert get_lengths(gold_heads) == correct_lengths

    for model_name, predictions in heads.items():
        if predictions:
            pred_flat = [p[0] for p in predictions]
            assert get_lengths(pred_flat) == correct_lengths, \
                f"Model {model_name}'s head predictions don't align with target: {predictions}"

    for model_name, predictions in labels.items():
        if predictions:
            assert get_lengths(predictions) == correct_lengths, \
                f"Model {model_name}'s label predictions don't align with target: {predictions}"

    info('Saving')
    for model_name, predictions in heads.items():
        if predictions:
            assert len(words) == len(predictions)
            output = {w: p for w, p in zip(words, predictions)}
            save_pickle(f'bin/parsing/output/{dataset}/connections/{model_name}.pkl', output)

    for model_name, predictions in labels.items():
        if predictions:
            assert len(words) == len(predictions)
            output = {w: p for w, p in zip(words, predictions)}
            save_pickle(f'bin/parsing/output/{dataset}/labels/{model_name}.pkl', output)

    assert len(words) == len(gold_heads)
    assert len(words) == len(gold_labels)

    output = {w: [p] for w, p in zip(words, gold_heads)}
    save_pickle(f'bin/parsing/output/{dataset}/connections/gold_standard_edge.pkl', output)
    output = {w: [[l]*(len(ls)+1) for l in ls] for w, ls in zip(words, gold_labels)}
    save_pickle(f'bin/parsing/output/{dataset}/labels/gold_standard_label.pkl', output)

info('Done')
