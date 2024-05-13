from dateutil import parser

from python.common.common import warn, info, save_json, open_json, save_pickle
from python.datatypes.feature.kept_feature import KeptFeature
from python.datatypes.feature.lost_feature import LostFeature
from python.datatypes.feature.modified_feature import ModifiedFeature
from python.datatypes.feature.new_feature import NewFeature
from python.datatypes.sense import Sense
from python.datatypes.sense_label import SenseLabel
from python.datatypes.wordform import WordForm


def get_wordnet_id(sense_id):
    # Reformat ID
    if sense_id[:8] == 'wordnet:':
        sense_id = sense_id[8:]
    elif sense_id[:10] == 'A_wordnet:':
        sense_id = sense_id[10:]
    elif sense_id[:10] == 'B_wordnet:':
        sense_id = sense_id[10:]
    elif sense_id[:4] == 'new:':
        return None
    else:
        assert False, f'Sense ID {sense_id} invalid'
    return sense_id


def filter_time(time_string):
    # Remove time zone from end
    return '('.join(time_string.split('(')[:-1]).rstrip()


def process_into_obj(wordform, lemma_values, user_id):

    # Extract time from logs
    try:
        start_log = lemma_values['logs'][0]
        end_log = lemma_values['logs'][-1]

        assert start_log['action'] == 'lemma_initialised'
        if end_log['action'] != 'submit':
            warn(f'Final log for {user_id} "{wordform}" is not submit')

        start_time = parser.parse(filter_time(start_log['time']))
        end_time = parser.parse(filter_time(end_log['time']))
        seconds_taken = (end_time - start_time).seconds

        date = end_time.date()
    except KeyError:
        warn(f'No logs for {user_id} "{wordform}"')
        start_time = None
        end_time = None
        seconds_taken = None
        date = None

    word_known = lemma_values['word_known']

    senses_dict = {}
    old_sense_id_to_new_sense_id = {}
    new_sense_id_to_data = {}
    outward_ids = []
    virtual_count = 0

    raw_sense_data = list(lemma_values['senses'].items())

    for i, (sense_id, sense_values) in enumerate(sorted(raw_sense_data, key=lambda x: x[1]['position'])):

        wordnet_sense_id = get_wordnet_id(sense_id)
        outward_id = sense_values['outward_id']
        position = sense_values['position']

        is_virtual = sense_values['is_virtual']
        if is_virtual:
            assert wordnet_sense_id is None
            virtual_count += 1
            outward_id = f'V{virtual_count}'

        old_sense_id_to_new_sense_id[sense_id] = outward_id
        outward_ids.append(outward_id)

        definition = sense_values['definition']
        is_known = sense_values['is_known']
        is_mixed = sense_values['is_mixed']
        if is_mixed:
            assert sense_id[0] in {'A', 'B'}

        label = sense_values['label']
        if label == 'association':
            label = SenseLabel.METONYMY
        elif label == 'metaphor':
            label = SenseLabel.METAPHOR
        else:
            assert label == 'core', f'Invalid label {label}'
            label = SenseLabel.PROTOTYPE

        new_sense_id_to_data[outward_id] = sense_values

        sense = Sense(sense_id=outward_id, wordnet_sense_id=wordnet_sense_id, is_known=is_known,
                      is_virtual=is_virtual, is_mixed=is_mixed, definition=definition, label=label,
                      position=position)

        senses_dict[outward_id] = sense

    # SECOND PARSE -- add parents and order
    senses = []
    for outward_id in outward_ids:
        sense = senses_dict[outward_id]

        # Add parent
        if sense.label != SenseLabel.PROTOTYPE:
            connection_old_sense_id = new_sense_id_to_data[outward_id]['connected_to']
            connection_sense = senses_dict[old_sense_id_to_new_sense_id[connection_old_sense_id]]
            sense.set_parent(connection_sense)

        senses.append(sense)

    # FINAL PARSE -- add features
    queue = [sense for sense in senses if sense.label == SenseLabel.PROTOTYPE]
    # Queue is a list of senses
    feature_map = {}
    while queue:

        sense = queue.pop(0)
        sense_values = new_sense_id_to_data[sense.sense_id]

        # First, if the sense is a metaphor, add any edited features.

        if 'features' in sense_values.keys():
            remaining_features = sense_values['features']
        else:
            remaining_features = {}

        if sense.label == SenseLabel.METAPHOR:
            for (feature_key_raw, feature_label) in sense_values['feature_map'].items():
                source_feature_private_id = sense.parent.sense_id + '_' + feature_key_raw

                source_feature = feature_map[source_feature_private_id]

                outward_feature_id = f'{source_feature.feature_id}:{sense.sense_id}'

                if feature_label == 'kept':
                    this_feature = KeptFeature(feature_id=outward_feature_id, source_feature=source_feature,
                                               sense=sense)
                    del remaining_features[feature_key_raw]
                elif feature_label == 'lost':
                    this_feature = LostFeature(feature_id=outward_feature_id, source_feature=source_feature,
                                               sense=sense)
                else:
                    assert feature_label == 'modified'
                    edited_string = sense_values['feature_modifications'][feature_key_raw]
                    this_feature = ModifiedFeature(feature_id=outward_feature_id,
                                                   source_feature=source_feature,
                                                   sense=sense, edited_feature_string=edited_string)
                    feature_key_raw += '(M)'
                    del remaining_features[feature_key_raw]

                this_feature_private_id = sense.sense_id + '_' + feature_key_raw
                feature_map[this_feature_private_id] = this_feature
                sense.add_feature(this_feature)

        # Next, add any (remaining) non-edited features
        for j, (feature_key_raw, feature_string) in enumerate(remaining_features.items()):
            feature_key = sense.sense_id + '_' + feature_key_raw

            feature_id = f'{wordform}:{sense.sense_id}_{j}'  # WordForm:Sense_Feature:ModSense1:ModSense2
            feature = NewFeature(feature_id=feature_id, sense=sense, feature_string=feature_string)
            sense.add_feature(feature)
            assert feature_key not in feature_map.keys()
            feature_map[feature_key] = feature

        # Enqueue its children
        for child in sense.children:
            queue.append(child)

    word_obj = WordForm(word_string=wordform, is_known=word_known, annotator_id=user_id,
                        annotation_time=seconds_taken, senses=senses, annotation_date=date, start_time=start_time,
                        end_time=end_time)

    return word_obj

def main():

    info('Opening raw JSON')

    data = open_json('bin/collection/metaphor-annotation-uk-default-rtdb-export.json')

    users = open_json('data/collection/users.json')

    for user_id, user_data in data.items():

        if user_id not in users.keys():
            continue
        username = users[user_id]

        info(f'Processing {user_id} ({username})')
        queue_ids = user_data['queues']

        output = {}

        output_by_queue = {}

        info('Preprocessing redos')
        overrides = {}
        redo_queue = f"{username}:redos"
        if redo_queue in queue_ids.keys():
            lemma_ids = queue_ids[redo_queue]
            for lemma_id, lemma_values in lemma_ids.items():
                wordform = lemma_id.split(':')[0]
                word_obj = process_into_obj(wordform, lemma_values, username)
                overrides[wordform] = word_obj

        info('Processing queues')
        for queue_id, lemma_ids in queue_ids.items():

            if queue_id == redo_queue or not (username in queue_id or queue_id == 'screener' or 'overlaps' in queue_id):
                continue

            local_output = {}
            for lemma_id, lemma_values in lemma_ids.items():

                wordform = lemma_id.split(':')[0]

                if wordform in overrides.keys() and ':i' not in queue_id:
                    info(f'Overriding {wordform}')
                    word_obj = overrides[wordform]
                else:
                    word_obj = process_into_obj(wordform, lemma_values, username)

                if ':i' not in queue_id:
                    output[wordform] = word_obj
                local_output[wordform] = word_obj

            output_by_queue[queue_id] = local_output

        info('Saving')
        save_pickle(f'bin/collection/output/{username}.pkl', output_by_queue)

    info('Done')

if __name__ == "__main__":
    main()
