from python.common.common import info, open_pickle, save_json

info('Loading')
lemma_to_senses = open_pickle('bin/collection/lemmas_to_senses.pkl')
concept_to_def = open_pickle('bin/collection/concepts_to_definitions.pkl')
sense_to_info = open_pickle('bin/collection/senses_to_info.pkl')

info('Checks')
# Check every sense and concept, in all the annotation, is accounted for in sense_to_info and concept_to_dict
for defn in concept_to_def.values():
    sense_ids = defn.get_all_senses()
    for sense_id in sense_ids:
        assert sense_id in sense_to_info.keys(), sense_id
for sense_info in sense_to_info.values():
    assert sense_info['concept_id'] in concept_to_def.keys()
    for example in sense_info['examples']:
        sense_ids = defn.get_all_senses()
        for sense_id in sense_ids:
            assert sense_id in sense_to_info.keys()
for sense_ids in lemma_to_senses.values():
    for sense_id in sense_ids:
        assert sense_id in sense_to_info.keys()

info('Processing lemma to senses')
save_json('bin/lemmas_to_senses.json', lemma_to_senses)

info('Processing concept to definition')
concept_to_def_flattened = {concept_id: defn.to_dict() for concept_id, defn in concept_to_def.items()}
save_json('bin/concepts_to_definitions.json', concept_to_def_flattened)

info('Processing sense to info')
sense_to_info_flattened = {}
for sense_id, sense_info in sense_to_info.items():
    sense_to_info_flattened[sense_id] = sense_info
save_json('bin/senses_to_info.json', sense_to_info_flattened)
