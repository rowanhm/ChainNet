import json

from python.common.common import open_pickle, info, warn, save_pickle, save_json


def get_anno_data(anno_id, filter='base'):

    raw_data = open_pickle(f'bin/collection/output/{anno_id}.pkl')
    output = {}
    queues_done = set()
    for queue_id, data in raw_data.items():
        if (anno_id in queue_id and 'i' not in queue_id and 'redo' not in queue_id):
            if len(data) != 10:
                warn(f'Queue {queue_id} incomplete')
            queues_done.add(queue_id.split(':')[1])

            for wordform, word_data in data.items():
                output[wordform] = word_data

    # Redos
    if f"{anno_id}:redos" in raw_data.keys():
        info(f'Overriding {anno_id} redos')
        for wordform, word_data in data.items():
            assert wordform in output.keys()
            output[wordform] = word_data

    info(f'{len(queues_done)} queues loaded for {anno_id} with {len(output)} words')
    return output

chainnet = get_anno_data('annotator01')

# Adding in 2nd annotator's words
for other_annotator in ['annotator02', 'annotator03']:
    chainnet_2 = get_anno_data(other_annotator)

    for k, v in chainnet_2.items():
        if k not in chainnet.keys():
            chainnet[k] = v

# Overriding author edits
author_data = open_pickle(f'bin/collection/output/author.pkl')
for queue_id, data in author_data.items():
    if "overlap" in queue_id:
        for wordform, word_data in data.items():
            assert wordform in chainnet.keys()
            chainnet[wordform] = word_data

edit_queues = sorted([q for q in author_data.keys() if 'edits' in q] + ['edits:0.9'], key=lambda x : float(x.split(':')[1]))
assert len(edit_queues) > 0

for queue_id in edit_queues:

    version = queue_id.split(':')[1]
    changed = 0

    if queue_id in author_data.keys():
        for wordform, word_data in data.items():
            assert wordform in chainnet.keys()
            chainnet[wordform] = word_data
            changed += 1

    info(f'Saving ChainNet v{version} with a total of {len(chainnet)} words ({changed} changed)')
    json_output = {
        'metadata': {
            'author': "Rowan Hall Maudslay",
            'version': str(version)
        },
        'content': [word.to_dict() for word_string, word in chainnet.items()]
    }  #sorted([word.to_dict() for word_string, word in chainnet.items()], key=lambda x: x['wordform'])
    save_json(f'data/versions/chainnet_v{version}.json', json_output)

info(f'Saving definitive v{version}')
save_pickle('bin/analysis/chainnet.pkl', chainnet)
save_json(f'data/chainnet.json', json_output)

info('Done')