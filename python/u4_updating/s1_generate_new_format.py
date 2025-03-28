from python.common.common import open_json, save_csv

chainnet = open_json("data/chainnet.json")['content']

virtual_senses = []
edges = []
for datapoint in chainnet:

    outer_wordform = datapoint['wordform']

    sense_dict = {}
    for sense in datapoint['senses']:
        s_id = sense['sense_id']
        if sense['is_virtual']:
            assert sense['wordform'] == outer_wordform
            other_sense_id = sense['wordform'] + '%' + sense['sense_id']
            virtual_senses.append({
                'sense_id': other_sense_id,
                'wordform': outer_wordform,
                'definition': sense['definition'],
                'origin_sense_id': None
            })
        elif sense['is_split']:
            other_sense_id = sense['wordform'] + '%M' + sense['sense_id']
            virtual_senses.append({
                'sense_id': other_sense_id,
                'wordform': outer_wordform,
                'definition': sense['definition'],
                'origin_sense_id': sense['wordnet_sense_id']
            })
        else:
            other_sense_id = sense['wordnet_sense_id']
        sense_dict[s_id] = other_sense_id

    for sense in datapoint['senses']:
        label = sense['label']
        if label != "prototype":
            edges.append({
                'wordform': outer_wordform,
                'from_sense_id': sense_dict[sense['child_of']],
                'to_sense_id': sense_dict[sense['sense_id']],
                'label': label
            })

save_csv('data/working_files/chainnet_edges.tsv', sorted(edges, key=lambda x: x['wordform']))
save_csv('data/working_files/chainnet_virtuals.tsv', sorted(virtual_senses, key=lambda x: x['wordform']))