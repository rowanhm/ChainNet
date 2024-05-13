from collections import defaultdict

import numpy as np
from sklearn.metrics import adjusted_rand_score

from python.common.common import open_dict_csv, safe_lemma_from_key, info, open_pickle, flatten
from python.datatypes.sense_label import SenseLabel

info('Loading chainnet')
chainnet_data = open_pickle('bin/analysis/chainnet.pkl')

info('Finding basic statistics')
total_words = 0
total_senses = 0
virtual_senses = 0
mixed_senses = 0
metaphors = 0
metonymys = 0
for wordform, word_obj in chainnet_data.items():

    total_words += 1

    for sense in word_obj.senses:
        if sense.wordnet_sense_id:
            total_senses += 1

            if sense.label == SenseLabel.METAPHOR:
                metaphors += 1
            elif sense.label == SenseLabel.METONYMY:
                metonymys += 1

        if sense.is_virtual:
            virtual_senses += 1

        if sense.is_mixed and sense.label == SenseLabel.METAPHOR:
            mixed_senses += 1

info(f'Total words {total_words} covering {total_senses} senses')
info(f'{metaphors}:{metonymys} metaphor:metonymy ({metaphors/metonymys})')
info(f'{virtual_senses} Virtual and {mixed_senses} Mixed')

info('Processing historical homonymys')
data = open_dict_csv('data/analysis/within_pos_clusters.csv')

historical_homonyms_raw = defaultdict(set)
for datapoint in data:

    lemma = datapoint['lemma']
    wordform = lemma.split('.')[0]

    sense_id = datapoint['wn_sense']
    synset = safe_lemma_from_key(wordform, sense_id).synset()

    if synset.pos() != 'n':
        continue

    assert synset not in historical_homonyms_raw[lemma]
    historical_homonyms_raw[lemma].add(synset.name())

historical_homonyms = defaultdict(list)  # word -> list of sets of synset ids
for lemma, synsets in historical_homonyms_raw.items():
    wordform, pos, index = lemma.split('.')
    assert pos == 'noun'
    assert wordform.lower() == wordform
    historical_homonyms[wordform].append(synsets)

info('Processing cognitive homonymys')
cognitive_homonyms = defaultdict(list)
for wordform, word_obj in chainnet_data.items():

    clusters = []
    for sense in word_obj.senses:
        if sense.label == SenseLabel.PROTOTYPE:
            cluster = {sense.get_wordnet_sense().synset().name()}
            queue = list(sense.children)
            while queue:
                child = queue.pop()
                queue.extend(list(child.children))
                if child.wordnet_sense_id:
                    cluster.add(child.get_wordnet_sense().synset().name())

            clusters.append(cluster)

    assert len(set().union(*clusters)) == sum([len(c) for c in clusters])
    cognitive_homonyms[wordform] = clusters

    # # Get parents
    # parents = {}
    # for annotation in datapoint['ANNOTATION']:
    #     parents[annotation['SENSE_ID']] = annotation['HEAD']
    #
    # # get cluster
    # cluster_dict = defaultdict(set)
    # for annotation in datapoint['ANNOTATION']:
    #     sense_id = annotation['SENSE_ID']
    #
    #     synset = safe_lemma_from_key(wordform, sense_id).synset()
    #     assert synset.pos() == 'n'
    #
    #     # go to core of cluster
    #     parent_sense = sense_id
    #     while parents[parent_sense] is not None:
    #         parent_sense = parents[parent_sense]
    #
    #     cluster_dict[parent_sense].add(synset.name())
    #
    # for cluster in cluster_dict.values():
    #     cognitive_homonyms[wordform].append(cluster)

info('Filter to Overlap')
historical_homonyms_filtered = {}
cognitive_homonyms_filtered = {}
for wordform, historical_clusters in historical_homonyms.items():
    if wordform not in cognitive_homonyms.keys():
        continue

    cognitive_clusters = cognitive_homonyms[wordform]

    shared_concepts = (set().union(*historical_clusters)).intersection(set().union(*cognitive_clusters))
    if len(shared_concepts) <= 1:
        continue

    cognitive_clusters = [{c for c in cluster if c in shared_concepts} for cluster in cognitive_clusters]
    historical_clusters = [{c for c in cluster if c in shared_concepts} for cluster in historical_clusters]

    cognitive_clusters = [cluster for cluster in cognitive_clusters if len(cluster) > 0]
    historical_clusters = [cluster for cluster in historical_clusters if len(cluster) > 0]

    cognitive_homonyms_filtered[wordform] = cognitive_clusters
    historical_homonyms_filtered[wordform] = historical_clusters

cognitive_homonyms = cognitive_homonyms_filtered
historical_homonyms = historical_homonyms_filtered


def clusters_to_index_dict(clusters):
    output = {}
    for i, cluster in enumerate(clusters):
        for synset in cluster:
            assert synset not in output.keys()
            output[synset] = i
    return output


info('Comparing')
scores = []
cluster_counts_historical = defaultdict(list)
cluster_counts_cognitive = defaultdict(list)
num_words = 0
num_disagree = 0
cases_cog_finer = []
cases_hist_finer = []
cases_incompatible = []

for wordform, historical_clusters in historical_homonyms.items():
    cognitive_clusters = cognitive_homonyms[wordform]
    num_words += 1

    historical_indices = clusters_to_index_dict(historical_clusters)
    cognitive_indices = clusters_to_index_dict(cognitive_clusters)

    cognitive_list = []
    historical_list = []
    for key, historical_itm in historical_indices.items():
        cognitive_itm = cognitive_indices[key]
        cognitive_list.append(cognitive_itm)
        historical_list.append(historical_itm)

    # Cluster agreement score
    score = adjusted_rand_score(cognitive_list, historical_list)
    scores.append(score)

    # Counts
    num_senses = len(cognitive_indices)
    cluster_counts_historical[num_senses].append(len(historical_clusters))
    cluster_counts_cognitive[num_senses].append(len(cognitive_clusters))

    if {frozenset(cluster) for cluster in historical_clusters} != {frozenset(cluster) for cluster in cognitive_clusters}:
        num_disagree += 1
        equiv_indices_historical = []
        equiv_indices_cognitive = []

        for cluster in historical_clusters:
            cluster_indicies = set()
            for sense in cluster:
                cog_cluster_id = cognitive_indices[sense]
                cluster_indicies.add(cog_cluster_id)
            equiv_indices_historical.append(cluster_indicies)

        for cluster in cognitive_clusters:
            cluster_indicies = set()
            for sense in cluster:
                hist_cluster_id = historical_indices[sense]
                cluster_indicies.add(hist_cluster_id)
            equiv_indices_cognitive.append(cluster_indicies)

        if len(set().union(*equiv_indices_historical)) == sum([len(c) for c in equiv_indices_historical]):
            # One cluster is indexed in multiple
            cases_cog_finer.append(wordform)
        elif len(set().union(*equiv_indices_cognitive)) == sum([len(c) for c in equiv_indices_cognitive]):
            cases_hist_finer.append(wordform)
        else:
            # They are incompatible
            cases_incompatible.append(wordform)

info(f'V-measure: {np.mean(scores)}')
info(f'{num_disagree} / {num_words} words had disagreements ({num_disagree/num_words})')

info(f'{len(cases_cog_finer)} / {num_disagree} had cognitive homonymy where there was historical polysemy ({len(cases_cog_finer)/num_disagree})')
example_word = cases_cog_finer.pop()
info(f'e.g. {example_word}: Cognitive: {cognitive_homonyms[example_word]} / Historical: {historical_homonyms[example_word]}')

info(f'{len(cases_hist_finer)} / {num_disagree} had cognitive polysemy where there was historical homonymy ({len(cases_hist_finer)/num_disagree})')
example_word = cases_hist_finer.pop()
info(f'e.g. {example_word}: Cognitive: {cognitive_homonyms[example_word]} / Historical: {historical_homonyms[example_word]}')

info(f'{len(cases_incompatible)} / {num_disagree} were incompatible ({len(cases_incompatible)/num_disagree})')
example_word = cases_incompatible.pop()
info(f'e.g. {example_word}: Cognitive: {cognitive_homonyms[example_word]} / Historical: {historical_homonyms[example_word]}')

for i in range(2, 11):
    info(f'Mean number of clusters for {i} senses: Historical {np.mean(cluster_counts_historical[i])} / Cognitive {np.mean(cluster_counts_cognitive[i])}')
# Filter to only senses in common

cluster_counts_all_historical = flatten(cluster_counts_historical.values())
cluster_counts_all_cognitive = flatten(cluster_counts_cognitive.values())
info(f'Total mean number of clusters: Historical {np.mean(cluster_counts_all_historical)} / Cognitive {np.mean(cluster_counts_all_cognitive)}')
