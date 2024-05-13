from python.datatypes.feature_label import FeatureLabel


class ModifiedFeature:

    def __init__(self, feature_id, sense, source_feature, edited_feature_string):
        self.feature_id = feature_id
        self.sense = sense
        self.label = FeatureLabel.MODIFIED
        self.source_feature = source_feature
        self.edited_feature_string = edited_feature_string

    def get_feature_string(self):
        return self.edited_feature_string

    def to_dict(self):
        return {
            'feature_id': self.feature_id,
            'feature_string': self.get_feature_string(),
            'label': self.label.value,
            'source_feature_id': self.source_feature.feature_id,
            'source_feature_string': self.source_feature.get_feature_string()
        }