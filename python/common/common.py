import csv
import json
import os
import pickle
import logging
import bz2
import re

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)


def flatten(list_of_lists):
    flat_list = [item for sublist in list_of_lists for item in sublist]
    return flat_list


def info(text):
    logging.info(text)


def warn(text):
    logging.warning(text)


def get_file_list(directory, end='', start=''):
    # create a list of file and sub directories
    # names in the given directory
    look_end = len(end)
    look_start = len(start)
    file_list = os.listdir(directory)
    all_files = list()
    # Iterate over all the entries
    for entry in file_list:
        # Create full path
        full_path = os.path.join(directory, entry)
        # If entry is a directory then get the list of files in this directory
        if os.path.isdir(full_path):
            all_files = all_files + get_file_list(full_path, end=end, start=start)
        elif full_path[len(full_path)-look_end:] == end and \
                os.path.basename(full_path)[:look_start] == start:
            all_files.append(full_path)

    return all_files


def generate_param_string(params, delimiter='_'):
    keys = sorted([k for k in params.keys()])
    values = []
    for k in keys:
        value = params[k]
        if type(value) is dict:
            value = generate_param_string(value, delimiter='*')
        values += [str(value)]
    return delimiter.join(values)


def open_csv_as_dict(file, key_col, val_col, delimiter=None):
    dict_csv_list = open_dict_csv(file, delimiter=delimiter)
    output = dict()
    for entry in dict_csv_list:
        key = entry[key_col]
        val = entry[val_col]
        if key in output.keys():
            assert output[key] == val  # Otherwise collision
        output[key] = val
    return output


def open_csv(file):
    ftype = file[-4:]
    delimiter = ''
    if ftype == '.tsv':
        delimiter = '\t'
    elif ftype == '.csv':
        delimiter = ','
    else:
        # update
        print("Invalid file extension: {}".format(file))
        exit()
    all_lines = []
    with open(file, 'r') as csv_file:
        for line in csv.reader(csv_file, delimiter=delimiter):
            all_lines += [line]
    return all_lines


def open_dict_csv(file, delimiter=None, encoding=None):
    ftype = file[-4:]
    if delimiter is None:
        if ftype == '.tsv':
            delimiter = '\t'
        elif ftype == '.csv':
            delimiter = ','
        else:
            # update
            print("Invalid file extension: {}".format(file))
            exit()
    all_lines = []
    with open(file, 'r', encoding=encoding) as csv_file:
        for line in csv.DictReader(csv_file, delimiter=delimiter):
            all_lines += [line]
    return all_lines


def save_list_csv(file, all_lines):
    ftype = file[-4:]
    delimiter = ''
    if ftype == '.tsv':
        delimiter = '\t'
    elif ftype == '.csv':
        delimiter = ','
    else:
        # update
        print("Invalid file extension: {}".format(file))
        exit()

    with open(file, 'w') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=delimiter)
        for row in all_lines:
            csv_writer.writerow(row)


def save_csv(file, all_lines, encoding=None):
    ftype = file[-4:]
    delimiter = ''
    if ftype == '.tsv':
        delimiter = '\t'
    elif ftype == '.csv':
        delimiter = ','
    else:
        # update
        print("Invalid file extension: {}".format(file))
        exit()
    with open(file, 'w', encoding=encoding) as csv_file:
        dict_writer = csv.DictWriter(csv_file, fieldnames=all_lines[0].keys(), delimiter=delimiter,
                                     quoting=csv.QUOTE_NONE, escapechar='\\')
        dict_writer.writeheader()
        dict_writer.writerows(all_lines)
    return


def save_json(file, dictionary):
    with open(file, "w") as fp:
        json.dump(dictionary, fp, indent=4)


def open_json(file):
    with open(file, "r") as fp:
        dictionary = json.load(fp)
    return dictionary


def strip_surrounding_whitespace(string):
    return string.lstrip().rstrip()


def open_pickle(file):
    with open(file, 'rb') as fp:
        data = pickle.load(fp)
    return data


def save_pickle(file, data):
    with open(file, 'wb') as fp:
        pickle.dump(data, fp)


def open_pickle_bz2(file):
    with bz2.open(file, 'rb') as fp:
        data = pickle.load(fp)
    return data


def save_pickle_bz2(file, data):
    with bz2.open(file, 'wb') as fp:
        pickle.dump(data, fp)


def save_text_lines(file, lines):
    if len(lines) > 1:
        lines = [line + '\n' for line in lines[:-1]] + [lines[-1]]
    with open(file, 'w') as fp:
        fp.writelines(lines)


def save_text_block(file, block):
    with open(file, 'w') as fp:
        fp.write(block)

def safe_lemma_from_key(word, sense_id):
    from nltk.corpus.reader.wordnet import WordNetError
    from nltk.corpus import wordnet as wn
    try:
        sense_obj = wn.lemma_from_key(sense_id)
    except WordNetError:
        sense_obj = None
        synsets = wn.synsets(word)
        for synset in synsets:
            synset_senses = synset.lemmas()
            for sense in synset_senses:
                if sense.key() == sense_id:
                    sense_obj = sense
                    break
            if sense_obj is not None:
                break
    assert sense_obj is not None
    return sense_obj

def open_text_lines(file):
    with open(file, 'r') as fp:
        lines = fp.readlines()
    lines_stripped = [line.rstrip() for line in lines]
    return lines_stripped

def open_text_block(file):
    with open(file, 'r') as fp:
        block = fp.read()
    return block


def tex_escape(text):
    """
        :param text: a plain text message
        :return: the message escaped to appear correctly in LaTeX
    """
    conv = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\^{}',
        '\\': r'\textbackslash{}',
        '<': r'\textless{}',
        '>': r'\textgreater{}',
    }
    regex = re.compile('|'.join(re.escape(str(key)) for key in sorted(conv.keys(), key = lambda item: - len(item))))
    return regex.sub(lambda match: conv[match.group()], text)

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def open_chainnet():
    return open_json('data/chainnet.json')['content']
