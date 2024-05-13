import numpy as np
import torch

from python.common.common import open_pickle, info, save_pickle, open_json, flatten
import random

from python.common.global_variables import EDGE_TYPE_MAP, seed
from python.datatypes.sense_label import SenseLabel

random.seed(seed)

info('Loading data')
chainnet = open_json('data/chainnet.json')
vocab = open_pickle('bin/parsing/sense_vocabulary.pkl')

info('Processing into form')

all_data = []

for word_data in chainnet:

    wordform = word_data['wordform']

    # Build wordnet_id -> data map
    synset_edges = []
    sense_dict = {sense['sense_id']: sense for sense in word_data['senses']}

    for sense_id, sense_info in sense_dict.items():
        if sense_info['is_virtual']:
            continue
        if sense_info['is_split'] and sense_info['label'] == 'metaphor':
            continue

        # ID
        wordnet_id = sense_info['wordnet_sense_id']
        assert wordnet_id is not None

        # Label
        sense_label = sense_info['label']

        parent_wordnet_id = None
        if sense_label == SenseLabel.PROTOTYPE.value:
            parent_wordnet_id = 'root'
        else:
            head_sense_id = sense_info['child_of']
            while not parent_wordnet_id:
                parent_info = sense_dict[head_sense_id]

                if not parent_info['is_virtual']:
                    parent_wordnet_id = parent_info['wordnet_sense_id']
                else:
                    head_sense_id = parent_info['child_of']

        synset_edges.append((wordnet_id, sense_label, parent_wordnet_id))

    # Convert to positions
    sense_to_position = {"root": 0}
    for i, (sense_key, _, _) in enumerate(synset_edges):
        sense_to_position[sense_key] = i+1

    head_positions = [(sense_to_position[sense_key], sense_to_position[head], EDGE_TYPE_MAP[edge_type]) for
                      (sense_key, edge_type, head) in synset_edges]

    x = [vocab[s] for (s, l, h) in synset_edges]
    x_tensor = torch.tensor(x)

    edges = [(head, edge_type) for (node, head, edge_type) in sorted(head_positions, key=lambda x: x[0])]
    y_heads, y_labels = zip(*edges)
    y_heads = torch.tensor(y_heads)
    y_labels = torch.tensor(y_labels)

    # Wordform, Sense keys, Head Positions, Labels
    all_data.append((wordform, x_tensor, y_heads, y_labels))

all_senses = set()
info('Sanity checking')
for (wordform, x_tensor, y_heads, y_labels) in all_data:
    for sense in x_tensor.tolist():
        assert sense not in all_senses
        all_senses.add(sense)
    for i, head in enumerate(y_heads):
        label = y_labels[i]
        if head == 0:
            assert label == 0  # Core
        else:
            assert 0 < head <= len(y_heads)
            assert label != 0  # Not core

info(f'{len(all_data)} words loaded with a total of {len(all_senses)} senses')

info('Splitting')
random.shuffle(all_data)

dev_count = round(0.1*len(all_data))

test = all_data[-dev_count:]
dev = all_data[-2*dev_count:-dev_count]
train = all_data[:-2*dev_count]
assert len(test) + len(dev) + len(train) == len(all_data)

output = [('train', train), ('dev', dev), ('test', test)]

info('Saving')
for name, d in output:
    lengths = flatten([[len(dp[1])]*len(dp[1]) for dp in d])

    info(f'{name}: mean # senses = {np.mean(lengths)}; median # senses = {np.median(lengths)}')
    info(f'{name}: {len(d)} words ({sum([len(x[1]) for x in d])} senses)')
    save_pickle(f'bin/parsing/data/{name}.pkl', d)

info('Done')
