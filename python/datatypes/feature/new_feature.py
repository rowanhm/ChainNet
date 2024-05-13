from python.datatypes.feature_label import FeatureLabel


class NewFeature:

    def __init__(self, feature_id, sense, feature_string):
        self.feature_id = feature_id
        self.sense = sense
        self.label = FeatureLabel.NEW
        self.feature_string = feature_string

    def get_feature_string(self):
        return self.feature_string

    def to_dict(self):
        return {
            'feature_id': self.feature_id,
            'feature_string': self.get_feature_string(),
            'label': self.label.value,
            'source_feature_id': None,
            'source_feature_string': None,
        }