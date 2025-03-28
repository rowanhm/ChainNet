from collections import defaultdict

from python.common.common import open_dict_csv, open_json, save_json
from nltk.corpus import wordnet as wn

# Loading edges
edges = open_dict_csv('data/working_files/chainnet_edges.tsv')
virtual_dict = {v['sense_id']: v for v in open_dict_csv('data/working_files/chainnet_virtuals.tsv')}

# Loading needed data
synset_to_definition = {k: v['string'] for k, v in open_json('bin/concepts_to_definitions.json').items()}
sense_to_examples = {k: v['examples'] for k, v in open_json('bin/senses_to_info.json').items()}
sense_to_synonyms = {k: [s['string'] for s in v['synonyms']] for k, v in open_json('bin/senses_to_info.json').items()}
words_to_senses = {k.split(':')[0]: v for k, v in open_json('bin/lemmas_to_senses.json').items() if ':noun:' in k}

# Remapping sense names
sense_remap = {}
for w, senses in words_to_senses.items():
    for i, sense in enumerate(senses):
        assert sense not in sense_remap.keys()
        sense_remap[sense] = f"{w}%{i+1}"
for sense in virtual_dict.keys():
    sense_remap[sense] = sense

# Adding prototypical senses
all_wordforms = set({e['wordform'] for e in edges})
all_sense_ids_by_wordform = {w: set(words_to_senses[w]) for w in all_wordforms}
for v, d in virtual_dict.items():
    wordform = d['wordform']
    all_sense_ids_by_wordform[wordform].add(v)
    if d['origin_sense_id'] != "":
        all_sense_ids_by_wordform[wordform].discard(d['origin_sense_id'])
all_to_senses = set({e['to_sense_id'] for e in edges})
for w, senses in all_sense_ids_by_wordform.items():
    for s in senses:
        if s not in all_to_senses:
            prototype_edge = {
                'wordform': w,
                'from_sense_id': None,
                'to_sense_id': s,
                'label': "prototype"
            }
            edges.append(prototype_edge)

# Process sense information into json form
chainnet_temp = defaultdict(list)
for edge in edges:
    wordform = edge['wordform']
    parent_sense_id = edge['from_sense_id']
    sense_id = edge['to_sense_id']
    label = edge['label']

    is_mixed = '%M' in sense_id
    is_virtual = '%V' in sense_id

    wordnet_sense_id = None
    if is_mixed:
        wordnet_sense_id = virtual_dict[sense_id]['origin_sense_id']
    elif not is_virtual:
        wordnet_sense_id = sense_id

    wordnet_synset_id = None
    if wordnet_sense_id is not None:
        wordnet_synset_id = wn.lemma_from_key(wordnet_sense_id).synset().name()

    if is_virtual or is_mixed:
        definition = virtual_dict[sense_id]['definition']
    else:
        # Generate definition
        synonym_string = ""
        synonyms = sense_to_synonyms[wordnet_sense_id]
        if len(synonyms) > 0:
            synonym_string = "[" + ", ".join(synonyms) + "] "

        example_string = ""
        examples = sense_to_examples[wordnet_sense_id]
        if len(examples) > 0:
            example_string = ", e.g. " + ", ".join(examples)

        definition = synonym_string + synset_to_definition[wordnet_synset_id] + example_string

    chainnet_temp[wordform].append({
        "sense_id": sense_remap[sense_id],
        "definition": definition,
        "wordnet_sense_id": wordnet_sense_id,
        "wordnet_synset_id": wordnet_synset_id,
        "label": label,
        "child_of": sense_remap[parent_sense_id] if parent_sense_id is not None else None,
        "is_virtual": is_virtual,
        "is_split": is_mixed
    })

# Constructing
chainnet_content = []
for w, senses in chainnet_temp.items():
    chainnet_content.append({
        'wordform': w,
        'senses': sorted(senses, key=lambda x: x['sense_id'])
    })
chainnet_content.sort(key=lambda x: x['wordform'])

chainnet_wrapped = {
    "metadata": {
        "resource": "ChainNet",
        "author": "Rowan Hall Maudslay",
        "version": "Working"
    },
    'content': chainnet_content
}

# Saving
save_json('data/working_files/chainnet_working.json', chainnet_wrapped)
