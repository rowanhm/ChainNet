import numpy as np
import torch

from python.common.global_variables import device, seed
import torch.nn as nn
from python.u3_parsing.models.base_model import BaseModel

torch.manual_seed(seed=seed)


class ContextlessLabel(BaseModel):

    def __init__(self, sense_embedding_dict):
        super().__init__()

        embedding_size = len(list(sense_embedding_dict.values())[0])
        sense_embedding_matrix = np.array([sense_embedding_dict[i] for i in range(len(sense_embedding_dict))])
        self.embedding = torch.tensor(sense_embedding_matrix, requires_grad=False).float().cpu()
        assert self.embedding.shape == (len(sense_embedding_dict), embedding_size)

        self.label_predictor = nn.Linear(in_features=embedding_size, out_features=3).to(device=device)
        self.loss_func = nn.CrossEntropyLoss(reduction='none')

    def forward(self, x):
        # Input: a list of sense indices [batch_size x num_senses]
        # Output: a list of label logits [batch_size x num_senses x 3]

        # Process to a list of sense embs [batch_size x num_senses x emb_size]
        embeddings = self.embedding[x.cpu()].to(device=device)

        # Score each sense as core (s)
        label_logits = self.label_predictor(embeddings)

        return label_logits

    def batch_loss(self, batch_data):
        wordforms, child_senses, y_heads, y_labels = batch_data

        child_senses_flat = torch.cat(child_senses)
        labels_flat = torch.cat(y_labels)

        child_senses = child_senses_flat.to(device=device)
        labels = labels_flat.to(device=device)

        predictions = self.forward(child_senses)
        losses = self.loss_func(predictions, labels)

        return losses

    def predict(self, batch_data):
        # Input is batch_size * num_senses
        # Return is batch_size * num_senses * num_senses+1
        all_labels = []

        (wordforms, x_tensor, y_heads, y_labels) = batch_data
        x_tensor = torch.nn.utils.rnn.pad_sequence(x_tensor, padding_value=-1, batch_first=True)

        predictions = self.forward(x_tensor)
        sense_lens_tensor = torch.sum((x_tensor != -1), dim=-1)

        for (prediction, num_senses) in zip(predictions, sense_lens_tensor):
            predictions_cropped = prediction[:num_senses, :]
            pred_labels = torch.argmax(predictions_cropped, dim=-1)

            # Force a core if there is no core
            if not torch.any(pred_labels == 0):
                core_sense = torch.argmax(predictions_cropped[:, 0])
                pred_labels[core_sense] = 0
                assert torch.any(pred_labels == 0)

            # Reshape:
            pred_labels = pred_labels.unsqueeze(-1).expand(-1, num_senses + 1)
            # pred_labels[:, 0] = 0  # Manually interject if core.

            assert pred_labels.shape == (num_senses, num_senses + 1)
            all_labels.append(pred_labels.cpu().numpy())

        return [], all_labels  # Check shape
