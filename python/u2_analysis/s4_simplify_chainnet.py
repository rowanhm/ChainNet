from collections import defaultdict

from python.common.common import info, open_json, safe_lemma_from_key, save_json, open_chainnet
from python.datatypes.sense_label import SenseLabel

info('Loading data')
chainnet = open_json('data/chainnet.json')
version = chainnet['metadata']['version']
chainnet = chainnet['content']

info('Processing into form')
all_data = {}

homonymy_data = []
connections = {
    'metaphor': [],
    'metonymy': []
}

for word_data in chainnet:

    wordform = word_data['wordform']

    # Build wordnet_id -> data map
    synset_edges = []
    senses = word_data['senses']
    sense_dict = {sense['sense_id']: sense for sense in senses}

    clusters = defaultdict(list)

    for sense_info in senses:
        sense_id = sense_info['sense_id']

        if sense_info['is_virtual']:
            continue
        if sense_info['is_split'] and sense_info['label'] == 'metaphor':
            continue

        # ID
        wordnet_id = sense_info['wordnet_sense_id']

        assert wordnet_id is not None
        synset = safe_lemma_from_key(wordform, wordnet_id).synset().name()

        # Label
        sense_label = sense_info['label']

        parent_wordnet_id = None
        if sense_label == SenseLabel.PROTOTYPE.value:
            parent_wordnet_id = None
            parent_synset = None

            clusters[sense_id].append(wordnet_id)
        else:
            head_sense_id = sense_info['child_of']
            while not parent_wordnet_id:
                parent_info = sense_dict[head_sense_id]

                if not parent_info['is_virtual']:
                    parent_wordnet_id = parent_info['wordnet_sense_id']
                else:
                    head_sense_id = parent_info['child_of']
            parent_synset = safe_lemma_from_key(wordform, parent_wordnet_id).synset().name()

            # Handle clusters
            head_sense_id = sense_info['child_of']
            while True:
                parent_info = sense_dict[head_sense_id]
                parent_core = parent_info['label'] == SenseLabel.PROTOTYPE.value
                if parent_core:
                    break
                head_sense_id = parent_info['child_of']
            clusters[head_sense_id].append(wordnet_id)

        synset_edges.append({
            'sense': wordnet_id,
            'concept': synset,
            'connection': sense_label,
            'parent_sense': parent_wordnet_id,
            'parent_concept': parent_synset
        })

        if sense_label != SenseLabel.PROTOTYPE.value:
            connections[sense_label].append({
                'wordform': wordform,
                'from_sense': parent_wordnet_id,
                'to_sense': wordnet_id
            })

    # Wordform, Sense keys, Head Positions, Labels
    all_data[wordform] = synset_edges

    homonymy_data.append({
        'wordform': wordform,
        'clusters': list(clusters.values())
    })

info('Extracting types')

info('Saving')

def wrap_data(data):
    return {
        'metadata': {
            'author': "Rowan Hall Maudslay",
            'version': str(version)
        },
        'content': data
    }

save_json('data/chainnet_simple/chainnet_metaphor.json', wrap_data(connections['metaphor']))
save_json('data/chainnet_simple/chainnet_metonymy.json', wrap_data(connections['metonymy']))
save_json('data/chainnet_simple/chainnet_homonymy.json', wrap_data(homonymy_data))

info('Done')