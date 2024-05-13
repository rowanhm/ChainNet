from collections import defaultdict

from python.datatypes.sense_label import SenseLabel


class WordForm:

    def __init__(self, word_string, is_known, annotator_id, annotation_time, senses, annotation_date, start_time=None, end_time=None):
        self.word_string = word_string
        self.known = is_known
        self.annotation_time = annotation_time
        self.start_time = start_time
        self.end_time = end_time
        self.annotator_id = annotator_id
        self.annotation_date = annotation_date

        self.senses = sorted(senses, key=lambda x: x.position)
        self.sense_dict = {sense.sense_id: sense for sense in self.senses}

        for sense in self.senses:
            sense.wordform = self
            if not sense.is_virtual:
                sense.word_string = sense.get_wordnet_sense().name()
            else:
                sense.word_string = sense.wordform.word_string

    def senses_by_wordnet_index(self):
        output = defaultdict(dict)
        for sense in self.senses:

            if sense.is_virtual:
                continue
            wordnet_id = sense.wordnet_sense_id
            assert wordnet_id is not None

            output[wordnet_id][sense.label] = sense

        return output


    def get_latex_table(self, width='7cm'):
        output = f'''\\begin{{center}}\\resizebox{{
  \\ifdim\\width>\\columnwidth
    \\columnwidth
  \\else
    \\width
  \\fi}}{{!}}{{
\\begin{{tabular}}{{l m{{{width}}} cl}} \\toprule
\\multicolumn{{2}}{{l}}{{\\textbf{{Senses of \\word{{{self.word_string}}}}}}} & \\textbf{{Label}}  & \\textbf{{Features}} \\\\ \\midrule\n'''

        rows = []
        for sense in self.senses:
            rows.append(sense.get_latex_table_row())
        output += ' \\tabspace \n'.join(rows)

        output += '''\\bottomrule
\end{tabular} }
\end{center}'''
        return output

    def to_dict(self):
        assert [sense.position for sense in self.senses] == list(range(len(self.senses)))
        return {
            'wordform': self.word_string,
            'is_known': self.known,
            'annotator_id': self.annotator_id,
            'annotation_seconds': self.annotation_time,
            'senses': [sense.to_dict() for sense in self.senses]
        }

    def get_tikz(self, upward=True):
        output = '''\\begin{center} \\resizebox{%
      \\ifdim\\width>\\columnwidth
        \\columnwidth
      \\else
        \\width
      \\fi}{!}{
\\begin{tikzpicture}[derivation]\n'''

        horizontal_queue = [sense for sense in self.senses if sense.label == SenseLabel.PROTOTYPE]

        y_pos_to_last_sense = defaultdict(list)  # x_col -> sense_id
        y_pos_to_last_sense[-1].append((0, 0))
        seen_merged_senses = set()
        furthest_right_per_row = {}

        global furthest_right_node
        furthest_right = {'node': None,
                          'x': -1}

        def tikz_subsection(x_pos, y_pos, vertical_queue, horizontal_queue, x_shift=1, y_shift=1, node_width=3.5):
            if vertical_queue:
                # Move down a level
                next_chunk_1, next_x_1 = tikz_subsection(x_pos=x_pos, y_pos=y_pos+y_shift, vertical_queue=[],
                                                         x_shift=x_shift, y_shift=y_shift,
                                                         horizontal_queue=vertical_queue)
                # Then move across
                next_chunk_2, next_x_2 = tikz_subsection(x_pos=next_x_1, y_pos=y_pos, vertical_queue=[],
                                                         x_shift=x_shift, y_shift=y_shift,
                                                         horizontal_queue=horizontal_queue)
                return next_chunk_1 + next_chunk_2, next_x_2
            elif horizontal_queue:
                # Move across a node
                sense = horizontal_queue.pop(0)

                # Get connection
                if y_pos in y_pos_to_last_sense.keys():
                    position = 'right'
                    connecting_sense = f'{y_pos_to_last_sense[y_pos][-1]}'

                    prev_furthest_right = furthest_right_per_row[y_pos]
                    num_gaps = x_pos - prev_furthest_right - 1
                    assert num_gaps >= 0
                    if num_gaps > 0:
                        if sense.label == SenseLabel.METAPHOR:
                            # Below
                            position = 'at'
                            connecting_sense += f' -| {furthest_right["node"]}'
                        else:
                            connecting_sense += f' -| {furthest_right["node"]}.east'
                    # if num_gaps > 0:
                    #     extra_side = f'{num_gaps*(node_width+.5+.3) + .5}cm'
                    # else:
                    #     extra_side = None
                else:
                    position = 'above'
                    connecting_sense = y_pos_to_last_sense[y_pos-1][-1]
                    # extra_side = None

                if position != "at":
                    position_code = f'[{position} =of {connecting_sense}]'
                else:
                    position_code = f'at ({connecting_sense})'
                node = sense.get_tikz_box(position_code=position_code, width=f'{node_width}cm')
                y_pos_to_last_sense[y_pos].append(sense.sense_id)
                furthest_right_per_row[y_pos] = x_pos

                # Update furthest right
                if x_pos > furthest_right["x"]:
                    furthest_right["x"] = x_pos
                    furthest_right["node"] = sense.sense_id

                # node = sense.get_tikz_box(self, right_sense, x_step=x_shift, pos_y=y_pos)
                if sense.label == SenseLabel.METAPHOR:
                    edge = f'\\draw[metaphor] ({sense.parent.sense_id}) -| ({sense.sense_id});\n'
                elif sense.label == SenseLabel.METONYMY:
                    edge = f'\\draw[association] ({sense.parent.sense_id}) to [bend left=-45] ({sense.sense_id});\n'
                else:
                    assert sense.label == SenseLabel.PROTOTYPE
                    # edge = f'\\draw[start] ({x_pos}, {y_pos+y_shift}) to ({sense.sense_id});\n'
                    root_id = sense.sense_id + "_root"
                    edge = f'\\path let \\p1 = ({sense.sense_id}) in node[shape=coordinate] ({root_id}) at (\\x1,{0}) {{}};\n\\draw[start] ({root_id}) to ({sense.sense_id});\n'

                # If it is split draw a box around them
                if sense.is_mixed:
                    assert sense.sense_id not in seen_merged_senses
                    seen_merged_senses.add(sense.sense_id)

                    if "B" in sense.sense_id:
                        other_half = sense.sense_id.replace('B', 'A')  #if 'B' in sense.sense_id else sense.sense_id.replace('A', 'B')
                        assert other_half in seen_merged_senses
                        edge += f"\\draw[split] ($({other_half}.south west) + (-0.15, -0.15)$)  rectangle ($({sense.sense_id}.north east) + (0.15, 0.2cm+0.3cm)$);\n"

                vertical_queue = list(sense.get_metaphorical_children())
                horizontal_queue = list(sense.get_associated_children()) + horizontal_queue
                if not vertical_queue:
                    # Shift right
                    x_pos += x_shift
                next_chunk, next_x = tikz_subsection(x_pos=x_pos, y_pos=y_pos, vertical_queue=vertical_queue,
                                                          horizontal_queue=horizontal_queue)

                return node + edge + next_chunk, next_x
            else:
                # Both are empty
                return '', x_pos

        tikz_text, _ = tikz_subsection(x_pos=0, y_pos=0, y_shift=1 if upward else -1,
                                       vertical_queue=[], horizontal_queue=horizontal_queue)
        output += tikz_text

        output += '''\\end{tikzpicture} }
\\end{center}'''
        return output
