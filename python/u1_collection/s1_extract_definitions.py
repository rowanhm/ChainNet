import glob
import itertools
import os
import string
import xml.etree.ElementTree as ET
from collections import defaultdict

from nltk.corpus import wordnet as wn
from nltk.corpus.reader import WordNetError

from python.common.common import info, warn, flatten, save_pickle
from python.datatypes.annotated_string import AnnotatedString

assert wn.get_version() == '3.0'

alphabet = set(list(string.ascii_uppercase+string.ascii_lowercase))


def strip_and_reformat(tokens, first_token_start):
    output_tokens = []
    for (token, sense, start_index, end_index) in tokens:
        if sense is not None:
            output_tokens.append((start_index-first_token_start, end_index-first_token_start, sense))
    return output_tokens


def add_offsets(tokens, raw_string):
    raw_string = raw_string.lower()
    current_offset = 0
    failed = False
    annotated_tokens = []
    for (token, sense) in tokens:
        token = token.lower()
        end_offset = current_offset + len(token)
        while raw_string[current_offset:end_offset] != token:
            current_offset += 1
            end_offset += 1
            if end_offset > len(raw_string):
                # Does not align
                failed = True
                break
        if failed:
            return [], False
        annotated_tokens.append((token, sense, current_offset, end_offset))
        current_offset = end_offset
    return annotated_tokens, True


def get_anno(root):
    senses = set()
    for id in root.findall('id'):
        sense = id.attrib['sk']
        to_attempt = [sense, sense.replace('%3', '%5')]
        for sense_id in to_attempt:
            try:
                senses.add(wn.lemma_from_key(sense_id).key())
                break
            except (WordNetError, ValueError, KeyError):
                continue
    if id.attrib['lemma'] != 'purposefully ignored':
        assert len(senses) >= 1, f"{id.attrib['id']} has {len(senses)} annotations"  # One annotation per word
        sense = senses.pop()  # Picks a random annotation if there are multiple
    else:
        # not actually annotated
        sense = None
    return sense


def process_sentence(sentence_xml, collocation_dict=None):

    if collocation_dict is None:
        collocation_dict = {}

    children = [child for child in sentence_xml]

    # First pass - filter multiple collocations
    previous_collocation = None
    for i, child in enumerate(children):
        if child.tag == 'cf':
            collocation = child.attrib['coll']
            if ',' in collocation:
                collocations = collocation.split(',')

                # First, try and make it the same as the preceding token
                if previous_collocation in collocations:
                    collocation = previous_collocation
                    child.attrib['coll'] = collocation
                else:
                    jump = 1
                    while i+jump < len(children)-1:
                        next_child = children[i+jump]
                        if next_child.tag == 'cf':
                            next_collocation = next_child.attrib['coll']
                            if ',' not in next_collocation:
                                if next_collocation in collocations:
                                    collocation = next_collocation
                                    child.attrib['coll'] = collocation
                                break
                            else:
                                next_collocations = next_collocation.split(',')
                                if next_collocations == collocations:
                                    # Continue to the one after
                                    jump += 1
                                    continue
                                else:
                                    break
                        else:
                            break

                    if ',' in collocation:
                        # Last hurrah - if it has an annotation use that
                        globs = child.findall('glob')
                        for glob in globs:
                            glob_coll = glob.attrib['coll']
                            if glob_coll in collocations:
                                collocation = glob_coll
                                child.attrib['coll'] = collocation
                                break

                    if ',' in collocation:
                        # As a last resort, choose randomly
                        collocation = set(collocations).pop()
                        child.attrib['coll'] = collocation

            previous_collocation = collocation

    tokens = []

    for child in children:
        tag = child.tag
        if tag == 'wf':

            annotation = child.attrib['tag']
            if annotation in {'man', 'auto'}:
                sense = get_anno(child)
                text = child.findall('id')[-1].tail
            else:
                assert annotation in {'un', 'ignore'}
                sense = None
                text = child.text
            tokens.append((text, sense))
            assert text.strip() != '', child.attrib['id']

        elif tag == 'cf':
            collocation = child.attrib['coll']

            globs = child.findall('glob')
            assert child.attrib['tag'] in {'un', 'ignore'}, child.attrib['id']

            # Add globs:
            for glob in globs:
                glob_coll = glob.attrib['coll']
                if glob.attrib['tag'] in {'man', 'auto'}:
                    collocation_dict[glob_coll] = get_anno(glob)
                else:
                    assert glob.attrib['tag'] in {'un', 'ignore'}
                    if glob_coll not in collocation_dict.keys():
                        collocation_dict[glob_coll] = None

            assert collocation in collocation_dict.keys(), f"{child.attrib['id']} with collocation ID {collocation}"
            if len(globs) > 0:
                text = globs[-1].tail
            else:
                text = child.text
            assert text.strip() != '', child.attrib['id']

            sense = collocation_dict[collocation]

            tokens.append((text, sense))
        elif tag == 'aux':
            tokens.extend(process_sentence(child, collocation_dict))
        elif tag == 'mwf':
            tokens.extend(process_sentence(child, collocation_dict))
        else:
            rendition = child.attrib['rend']
            if rendition == 'dq':
                quote = '"'
            else:
                assert rendition == 'sq'
                quote = "'"
            assert tag == 'qf'
            tokens.extend([(quote, None)]+process_sentence(child, collocation_dict)+[(quote, None)])

    return tokens


def main():
    definitions = {}  # synset -> annotated_tokens
    examples = defaultdict(list)  # synset -> [annotated_tokens]
    synonym_dict = {}

    for file in sorted(glob.glob(os.path.join('data/collection/WordNet-3.0/glosstag/merged/*.xml'))):

        info(f'Processing {file}')

        tree = ET.parse(file)
        root = tree.getroot()

        for synset_xml in root.findall('synset'):
            synset_offset = synset_xml.attrib['ofs']
            synset_pos = synset_xml.attrib['pos']

            # Get tokens and raw text
            glosses = synset_xml.findall('gloss')
            assert len(glosses) > 0
            raw_string = None
            sentences = []
            for gloss in glosses:
                description = gloss.attrib['desc']
                if description == 'orig':
                    assert raw_string == None
                    raw_strings = gloss.findall('orig')
                    assert len(raw_strings) == 1
                    raw_string = raw_strings[0].text.replace('`', "'")

                elif description == 'wsd':
                    assert sentences == []
                    definition_found = False
                    for i, sentence in enumerate(gloss):
                        tokens = process_sentence(sentence)
                        if len(tokens) == 0:
                            continue
                        sentence_type = sentence.tag
                        if sentence_type == 'classif':
                            assert tokens[0][0] == '('
                            assert tokens[-1][0] == ')'
                            if len(tokens) == 2:
                                continue
                            # Definitions are formatted differently
                            domain = tokens[1:-1]
                            sentences.append((domain, 'Domain'))
                        elif sentence_type == 'def':
                            sentences.append((tokens, 'Definition'))
                        elif sentence_type == 'aux':
                            sentences.append((tokens, 'Auxiliary'))
                        else:
                            assert sentence_type == 'ex', sentence.attrib['id']
                            sentences.append((tokens, 'Example'))

            assert raw_string is not None
            assert len(sentences) > 0
            codes = {s[1] for s in sentences}
            no_def = False
            if not 'Definition' in codes:
                info(f'No definition in {synset_xml.attrib["id"]}')
                no_def = True
                sentences = [([], 'Definition')] + sentences

            # Combine into a single token streak, finding out indicies which strip dividing ';'s
            # all_orderings = generate_orderings(sentences)

            # Filter end punctuation
            sentences_filtered = []
            for (sentence, code) in sentences:
                # Swap special character
                sentence = [(token.replace('`', "'"), sense) for (token, sense) in sentence]
                if len(sentence) > 0:
                    if sentence[-1][0] in {';', ':', ','}:
                        sentences_filtered.append((sentence[:-1], code))
                    else:
                        sentences_filtered.append((sentence, code))
                else:
                    sentences_filtered.append((sentence, code))
            sentences = sentences_filtered

            for number_of_attempts, ordering in enumerate(itertools.permutations(sentences)):  # TODO make this faster
                # Elements of ordering are (tokens, code) tuples
                tokens_flat = flatten([o[0] for o in ordering])

                annotated_tokens, success = add_offsets(tokens_flat, raw_string)
                if success:
                    break

            if not success:
                warn(f'Failed to align:\n{raw_string}\n{"+".join([t[0] for t in flatten([o[0] for o in sentences])])}')

            for (token, sense, start_index, end_index) in annotated_tokens:
                assert token.lower() == raw_string[start_index:end_index].lower()

            assert len(flatten([s[0] for s in ordering])) == len(annotated_tokens)
            annotated_tokens_index = 0

            # Collect them back into sentences
            all_sentences = []
            all_codes = []
            for (tokens, code) in ordering:
                number_of_tokens = len(tokens)
                tokens = annotated_tokens[annotated_tokens_index:annotated_tokens_index+number_of_tokens]
                annotated_tokens_index += number_of_tokens
                all_sentences.append(tokens)
                all_codes.append(code)
            assert annotated_tokens_index == len(annotated_tokens)

            # First, add back brackets around domain if present
            if 'Domain' in all_codes:
                domain_index = 0
                if all_codes[0] != 'Domain':
                    assert all_codes[1] == 'Domain'
                    domain_index = 1
                domain_sentence = all_sentences[domain_index]
                domain_start = domain_sentence[0][2]
                domain_end = domain_sentence[-1][3]
                if domain_start > 0:
                    if raw_string[domain_start-1:domain_start] == '(':
                        domain_sentence = [('(', None, domain_start-1, domain_start)] + domain_sentence
                if domain_end < len(raw_string):
                    if raw_string[domain_end:domain_end+1] == ')':
                        domain_sentence.append((')', None, domain_end, domain_end+1))

                # Next, merge domain
                if all_codes[0] == 'Domain':
                    assert all_codes[1] == 'Definition'
                    all_codes = all_codes[1:]
                else:
                    assert all_codes[1] == 'Domain'
                    assert all_codes[0] == 'Definition'
                    all_codes = all_codes[:1] + all_codes[2:]
                all_sentences[1] = domain_sentence + all_sentences[1]
                all_sentences = all_sentences[1:]
            assert 'Domain' not in all_codes

            # Now, merge all aux left
            while 'Auxiliary' in all_codes:
                aux_index = 0
                while all_codes[aux_index] != 'Auxiliary':
                    aux_index += 1
                if aux_index > 0:
                    # Add the aux and split it in
                    all_sentences[aux_index-1] = all_sentences[aux_index-1] + all_sentences[aux_index]
                    all_codes = all_codes[:aux_index] + all_codes[aux_index+1:]
                    all_sentences = all_sentences[:aux_index] + all_sentences[aux_index+1:]
                else:
                    all_sentences[1] = all_sentences[0] + all_sentences[1]
                    all_sentences = all_sentences[1:]
                    all_codes = all_codes[1:]

            assert all_codes[0] == 'Definition'
            assert sum([1 if code == 'Definition' else 0 for code in all_codes]) == 1
            assert 'Auxiliary' not in all_codes
            assert len(all_codes) == len(all_sentences)

            # Merge consecutive tokens with the same annotation
            for j in range(len(all_sentences)):
                sentence = all_sentences[j]
                found_merge = True
                while found_merge:
                    found_merge = False
                    for i in range(len(sentence)-1):
                        (token_1, sense_1, start_index_1, end_index_1) = sentence[i]
                        (token_2, sense_2, start_index_2, end_index_2) = sentence[i+1]
                        if sense_1 is not None and sense_1 == sense_2:
                            if raw_string[end_index_1:start_index_2] in {' ', '-', ''}:
                                found_merge = True
                                sentence[i] = (raw_string[start_index_1:end_index_2], sense_1, start_index_1, end_index_2)
                                sentence = sentence[:i+1] + sentence[i+2:]
                                all_sentences[j] = sentence
                                break

            # Get synonyms
            synonyms = set()
            terms = synset_xml.findall('terms')
            assert len(terms) == 1
            terms = terms[0]
            for term in terms.findall('term'):
                synonyms.add(term.text)

            synset_nltk = wn.synset_from_pos_and_offset(synset_pos, int(synset_offset))
            synset = synset_nltk.name()

            expected_synonyms = {(lemma.name().replace('_', ' '), lemma.key()) for lemma in synset_nltk.lemmas()}
            assert synonyms == {k for k in [e[0] for e in expected_synonyms]}, f"Synonym mismatch: {synonyms} != {[e[0] for e in expected_synonyms]}"

            synonyms_additional_e_removed = {(s[:-1], key) for (s, key) in expected_synonyms if s[-1].lower() == 'e'}
            synonyms_additional = synonyms_additional_e_removed.union(expected_synonyms)
            synonyms_additional_or = {(s.replace('or', 'our'), key) for (s, key) in synonyms_additional if 'or' in s.lower()}
            synonyms_additional_z = {(s.replace('z', 's'), key) for (s, key) in synonyms_additional if 'z' in s.lower()}
            synonyms_additional_hyphen_space = {(s.replace('-', ' '), key) for (s, key) in synonyms_additional if '-' in s.lower()}
            synonyms_additional_hyphen_none = {(s.replace('-', ''), key) for (s, key) in synonyms_additional if '-' in s.lower()}

            synonyms_additional = synonyms_additional.union(synonyms_additional_or)
            synonyms_additional = synonyms_additional.union(synonyms_additional_z)
            synonyms_additional = synonyms_additional.union(synonyms_additional_hyphen_space)
            synonyms_additional = synonyms_additional.union(synonyms_additional_hyphen_none)

            for code, sentence in zip(all_codes, all_sentences):
                start_index = sentence[0][2]
                end_index = sentence[-1][3]
                raw_text = raw_string[start_index:end_index]
                sentence_stripped = strip_and_reformat(sentence, start_index)
                sentence_object = AnnotatedString(raw_text, sentence_stripped)
                if code == 'Definition':
                    if no_def:
                        info(f'Definition assigned: {sentence_object.to_string()}')
                    assert synset not in definitions.keys()
                    definitions[synset] = sentence_object
                else:
                    assert code == 'Example'
                    synsets = {wn.lemma_from_key(sense).synset().name() for (start, end, sense) in sentence_stripped}
                    if synset not in synsets:
                        success = False
                        # Attempt to find it automatically
                        for synonym, sense_key in sorted(synonyms_additional, key=lambda x: len(x[0]), reverse=True):  # Go in reverse length order so that nested synonyms hit longest first
                            if synonym.lower() in raw_text.lower():
                                start_index = raw_text.lower().find(synonym.lower())
                                end_index = start_index + len(synonym)

                                # Expand outwards
                                while True:
                                    if start_index > 0:
                                        if raw_text[start_index-1] in alphabet:
                                            start_index -= 1
                                        else:
                                            break
                                    else:
                                        break
                                while True:
                                    if end_index < len(raw_text)+1:
                                        if raw_text[end_index] in alphabet:
                                            end_index += 1
                                        else:
                                            break
                                    else:
                                        break

                                sentence_stripped.append((start_index, end_index, sense_key))
                                sentence_object = AnnotatedString(raw_text, sentence_stripped)
                                info(f'Added {synset} ({sense_key}; {synonyms}) annotation to example: {sentence_object.to_string()}')
                                success = True
                                break
                        if not success:
                            warn(f'Synset {synset} ({synonyms}) not found in example: {sentence_object.to_string()}')

                    examples[synset].append(sentence_object)

            expected_synonyms = set([lemma.name().replace('_', ' ') for lemma in wn.synset(synset).lemmas()])
            assert synonyms == expected_synonyms, f'Expected {expected_synonyms} but got {synonyms}'
            synonym_dict[synset] = synonyms

    info('Saving')
    for synset in wn.all_synsets():
        synset_id = synset.name()
        assert synset_id in definitions.keys()

    save_pickle('bin/collection/concepts_to_definitions.pkl', definitions)
    save_pickle('bin/collection/example_sentences_princeton.pkl', examples)


if __name__ == "__main__":
    main()
