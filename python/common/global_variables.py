pos_map = {
    'v': 'verb',
    'n': 'noun',
    'r': 'adv',
    'a': 'adj',
    's': 'adj'
}

pos_map_reverse = {
    'verb': {'v'},
    'noun': {'n'},
    'adv': {'r'},
    'adj': {'a', 's'}
}

# Polysemy Parsing:

seed = 42

import torch
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

BATCH_SIZE = 32
EARLY_STOPPING = 8
RESTART_WITH_DIVISOR = 1
EPSILON = 1e-6
LEARNING_RATE = 0.00005
BETAS = (0.9, 0.9)

TESTING = False

EDGE_TYPE_MAP = {
    "prototype": 0,
    "metonymy": 1,
    "metaphor": 2
}