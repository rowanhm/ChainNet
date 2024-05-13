from python.datatypes.feature_label import FeatureLabel


class KeptFeature:

    def __init__(self, feature_id, sense, source_feature):
        self.feature_id = feature_id
        self.sense = sense
        self.label = FeatureLabel.KEPT
        self.source_feature = source_feature

    def get_feature_string(self):
        return self.source_feature.get_feature_string()

    def to_dict(self):
        return {
            'feature_id': self.feature_id,
            'feature_string': self.get_feature_string(),
            'label': self.label.value,
            'source_feature_id': self.source_feature.feature_id,
            'source_feature_string': self.get_feature_string(),
        }