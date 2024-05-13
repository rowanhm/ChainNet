from typing import List, Tuple
from simple_colors import *


class AnnotatedString:

    def __init__(self, string: str, senses: List[Tuple[int, int, str]]):
        # senses is list of (start_offset, end_offset, sense_id)
        self.string = string
        self.senses = senses

    def to_string(self):
        output_string = self.string
        last_start_offset = len(output_string)
        for (start_offset, end_offset, sense_id) in sorted(self.senses, key=lambda x: x[1], reverse=True):
            if end_offset > last_start_offset:
                continue
            last_start_offset = start_offset
            output_string = output_string[:]
            output_string = output_string[:start_offset] + green(output_string[start_offset:end_offset].replace(' ', '_'), ['bold']) + output_string[end_offset:]
        return output_string

    def get_all_senses(self):
        return {sense for (start, end, sense) in self.senses}

    def to_dict(self):
        return {
            'string': self.string,
            'annotations': self.senses
        }
