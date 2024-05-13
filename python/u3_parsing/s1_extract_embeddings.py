# Build dicts of embeddings, and vocabulary
import os
import numpy as np
from bidict import bidict
from gensim.models import KeyedVectors
from nltk.corpus import wordnet as wn
from python.common.common import info, save_pickle, warn


assert wn.get_version() == '3.0'

info("Opening sense embeddings")

sensembert_file = 'bin/parsing/sensembert_embeddings.bin'
if os.path.isfile(sensembert_file):
    info("Opening SensEmBERT sense embeddings from binary")
    sensembert_sense_embs = KeyedVectors.load_word2vec_format(sensembert_file, binary=True)
else:
    info("Opening SensEmBERT sense embeddings from text")
    sensembert_sense_embs = KeyedVectors.load_word2vec_format('data/parsing/sensembert_data/sensembert_EN_supervised.txt',
                                                              binary=False)
    sensembert_sense_embs.save_word2vec_format(sensembert_file, binary=True)

info("Getting all noun senses")
senses = set()
words = set()
for synset in wn.all_synsets('n'):
    for sense in synset.lemmas():
        senses.add(sense.key())
        words.add(sense.name())

info("Ordering and indexing them")
senses_sorted = sorted(list(senses))
words_sorted = sorted(list(words))

info('Creating sense embedding dictionaries')
sensembert_embeddings = {}

index = 1
sense_vocabulary = {}
excluded = set()
for sense in senses_sorted:

    if sense not in sensembert_sense_embs:
        excluded.add(sense)
        continue

    sense_vocabulary[sense] = index
    sensembert_embeddings[index] = sensembert_sense_embs[sense]

    index += 1

info(f'{index} senses indexed')
if len(excluded) > 0:
    warn(f'{len(excluded)} senses excluded" {excluded}')

info('Adding padding embedding')
embedding_size = len(list(sensembert_embeddings.values())[0])
sensembert_embeddings[0] = np.zeros(embedding_size)

info("Saving vocab and each embedding dict")
save_pickle('bin/parsing/sensembert_embeddings.pkl', sensembert_embeddings)
save_pickle('bin/parsing/sense_vocabulary.pkl', bidict(sense_vocabulary))  # WN sense ('lemma') IDS -> index of emb

info('Done')
