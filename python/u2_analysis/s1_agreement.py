from sklearn.metrics import accuracy_score, cohen_kappa_score, \
    adjusted_mutual_info_score, adjusted_rand_score, homogeneity_completeness_v_measure
import itertools
import math
import warnings
from collections import defaultdict
from statsmodels.stats.inter_rater import fleiss_kappa, aggregate_raters
import numpy as np
import krippendorff

from python.common.common import open_pickle, info, flatten, open_json
from python.datatypes.sense_label import SenseLabel

def get_primary_sense(sense):
    if SenseLabel.PROTOTYPE in sense.keys():
        return sense[SenseLabel.PROTOTYPE]
    elif SenseLabel.METONYMY in sense.keys():
        return sense[SenseLabel.METONYMY]
    else:
        assert SenseLabel.METAPHOR in sense.keys()
        return sense[SenseLabel.METAPHOR]


def get_label(sense):
    assert len(sense.keys()) > 0
    if len(sense.keys()) > 1:
        # Mixed
        # label = "mixed"
        label = list([s for s in sense.keys() if s != SenseLabel.METAPHOR])[0].value
    else:
        label = list(sense.keys())[0].value
    return label


def get_head(sense):
    if SenseLabel.PROTOTYPE in sense.keys():
        return "root"
    elif SenseLabel.METONYMY in sense.keys():
        return sense[SenseLabel.METONYMY].parent.wordnet_sense_id
    else:
        assert SenseLabel.METAPHOR in sense.keys()
        return sense[SenseLabel.METAPHOR].parent.wordnet_sense_id


def get_cluster_id(sense_obj, cluster_dict, collapse_metaphors=True):
    # cluster dict is ID -> sense_set

    # check if it is already in a cluster
    for cluster_id, sense_ids in cluster_dict.items():
        if sense_obj.sense_id in sense_ids:
            return cluster_id, cluster_dict

    # else add a new cluster
    new_id = len(cluster_dict)
    cluster_dict[new_id] = get_cluster(sense_obj, collapse_metaphors=collapse_metaphors)
    return new_id, cluster_dict


def get_cluster(sense_obj, collapse_metaphors=True):
    # Go to root
    root = sense_obj
    while root.parent is not None:
        if collapse_metaphors or root.label != SenseLabel.METAPHOR:
            root = root.parent
        else:
            break

    # Go to all leaves
    queue = [root]
    visited = set()
    while queue:
        node = queue.pop(0)
        assert node.sense_id not in visited
        visited.add(node.sense_id)

        for child_node in list(node.children):
            if collapse_metaphors or child_node.label != SenseLabel.METAPHOR:
                queue.append(child_node)

    return visited


def get_labels_subsets(data):

    labels = defaultdict(list)  # anno_ind -> list
    labels_given_attachment = defaultdict(list)
    labels_given_core = defaultdict(list)

    for word, senses in data.items():
        labels_local = defaultdict(list)
        labels_local_given_attachment = defaultdict(list)
        labels_local_given_core = defaultdict(list)

        # Check if they agree core
        agree_core = True
        for sense_id, annos in senses.items():
            labs = {get_label(a) for a in annos}
            if SenseLabel.PROTOTYPE.value in labs and len(labs) > 1:  # One thinks it is core but others don't
                agree_core = False
                break

        for sense_id, annos in senses.items():
            labs = {i: get_label(a) for i, a in enumerate(annos)}

            for i, lab in labs.items():
                labels_local[i].append(lab)

            heads = {i: get_head(a) for i, a in enumerate(annos)}

            if len(set(heads.values())) == 1:
                # All agree on head
                for i, lab in labs.items():
                    labels_local_given_attachment[i].append(lab)

            if agree_core:
                for i, lab in labs.items():
                    labels_local_given_core[i].append(lab)

        # Add word

        for i, labs in labels_local.items():
            labels[i].append(labs)

        for i, labs in labels_local_given_attachment.items():
            labels_given_attachment[i].append(labs)

        for i, labs in labels_local_given_core.items():
            labels_given_core[i].append(labs)

    flat_labels = {i: flatten(labs) for i, labs in labels.items()}
    flat_labels_given_attachment = {i: flatten(labs) for i, labs in labels_given_attachment.items()}
    flat_labels_given_core = {i: flatten(labs) for i, labs in labels_given_core.items()}

    # Check each set the same length
    assert len({len(labs) for labs in flat_labels.values()}) == 1
    assert len({len(labs) for labs in flat_labels_given_attachment.values()}) == 1
    assert len({len(labs) for labs in flat_labels_given_core.values()}) == 1

    return flat_labels, flat_labels_given_attachment, flat_labels_given_core


def fleiss(label_data):
    # assumes subjects in rows, and categories in columns

    num_annotators = len(label_data)
    num_datapoints = len(label_data[0])
    lab_lookup = {}
    data = np.zeros((num_datapoints, num_annotators)).astype(int)

    for annotator_id, labs in label_data.items():
        for i, lab in enumerate(labs):
            if lab not in lab_lookup.keys():
                lab_code = len(lab_lookup)
                lab_lookup[lab] = lab_code
            lab_code = lab_lookup[lab]
            data[i, annotator_id] = lab_code

    # input to add is subjects (items) in rows and raters in columns
    agg_data = aggregate_raters(data)
    kappa = fleiss_kappa(agg_data[0])

    return kappa

def alpha(label_data):

    reliability_data = []
    lab_lookup = {}

    for annotator_id, labs in label_data.items():
        annotator_data = []
        for i, lab in enumerate(labs):
            if lab not in lab_lookup.keys():
                lab_code = len(lab_lookup)+1
                lab_lookup[lab] = lab_code
            lab_code = lab_lookup[lab]
            annotator_data.append(lab_code)
        reliability_data.append(annotator_data)

    return krippendorff.alpha(reliability_data=reliability_data, level_of_measurement="nominal")

def label_agreement(multi_data, num_annotators):
    # RQ: can it correctly say which senses are core/mixed/met/assoc?
    # -> do annotators agree which senses are mixed?
    # -> do annotators agree on which is metaphorical / non-metaphorical? (merge core & assoc)
    # -> do annotators agree on centrality? (merge assoc & met)

    multi_results = defaultdict(list)

    for anno_pos_1, anno_pos_2 in itertools.combinations(range(num_annotators), 2):

        data = {wordform: {sense: (annos[anno_pos_1], annos[anno_pos_2]) for sense, annos in senses.items()}
                for wordform, senses in multi_data.items()}

        flat_labels, flat_labels_given_attachment, flat_labels_given_core = get_labels_subsets(data)

        results = {}

        for label in [SenseLabel.PROTOTYPE.value, SenseLabel.METAPHOR.value, SenseLabel.METONYMY.value, 'mixed']:
            anno_1_label_only = [datapoint == label for datapoint in flat_labels[0]]
            anno_2_label_only = [datapoint == label for datapoint in flat_labels[1]]

            results[f'{label}:percent'] = accuracy_score(y_true=anno_1_label_only, y_pred=anno_2_label_only)
            results[f'{label}:cohens'] = cohen_kappa_score(y1=anno_1_label_only, y2=anno_2_label_only)

            anno_1_label_only_agreed_attachment = [datapoint == label for datapoint in
                                                   flat_labels_given_attachment[0]]
            anno_2_label_only_agreed_attachment = [datapoint == label for datapoint in
                                                   flat_labels_given_attachment[1]]

            results[f'{label}|attachment:percent'] = accuracy_score(y_true=anno_1_label_only_agreed_attachment,
                                                                            y_pred=anno_2_label_only_agreed_attachment)
            results[f'{label}|attachment:cohens'] = cohen_kappa_score(
                y1=anno_1_label_only_agreed_attachment,
                y2=anno_2_label_only_agreed_attachment)

            anno_1_label_only_agreed_core = [datapoint == label for datapoint in flat_labels_given_core[0]]
            anno_2_label_only_agreed_core = [datapoint == label for datapoint in flat_labels_given_core[1]]

            results[f'{label}|prototype:percent'] = accuracy_score(y_true=anno_1_label_only_agreed_core,
                                                                      y_pred=anno_2_label_only_agreed_core)
            results[f'{label}|prototype:cohens'] = cohen_kappa_score(y1=anno_1_label_only_agreed_core,
                                                                             y2=anno_2_label_only_agreed_core)

        results['all:percent'] = accuracy_score(y_true=flat_labels[0], y_pred=flat_labels[1])  # (LOS)
        results['all:cohens'] = cohen_kappa_score(y1=flat_labels[0], y2=flat_labels[1])

        results['all|attachment:percent'] = accuracy_score(y_true=flat_labels_given_attachment[0],
                                                                   y_pred=flat_labels_given_attachment[1])
        results['all|attachment:cohens'] = cohen_kappa_score(y1=flat_labels_given_attachment[0],
                                                                          y2=flat_labels_given_attachment[1])
        results['all|prototype:percent'] = accuracy_score(y_true=flat_labels_given_core[0],
                                                             y_pred=flat_labels_given_core[1])
        results['all|prototype:cohens'] = cohen_kappa_score(y1=flat_labels_given_core[0],
                                                                    y2=flat_labels_given_core[1])

        for k, v in results.items():
            multi_results[k].append(v)

    all_results = {k: np.mean(vs) for k, vs in multi_results.items()}

    # Now add fleiss and alpha
    flat_labels, flat_labels_given_attachment, flat_labels_given_core = get_labels_subsets(multi_data)

    for add_string, labels in [('', flat_labels),
                               ('|attachment', flat_labels_given_attachment),
                               ('|prototype', flat_labels_given_core)]:

        for label in [SenseLabel.PROTOTYPE.value, SenseLabel.METONYMY.value, SenseLabel.METAPHOR.value]:

            labels_filtered = {i: [datapoint == label for datapoint in labs] for i, labs in labels.items()}

            all_results[f'{label}{add_string}:fleiss'] = fleiss(labels_filtered)
            all_results[f'{label}{add_string}:alpha'] = alpha(labels_filtered)


        all_results[f'all{add_string}:fleiss'] = fleiss(labels)
        all_results[f'all{add_string}:alpha'] = alpha(labels)


    return all_results


def attachment_agreement(multi_data, num_annotators):
    # RQ do annotators agree on which node assoc/met connect to? both together and seperately
    # RQ what about coarse grained? do they connect them to a node that is itself connected to the right one?

    multi_results = defaultdict(list)

    for anno_pos_1, anno_pos_2 in itertools.combinations(range(num_annotators), 2):

        data = {wordform: {sense: (annos[anno_pos_1], annos[anno_pos_2]) for sense, annos in senses.items()}
                for wordform, senses in multi_data.items()}

        uaa_all = []
        las_and_all = []
        las_or_all = []
        uaa_both_agree_met = []
        uaa_both_agree_met_cluster = {
            True: [],
            False: []
        }
        uaa_both_agree_assoc = []

        uaa_both_agree_core = []
        las_both_agree_core = []

        for word, senses in data.items():

            # Check if they agree core
            agree_core = True
            for sense_id, (anno_1, anno_2) in senses.items():
                anno_1_label = get_label(anno_1)
                anno_2_label = get_label(anno_2)
                if (anno_1_label == SenseLabel.PROTOTYPE.value or anno_2_label == SenseLabel.PROTOTYPE.value) and (anno_1_label != anno_2_label):
                    agree_core = False
                    break
            # Process
            for sense_id, (anno_1, anno_2) in senses.items():

                anno_1_head = get_head(anno_1)
                anno_2_head = get_head(anno_2)
                is_correct = int(anno_1_head == anno_2_head)

                uaa_all.append(is_correct)

                anno_1_label = get_label(anno_1)
                anno_2_label = get_label(anno_2)
                las_and_all.append(is_correct and (anno_1_label == anno_2_label))
                las_or_all.append(is_correct or (anno_1_label == anno_2_label))

                if agree_core:
                    uaa_both_agree_core.append(is_correct)
                    las_both_agree_core.append(is_correct and (anno_1_label == anno_2_label))

                if anno_1_label == anno_2_label == "associated":
                    uaa_both_agree_assoc.append(is_correct)

                elif anno_1_label == anno_2_label == "metaphorical":
                    uaa_both_agree_met.append(is_correct)

                    # Check if it is in the same coarse grained class as the thing it connects to
                    assert anno_1_label != "root"
                    assert anno_2_label != "root"

                    for collapse_metaphor in [True, False]:
                        # Check that the test assignment has the gold node in the same group
                        is_correct_cluster_anno_1 = anno_1_head in get_cluster(anno_2[SenseLabel.METAPHOR],
                                                                               collapse_metaphors=collapse_metaphor)
                        # Check that the gold assignment has the test node in the same class (avoid case where test puts everything in same group)
                        is_correct_cluster_anno_2 = anno_2_head in get_cluster(anno_1[SenseLabel.METAPHOR],
                                                                               collapse_metaphors=collapse_metaphor)
                        is_correct_cluster = int(is_correct_cluster_anno_1 and is_correct_cluster_anno_2)

                        uaa_both_agree_met_cluster[collapse_metaphor].append(is_correct_cluster)

        results = {
            'all:uas': np.mean(uaa_all),
            'all:las/label_and_attachment': np.mean(las_and_all),
            'all:las/label_or_attachment': np.mean(las_or_all),
            'both_agree_associated:uas': np.mean(uaa_both_agree_assoc),
            'both_agree_metaphorical:uas': np.mean(uaa_both_agree_met),
            'both_agree_all:uas': np.mean(uaa_both_agree_assoc + uaa_both_agree_met),
            'both_agree_metaphorical:uas/clustered_collapsed_mets': np.mean(uaa_both_agree_met_cluster[True]),
            'both_agree_metaphorical:uas/clustered_seperated_mets': np.mean(uaa_both_agree_met_cluster[False]),
            'both_agree_core:uas': np.mean(uaa_both_agree_core),
            'both_agree_core:las': np.mean(las_both_agree_core),
        }

        # Recompute overall UAS and LAS with unordered edges
        # First get all edges
        anno_1_edges = []
        anno_2_edges = []

        anno_1_edges_agreed_core = []
        anno_2_edges_agreed_core = []

        for word, senses in data.items():
            # Check if they agree core
            agree_core = True
            for sense_id, (anno_1, anno_2) in senses.items():
                anno_1_label = get_label(anno_1)
                anno_2_label = get_label(anno_2)
                if (anno_1_label == SenseLabel.PROTOTYPE.value or anno_2_label == SenseLabel.PROTOTYPE.value) and (anno_1_label != anno_2_label):
                    agree_core = False
                    break

            for sense_id, (anno_1, anno_2) in senses.items():

                anno_1_head = get_head(anno_1)
                anno_2_head = get_head(anno_2)

                anno_1_label = get_label(anno_1)
                anno_2_label = get_label(anno_2)

                anno_1_edges.append(({anno_1_head, sense_id}, anno_1_label))
                anno_2_edges.append(({anno_2_head, sense_id}, anno_2_label))

                if agree_core:
                    anno_1_edges_agreed_core.append(({anno_1_head, sense_id}, anno_1_label))
                    anno_2_edges_agreed_core.append(({anno_2_head, sense_id}, anno_2_label))

        anno_2_edges_unlabelled = [edge for (edge, label) in anno_2_edges]
        agreements_labelled = []
        agreements_unlabelled = []
        for (edge, label) in anno_1_edges:

            if (edge, label) in anno_2_edges:
                agreements_labelled.append(True)
            else:
                agreements_labelled.append(False)

            if edge in anno_2_edges_unlabelled:
                agreements_unlabelled.append(True)
            else:
                agreements_unlabelled.append(False)

        anno_2_edges_agreed_core_unlabelled = [edge for (edge, label) in anno_2_edges_agreed_core]
        agreements_given_core_labelled = []
        agreements_given_core_unlabelled = []
        for (edge, label) in anno_1_edges_agreed_core:

            if (edge, label) in anno_2_edges_agreed_core:
                agreements_given_core_labelled.append(True)
            else:
                agreements_given_core_labelled.append(False)

            if edge in anno_2_edges_agreed_core_unlabelled:
                agreements_given_core_unlabelled.append(True)
            else:
                agreements_given_core_unlabelled.append(False)

        results['all:uuas'] = np.mean(agreements_unlabelled)
        results['all:ulas'] = np.mean(agreements_labelled)

        results['agreed_core:uuas'] = np.mean(agreements_given_core_unlabelled)
        results['agreed_core:ulas'] = np.mean(agreements_given_core_labelled)

        for k, v in results.items():
            multi_results[k].append(v)

    averaged_results = {k: np.mean(vs) for k, vs in multi_results.items()}

    return averaged_results


def cluster_agreement(multi_data, num_annotators):
    # RQ: do annotators agree on homonymy (w/ met)? (put into clusters, incl. metaphor) [clustering]

    results = defaultdict(list)

    for anno_pos_1, anno_pos_2 in itertools.combinations(range(num_annotators), 2):

        data = {wordform: {sense: (annos[anno_pos_1], annos[anno_pos_2]) for sense, annos in senses.items()}
                for wordform, senses in multi_data.items()}

        for collapse_metaphors in [True, False]:
            ami_results = []
            ari_results = []
            v_measure_results = []
            completeness_results = []
            homogeneity_results = []

            for word, senses in data.items():
                anno_1_assignments = []
                anno_2_assignments = []
                anno_1_cluster_dict = {}
                anno_2_cluster_dict = {}
                for wn_sense_id, (anno_1, anno_2) in senses.items():
                    anno_1_sense_obj = get_primary_sense(anno_1)
                    anno_2_sense_obj = get_primary_sense(anno_2)

                    anno_1_cluster_id, anno_1_cluster_dict = get_cluster_id(anno_1_sense_obj, anno_1_cluster_dict,
                                                                            collapse_metaphors=collapse_metaphors)
                    anno_2_cluster_id, anno_2_cluster_dict = get_cluster_id(anno_2_sense_obj, anno_2_cluster_dict,
                                                                            collapse_metaphors=collapse_metaphors)

                    anno_1_assignments.append(anno_1_cluster_id)
                    anno_2_assignments.append(anno_2_cluster_id)

                # Get result
                ami_results.append(adjusted_mutual_info_score(anno_1_assignments, anno_2_assignments))
                ari_results.append(adjusted_rand_score(anno_1_assignments, anno_2_assignments))

                homogeneity, completeness, v_measure = homogeneity_completeness_v_measure(anno_1_assignments,
                                                                                          anno_2_assignments)
                v_measure_results.append(v_measure)
                completeness_results.append(completeness)
                homogeneity_results.append(homogeneity)

            detail = 'collapsed_mets' if collapse_metaphors else 'seperated_mets'
            results[f'{detail}:ami'].append(np.mean(ami_results))
            results[f'{detail}:ari'].append(np.mean(ari_results))
            results[f'{detail}:v_measure'].append(np.mean(v_measure_results))
            results[f'{detail}:completeness'].append(np.mean(completeness_results))
            results[f'{detail}:homogeneity'].append(np.mean(homogeneity_results))

    # Now take a mean across all pairs
    averaged_results = {k: np.mean(vs) for k, vs in results.items()}
    return averaged_results


def has_virtual(wordform):
    for sense in wordform.senses:
        if sense.is_virtual:
            return True

    return False


def full_compare(raw_data, filter_unknown='words', min_senses=0, max_senses=100):

    # Get list of words in both
    num_annotators = len(raw_data)
    words = set.intersection(*[set(r.keys()) for r in raw_data])
    assert len(words) == 100

    words_filtered = set()
    lemmas_to_senses = open_json('bin/lemmas_to_senses.json')
    words_to_num_senses = {l.split(':')[0]: len(s) for l, s in lemmas_to_senses.items() if l.split(':')[1] == 'noun'}
    for word in words:
        if min_senses <= words_to_num_senses[word] <= max_senses:
            words_filtered.add(word)

    # info(f'Filtered to {min_senses} to {max_senses} words; {len(words_filtered)}/{len(words)} remaining')
    words = words_filtered

    # Repackage into tuples: wordstring -> (list of annos)
    data = {word: [d[word] for d in raw_data] for word in words}

    filtered_and_reformatted_data = {}

    skipped_words = 0
    skipped_senses = 0

    for wordform, annotator_wordforms in data.items():

        if any([not w.known for w in annotator_wordforms]):
            skipped_words += 1

            if filter_unknown == 'words' or filter_unknown == 'senses':
                continue

        known_senses = set.intersection(*[{s.wordnet_sense_id for s in w.senses if s.is_known}
                                          for w in annotator_wordforms])

        annotator_wordforms_reindexed = [w.senses_by_wordnet_index() for w in annotator_wordforms]

        # Repackage into tuples: sense_id -> gold_anno, test_anno
        for i, s in enumerate(annotator_wordforms_reindexed):
            if i == 0:
                continue
            assert set(s.keys()) == set(annotator_wordforms_reindexed[0].keys())

        word_data = {}
        for wordnet_sense_id in annotator_wordforms_reindexed[0].keys():

            if wordnet_sense_id not in known_senses:
                skipped_senses += 1
                if filter_unknown == 'senses':
                    continue

            word_data[wordnet_sense_id] = [a[wordnet_sense_id] for a in annotator_wordforms_reindexed]

        filtered_and_reformatted_data[wordform] = word_data
        # Compute metrics

    # info(f'{skipped_words} skipped words and an additional {skipped_senses} skipped senses')

    # data_2 is: word -> [wordnet sense -> (gold standard, test)]
    results = {}
    cluster_agreement_results = cluster_agreement(filtered_and_reformatted_data, num_annotators=num_annotators)
    for key, res in cluster_agreement_results.items():
        results[f'C:{key}'] = res
    attachment_agreement_results = attachment_agreement(filtered_and_reformatted_data, num_annotators=num_annotators)
    for key, res in attachment_agreement_results.items():
        results[f'A:{key}'] = res
    label_agreement_results = label_agreement(filtered_and_reformatted_data, num_annotators=num_annotators)
    for key, res in label_agreement_results.items():
        results[f'L:{key}'] = res
    return results


def format_frac(value):
    value = round(value, 2)
    value = "{:.2f}".format(value)
    value = value[1:]  # Remove 0
    value = "${}$".format(value)
    return value

def format_frac_simple(value):
    return round(value, 2)

def format_perc(value):
    value = round(value, 2)
    value = "{:.2f}".format(value)
    value = value[2:]  # Remove 0.
    value = "${}$".format(value)
    return value


def main():
    annotators = ['annotator01', 'annotator02', 'annotator03', 'author']

    info(f'Computing results for {annotators}')

    info('Loading Annotation')
    raw_annotations = {
        annotator_id: open_pickle(f'bin/collection/output/{annotator_id}.pkl') for annotator_id in annotators
    }

    queue_ids = ['overlaps:1', 'overlaps:2', 'overlaps:3']
    inter_words = set()
    for queue_id in queue_ids:
        inter_words.update({itm.split(':')[0] for itm in open_json('data/collection/queues.json')[queue_id]})
    assert len(inter_words) == 100

    inter_data = {}
    intra_data_before = {}
    intra_data_after = {}

    for annotator_id, raw_annotation in raw_annotations.items():

        inter_data[annotator_id] = {}
        intra_data_before[annotator_id] = {}
        intra_data_after[annotator_id] = {}

        # Get intra data after
        for q, d in raw_annotation.items():
            if ':i' in q:
                for k, v in d.items():
                    intra_data_after[annotator_id][k] = v

        # Get inter data and intra before
        for q, d in raw_annotation.items():
            if q == 'screener':
                continue
            if ':i' not in q:
                for k, v in d.items():
                    if k in inter_words:
                        inter_data[annotator_id][k] = v
                    if k in intra_data_after[annotator_id].keys():
                        intra_data_before[annotator_id][k] = v

    # Build combinations of data for testing
    datas = []
    for annotator_id in annotators:
        if annotator_id == 'author':
            continue
        datas.append((f'Intra ({annotator_id})', [intra_data_before[annotator_id], intra_data_after[annotator_id]]))

    datas.append(('Inter (macro-average)', list(inter_data.values())))
    for anno1, anno2 in itertools.combinations(range(1, len(annotators)+1), 2):
        anno1_id = annotators[anno1-1]
        anno2_id = annotators[anno2-1]

        datas.append((f'Inter ({anno1_id}+{anno2_id})', [inter_data[anno1_id], inter_data[anno2_id]]))

    all_results = {}

    for name, data in datas:

        for d in data:
            assert len(d) == 100

        info(name)
        all_results[name] = full_compare(raw_data=data)

    info('Meaning intras')
    list_intra_results = defaultdict(list)
    for experiment_name, results in all_results.items():
        if 'Intra' in experiment_name:
            for result_label, result in results.items():
                list_intra_results[result_label].append(result)
    all_results['Intra (micro-average)'] = {lab: np.mean(results2) if all([not (r is None or math.isnan(r)) for r in results2]) else None for lab, results2 in list_intra_results.items()}

    info('Meaning inters')
    list_inter_results = defaultdict(list)
    for experiment_name, results in all_results.items():
        if 'Inter' in experiment_name and 'macro' not in experiment_name:
            for result_label, result in results.items():
                list_inter_results[result_label].append(result)
    all_results['Inter (micro-average)'] = {lab: np.mean(results2) if all([not (r is None or math.isnan(r)) for r in results2]) else None for lab, results2 in list_inter_results.items()}

    info('Filtering to only results that matter')
    all_results = {
        'Inter': all_results['Inter (macro-average)'],
        'Intra': all_results['Intra (micro-average)'],
    }

    print('CLUSTERING AGREEMENT:')
    print('\\toprule & ARI \\\\ \\midrule')
    for name, results in all_results.items():
        print(f"{name} & {format_frac(results['C:collapsed_mets:ari'])} \\\\")

    print('LABEL AGREEMENT:')
    print(f''' \\toprule
     &            & \multicolumn{{3}}{{c}}{{Percentage}} & \multicolumn{{3}}{{c}}{{Fleiss' $\\kappa$}} \\\\
     &            & \\textit{{All}} & \\textit{{AC}} & \\textit{{AH}} & \\textit{{All}} & \\textit{{AC}} & \\textit{{AH}} \\\\ \\midrule''')
    for name, results in all_results.items():
        print(f'''\multirow{{4}}{{*}}{{\\rotatebox[origin=c]{{90}}{{{name}}}}} 
        & Prot./      & {format_perc(results["L:prototype:percent"])} & & & {format_frac(results["L:prototype:fleiss"])} \\\\
        & Metap.\     & {format_perc(results["L:metaphor:percent"])} & {format_perc(results["L:metaphor|prototype:percent"])} & {format_perc(results["L:metaphor|attachment:percent"])} & {format_frac(results["L:metaphor:fleiss"])} &  {format_frac(results["L:metaphor|prototype:fleiss"])}  & {format_frac(results["L:metaphor|attachment:fleiss"])}  \\\\
        & Meton.\     & {format_perc(results["L:metonymy:percent"])}  & {format_perc(results["L:metonymy|prototype:percent"])} & {format_perc(results["L:metonymy|attachment:percent"])} & {format_frac(results["L:metonymy:fleiss"])} & {format_frac(results["L:metonymy|prototype:fleiss"])}  & {format_frac(results["L:metonymy|attachment:fleiss"])}  \\\\
        & All         & {format_perc(results["L:all:percent"])} & {format_perc(results["L:all|prototype:percent"])} & {format_perc(results["L:all|attachment:percent"])} & {format_frac(results["L:all:fleiss"])} & {format_frac(results["L:all|prototype:fleiss"])} & {format_frac(results["L:all|attachment:fleiss"])}  \\\\ \\midrule''')

    print('ATTACHMENT AGREEMENT:')
    print('''\\toprule
    & \\multicolumn{2}{c}{Unlabelled} & \\multicolumn{2}{c}{Labelled} \\\\ 
    & \\textit{All} & \\textit{AC} & \\textit{All} & \\textit{AC} \\\\ \\midrule''')
    for name, results in all_results.items():
        print(
            f'{name} & {format_perc(results["A:all:uuas"])} & {format_perc(results["A:agreed_core:uuas"])} & {format_perc(results["A:all:ulas"])} & {format_perc(results["A:agreed_core:ulas"])} \\\\')

if __name__ == "__main__":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        main()
