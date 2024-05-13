from nltk.corpus.reader import WordNetError

from python.common.common import safe_lemma_from_key, warn
from python.datatypes.sense_label import SenseLabel
from nltk.corpus import wordnet as wn


class Sense:

    def __init__(self, sense_id, wordnet_sense_id, is_known, is_virtual, is_mixed, definition, label, position):

        self.sense_id = sense_id
        self.definition = definition
        self.wordform = None
        self.position = position

        self.is_known = is_known
        self.is_virtual = is_virtual
        self.is_mixed = is_mixed

        assert isinstance(label, SenseLabel)
        self.label = label

        self.parent = None
        self.children = set()

        self.wordnet_sense_id = wordnet_sense_id
        if wordnet_sense_id is not None:
            assert not is_virtual
        else:
            assert is_virtual

        self.features = []

    def is_conduit(self):
        if self.label == SenseLabel.METONYMY:
            # Then if ass child
            for child in self.children:
                if child.label == SenseLabel.METONYMY:
                    return True
        if self.label == SenseLabel.METAPHOR:
            # Then if met/ass child
            if len(self.children) > 0:
                return True
        return False

    def set_parent(self, sense):
        assert self.parent is None
        self.parent = sense
        sense.children.add(self)

    def add_feature(self, feature):
        if feature not in self.features:
            self.features.append(feature)

    def get_wordnet_sense(self):
        if not self.is_virtual:
            try:
                return wn.lemma_from_key(self.wordnet_sense_id)
            except WordNetError:
                warn(f'{self.wordnet_sense_id} not safe')
                return safe_lemma_from_key(self.wordform.word_string, self.wordnet_sense_id)
        else:
            return None

    def get_latex_table_row(self):
        return f'{self.get_latex_sense_id(index_label=True)} & {self.get_latex_definition()} & {self.get_latex_table_label()} & {self.get_latex_features()} \\\\'

    #def get_tikz_box(self, pos_x, pos_y, width='3.5cm'):
    #    return f'\\node[{self.label.value}_definition, text width={width}{", dashed" if self.is_virtual else ""}] ({self.sense_id}) at ({pos_x},{pos_y}) {{{self.get_latex_sense_id()} {self.get_latex_definition()}}};\n'

    def get_tikz_box(self, position_code, width='3.5cm'):

        return f'\\node[{self.label.value}{"conduit" if self.is_conduit() else ""}_definition, text width={width}{", dashed" if self.is_virtual else ""}] ({self.sense_id}) {position_code} {{{self.get_latex_sense_id(index_label=True)} {self.get_latex_definition()}}};\n'

    # def get_tikz_box(self, right_sense, x_step, pos_y, width='3.5cm'):
    #     return f'\\path let \\p1 = ({right_sense}.east) in node[{self.label.value}_definition, text width={width}{", dashed" if self.is_virtual else ""}] ({self.sense_id}) at (\\x1+{x_step},{pos_y}) {{{self.get_latex_sense_id()} {self.get_latex_definition()}}};\n'

    def to_dict(self):
        return {
            'sense_id': self.sense_id,
            'wordform': self.wordform.word_string,
            'definition': self.definition,
            'wordnet_sense_id': self.wordnet_sense_id,
            'wordnet_synset_id': wn.lemma_from_key(self.wordnet_sense_id).synset().name() if self.wordnet_sense_id is not None else None,
            'label': self.label.value,
            'child_of': None if self.label == SenseLabel.PROTOTYPE else self.parent.sense_id,
            'is_known': self.is_known,
            'is_virtual': self.is_virtual,
            'is_split': self.is_mixed,
            'features': [feature.to_dict() for feature in self.features]
        }

    def get_latex_sense_id(self, index_label=False):
        sense_id = self.sense_id
        if 'V' in sense_id:
            sense_id = f'\\text{"bf" if index_label else ""}{{{sense_id[0]}}}{sense_id[1:]}'
        elif 'A' in sense_id or 'B' in sense_id:
            sense_id = f'{sense_id[:-1]}\\text{"bf" if index_label else ""}{{{sense_id[-1]}}}'

        sense_id = f'{{{sense_id}}}'

        if index_label and not self.is_known:
            sense_id += "^\\textcolor{Red}{\\star}"

        sense_id = f'\\sense{"bf" if index_label else ""}{{{self.word_string}}}{{{sense_id}}}'

        return sense_id

    def get_latex_definition(self):
        latex_definition = self.definition.strip()

        # Italicise the synonyms
        if latex_definition[0] == '[':
            latex_definition_fragments = latex_definition[1:].split(']')
            if len(latex_definition_fragments) > 1:
                # Only italicise if it seems to fit
                synonyms = latex_definition_fragments[0].split(', ')
                latex_definition = '[' + ', '.join(
                    [f'\\synonym{{{synonym}}}' for synonym in synonyms]) + ']' + ']'.join(
                    latex_definition_fragments[1:])

        # Escape e.g.
        latex_definition = latex_definition.replace('e.g. ', 'e.g.\\ ')

        # Change quote marks
        latex_definition_split = latex_definition.split('"')
        latex_definition = latex_definition_split[0]
        for i, part in enumerate(latex_definition_split[1:]):
            if i % 2 == 0:
                latex_definition += '``'
            else:
                latex_definition += "''"
            latex_definition += part

        return latex_definition

    def get_latex_table_label(self):
        label = f'\\textcolor{{\\{self.label.value}colour}}{{\\{self.label.value}label}}'
        if self.label != SenseLabel.PROTOTYPE:
            if not self.is_conduit():
                label = f"\\makecell{{{label} \\\\ \\textcolor{{\\{self.label.value}colour}}{{(from {self.parent.get_latex_sense_id()})}}}}"
            else:
                label = f"\\makecell{{{label} \\\\ \\textcolor{{\\{self.label.value}colour}}{{(from {self.parent.get_latex_sense_id()})}} \\\\ \\textcolor{{\\conduitcolour}}{{+{{ }}\\conduitlabel}}}}"
        return label

    def get_latex_features(self):
        if len(self.features) == 0:
            return ''

        features_latex = []
        for feature in self.features:  # sorted(self.features, key=lambda x: x.feature_id):
            features_latex.append(f'\\{feature.label.value}feature{{{feature.get_feature_string()}}}')
        return '\makecell[l]{' + ' \\\\ '.join(features_latex) + '}'

    def get_metaphorical_children(self):
        return sorted([sense for sense in self.children if sense.label == SenseLabel.METAPHOR], key=lambda x: x.position)

    def get_associated_children(self):
        return sorted([sense for sense in self.children if sense.label == SenseLabel.METONYMY], key=lambda x: x.position)
