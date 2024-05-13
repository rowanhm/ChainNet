from collections import defaultdict
from nltk.corpus import wordnet as wn
from nltk.corpus.reader import WordNetError

from python.common.common import info, save_pickle, warn
from python.common.global_variables import pos_map

assert wn.get_version() == '3.0'

info('Extracting')
lemmas_to_senses = defaultdict(set)
for synset in wn.all_synsets():
    pos = pos_map[synset.pos()]

    for word in synset.lemmas():
        sense_id = word.key()
        wordform = word.name()
        index = 1

        # Check the sense is fine
        try:
            wn.lemma_from_key(sense_id)
            lemmas_to_senses[f'{wordform.lower()}:{pos}:{index}'].add(sense_id)
        except WordNetError:
            warn(f'{sense_id} not safe; skipping')


info('Ordering')
lemmas_to_senses_ordered = {}
for lemma_id, sense_ids in lemmas_to_senses.items():
    wordform, pos, index = lemma_id.split(':')
    synsets = wn.synsets(wordform)
    sense_ids_ordered = []
    for sense in wn.lemmas(wordform):
        sense_id = sense.key()
        if sense_id in sense_ids and sense_id not in sense_ids_ordered:
            sense_ids_ordered.append(sense_id)
    assert set(sense_ids_ordered) == sense_ids, f'{sense_ids_ordered} != {sense_ids}'
    assert len(sense_ids_ordered) == len(set(sense_ids_ordered))
    lemmas_to_senses_ordered[lemma_id] = sense_ids_ordered

info('Saving')
save_pickle('bin/collection/lemmas_to_senses.pkl', lemmas_to_senses_ordered)
