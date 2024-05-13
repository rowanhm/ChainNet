import numpy as np
import torch
from torch import sigmoid

from python.common.common import flatten
from python.common.global_variables import device, seed
from python.u3_parsing.models.base_model import BaseModel
from python.u3_parsing.models.biaffine import Biaffine
from python.u3_parsing.models.mlp import MLP

import torch.nn as nn

torch.manual_seed(seed=seed)


class BiaffineLabel(BaseModel):

    def __init__(self, sense_embedding_dict):
        super().__init__()

        self.loss_func = nn.BCELoss(reduction='none')

        embedding_size = len(list(sense_embedding_dict.values())[0])

        sense_embedding_matrix = np.array([sense_embedding_dict[i] for i in range(len(sense_embedding_dict))])
        self.embedding = torch.tensor(sense_embedding_matrix, requires_grad=False).float().cpu()
        assert self.embedding.shape == (len(sense_embedding_dict), embedding_size)

        self.encoding_size = 100
        dropout = .33
        self.head_encoder = MLP(n_in=embedding_size, n_out=self.encoding_size, dropout=dropout).to(device=device)
        self.dep_encoder = MLP(n_in=embedding_size, n_out=self.encoding_size, dropout=dropout).to(device=device)

        self.biaff = Biaffine(n_in=self.encoding_size, n_out=1, bias_y=True)

    def forward(self, child_senses):
        # Process to a list of sense embs [batch_size x num_senses x emb_size]
        embs = self.embedding[child_senses.cpu()].to(device=device)
        dep_embeddings = self.dep_encoder(embs)
        head_embeddings = self.head_encoder(embs)

        # Score each sense
        label_logits = self.biaff(x=head_embeddings, y=dep_embeddings)
        return sigmoid(label_logits)

    def batch_loss(self, batch_data):
        wordforms, child_senses, y_heads, y_labels = batch_data

        child_senses_padded = torch.nn.utils.rnn.pad_sequence(child_senses, padding_value=-1, batch_first=True)

        label_scores = self.forward(child_senses_padded)

        # NB this can be optimised by removing loop
        extracted_pairs = [
            [(label_scores[batch, child, head - 1], label - 1) for child, (head, label) in enumerate(zip(heads, labels))
             if label > 0] for batch, (heads, labels) in enumerate(zip(y_heads, y_labels))]
        preds, gold = zip(*flatten(extracted_pairs))

        preds = torch.stack(list(preds))
        gold = torch.stack(list(gold))
        # Filter core senses

        losses = self.loss_func(preds, gold.float())

        return losses

    def predict(self, batch_data):
        all_labels = []
        (wordforms, x_tensor, y_heads, y_labels) = batch_data
        x_tensor = torch.nn.utils.rnn.pad_sequence(x_tensor, padding_value=-1, batch_first=True)

        label_scores = self.forward(x_tensor)

        sense_lens_tensor = torch.sum((x_tensor != -1), dim=-1)

        for score_matrix, num_senses in zip(label_scores, sense_lens_tensor):
            score_matrix = score_matrix[:num_senses, :num_senses]

            predictions = torch.add(torch.round(score_matrix), 1)
            assert torch.all(torch.logical_or(predictions == 1, predictions == 2))

            predictions_full = torch.zeros(size=(num_senses, num_senses + 1)).long()
            predictions_full[:, 1:] = predictions

            assert predictions_full.shape == (num_senses, num_senses + 1)

            all_labels.append(predictions_full.cpu().numpy())

        return [], all_labels
