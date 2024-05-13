import copy
import torch.nn as nn


class BaseModel(nn.Module):

    def __init__(self):
        super().__init__()
        self.train_collate_fn = None
        self.best_state_dict = copy.deepcopy(self.state_dict())

    def set_best(self):
        self.best_state_dict = copy.deepcopy(self.state_dict())

    def recover_best(self):
        self.load_state_dict(self.best_state_dict)