import os.path

from python.common.common import info, open_pickle, open_json, save_json
from python.datatypes.feature_label import FeatureLabel
from python.datatypes.sense_label import SenseLabel
from colorama import Fore
from colorama import Style

def color(s, c):
    return f"{c}{s}{Style.RESET_ALL}"

def process_feature(feature):
    if feature.label == FeatureLabel.NEW:
        return None

    if feature.label == FeatureLabel.MODIFIED:
        new_string = feature.edited_feature_string
    else:
        new_string = ''

    base_string = None
    parent = feature
    while not base_string:
        parent = parent.source_feature
        if parent.label == FeatureLabel.NEW:
            base_string = parent.feature_string
        elif parent.label == FeatureLabel.MODIFIED:
            base_string = parent.edited_feature_string

    return (base_string, feature.label, new_string, feature.feature_id)

def extract_features(features):
    output = [process_feature(f) for f in features]
    return [o for o in output if o is not None]

def stringify(feature_tuple):
    base_string, label, edit, fid = feature_tuple
    if label == FeatureLabel.MODIFIED:
        output = color("This thing " + edit, Fore.YELLOW)
    elif label == FeatureLabel.KEPT:
        output = color("This thing " + base_string, Fore.GREEN)
    else:
        assert label == FeatureLabel.LOST
        output = color('\u0336'.join("This thing " + base_string) + '\u0336', Fore.RED)

    return f"This thing {base_string} --> {output}"


info('Loading overlap words')
queue_ids = ['overlaps:1', 'overlaps:2', 'overlaps:3']
words = set()
for queue_id in queue_ids:
    words.update({itm.split(':')[0] for itm in open_json('data/collection/queues.json')[queue_id]})


info('Loading annotation')
annotator_1 = 'annotator01'
annotator_2 = 'annotator02'

info(f'Comparing {annotator_1} and {annotator_2}')

annotator_1_raw = open_pickle(f'bin/collection/output/{annotator_1}.pkl')
annotator_2_raw = open_pickle(f'bin/collection/output/{annotator_2}.pkl')

info('Reformatting annotation')
annotation_1 = {}
for queue, annotation in annotator_1_raw.items():
    for word, anno in annotation.items():
        if word in words:
            annotation_1[word] = anno
annotation_2 = {}
for queue, annotation in annotator_2_raw.items():
    for word, anno in annotation.items():
        if word in words:
            annotation_2[word] = anno

info('Running loop')
output_file = f'bin/analysis/feature_alignments.json'
count = 0
for word in words:

    anno_1 = annotation_1[word].senses_by_wordnet_index()
    anno_2 = annotation_2[word].senses_by_wordnet_index()

    for wordnet_sense, anno_1_wn_sense in anno_1.items():

        # Check if done
        already_annotated = False
        data = []
        if os.path.isfile(output_file):
            data = open_json(output_file)
            for datapoint in data:
                if datapoint['word'] == word and datapoint['sense'] == wordnet_sense:
                    already_annotated = True
                    break
        if already_annotated:
            count += 1
            continue

        anno_2_wn_sense = anno_2[wordnet_sense]

        if len(anno_1_wn_sense) != 1 or len(anno_2_wn_sense) != 1:
            # One might be mixed
            continue

        if SenseLabel.METAPHOR not in anno_2_wn_sense.keys() or SenseLabel.METAPHOR not in anno_1_wn_sense.keys():
            # One might not be metaphorical
            continue

        anno_1_sense = anno_1_wn_sense[SenseLabel.METAPHOR]
        anno_2_sense = anno_2_wn_sense[SenseLabel.METAPHOR]

        if anno_1_sense.parent.wordnet_sense_id != anno_2_sense.parent.wordnet_sense_id:
            continue

        # They are a match!
        count += 1

        definition = anno_1_sense.definition
        parent_definition = anno_2_sense.parent.definition

        anno_1_features = extract_features(anno_1_sense.features)
        anno_2_features = extract_features(anno_2_sense.features)

        code_map = {}
        print(f'\n({count}) Word: {word}')
        print(f'{parent_definition} -> {definition}\n')
        print(f'Annotator 1:')
        for i, f in enumerate(anno_1_features):
            index = f"A{i + 1}"
            print(f"({index}) {stringify(f)}")
            code_map[index] = f"{annotator_1}:{f[-1]}"

        print(f'\nAnnotator 2:')
        for i, f in enumerate(anno_2_features):
            index = f"B{i + 1}"
            print(f"({index}) {stringify(f)}")
            code_map[index] = f"{annotator_2}:{f[-1]}"

        equivalences = input("\nEnter equivalences: ")
        clusters = equivalences.strip().split()
        output_clusters = []
        for cluster in clusters:
            assert 'A' in cluster and 'B' in cluster
            feature_codes = cluster.split(';')
            output_codes = []
            for feature_code in feature_codes:
                assert feature_code in code_map.keys()
                output_codes.append(code_map[feature_code])
                del code_map[feature_code]
            output_clusters.append(output_codes)
        remaining_features = list(code_map.values())

        # Save
        output = {
            'word': word,
            'sense': wordnet_sense,
            'feature_clusters': output_clusters,
            'excluded_features': remaining_features
        }
        data.append(output)
        save_json(output_file, data)

info("Analysing")
data = open_json(output_file)
info(f"{100 * len([d for d in data if d['feature_clusters'] != []])/len(data)}% of metaphors have shared feature")
info(f"{100 * len([d for d in data if len({s.split(':')[0] for s in d['excluded_features']})!=2])/len(data)}% of metaphors have all of one users features aligned")

excluded_features = 0
included_features = 0
for d in data:
    clusters = d['feature_clusters']
    excluded = d['excluded_features']
    excluded_features += len(excluded)
    for c in clusters:
        included_features += len(c)
info(f"{100*included_features/(included_features+excluded_features)}% of features are aligned")

