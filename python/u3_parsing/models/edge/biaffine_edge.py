import numpy as np
import torch
import torch.nn as nn

from python.common.global_variables import device, seed
from python.u3_parsing.models.base_model import BaseModel
from python.u3_parsing.models.biaffine import Biaffine
from python.u3_parsing.models.mlp import MLP
from python.u3_parsing.utils.training_utils import decode_edmunds_labelless

torch.manual_seed(seed=seed)


class BiaffineEdge(BaseModel):

    def __init__(self, sense_embedding_dict):
        super().__init__()

        loss_code = 'entropy'

        self.embedding_size = len(list(sense_embedding_dict.values())[0])

        sense_embedding_matrix = np.array([sense_embedding_dict[i] for i in range(len(sense_embedding_dict))])
        self.embedding = torch.tensor(sense_embedding_matrix, requires_grad=False).float().cpu()

        assert self.embedding.shape == (len(sense_embedding_dict), self.embedding_size)

        self.encoding_size = self.embedding_size  # 500
        dropout = .33
        self.head_encoder = MLP(n_in=self.embedding_size, n_out=self.encoding_size, dropout=dropout).to(device=device)
        self.dep_encoder = MLP(n_in=self.embedding_size, n_out=self.encoding_size, dropout=dropout).to(device=device)

        self.biaff = Biaffine(n_in=self.encoding_size, n_out=1)

        if loss_code == 'entropy':
            self.batch_loss = self.entropy_batch_loss
            self.loss_func = nn.CrossEntropyLoss(reduction='none')
        elif loss_code == 'structural':
            self.batch_loss = self.structural_batch_loss
        else:
            self.batch_loss = self.structural_approx_batch_loss

    def forward(self, x):
        # Input: a list of sense indices [batch_size x num_senses]
        # Output: a score matrix [batch_size x num_senses+1 x num_senses+1 x 3]

        batch_size, max_num_senses = x.shape

        # Process to a list of sense embs [batch_size x num_senses x emb_size]
        embeddings = self.embedding[x.cpu()].to(device=device)

        # Calculate the root embedding
        embs_zeroed = embeddings.masked_fill((x == -1).unsqueeze(-1).repeat(1, 1, self.embedding_size), 0)
        sizes = (x != -1).sum(dim=1)
        embs_meaned = embs_zeroed.sum(dim=1) / sizes.unsqueeze(-1).repeat(1, self.embedding_size)

        # Add the root to the embeddings
        embeddings_with_root = torch.cat((embs_meaned.unsqueeze(1), embeddings), dim=1)

        # Split [both are batch_size x num_senses + 1 x enc_size
        head_encodings = self.head_encoder(embeddings_with_root)
        dep_encodings = self.dep_encoder(embeddings_with_root)

        # Compute scores
        scores = self.biaff(x=head_encodings, y=dep_encodings)

        # Filter diagonal
        diag_filter = torch.eye(max_num_senses + 1, dtype=bool).to(device=device)
        diag_filter = diag_filter.unsqueeze(0).repeat(batch_size, 1, 1)
        scores = scores.masked_fill(diag_filter, float('-inf'))

        # Filter root
        scores[:, :, 0] = float('-inf')

        # Filter based on number of senses
        pad_mask = torch.full((batch_size, max_num_senses + 1), fill_value=True).to(device=device)
        pad_mask[:, 1:] = (x != -1)
        pad_mask = torch.logical_not(torch.logical_and(pad_mask.unsqueeze(-1).repeat(1, 1, max_num_senses + 1),
                                                       pad_mask.unsqueeze(-2).repeat(1, max_num_senses + 1, 1)))
        scores = scores.masked_fill(pad_mask, float('-inf'))

        return scores

    def entropy_batch_loss(self, batch_data):
        (wordforms, sense_sets, all_heads, all_labels) = batch_data
        sense_sets = torch.nn.utils.rnn.pad_sequence(sense_sets, padding_value=-1, batch_first=True)
        heads = torch.nn.utils.rnn.pad_sequence(all_heads, padding_value=-1, batch_first=True)

        score_matrices = self.forward(sense_sets)
        predictions = score_matrices[:, :, 1:]
        batch_size, num_heads, num_senses = predictions.shape

        # Flatten batch
        scores = predictions.transpose(-2, -1).reshape(batch_size * num_senses, num_heads)
        heads_flat = heads.reshape(batch_size * num_senses)

        # Remove all padding
        indices = torch.where(heads_flat != -1)
        heads_flat_filtered = heads_flat[indices]
        scores_filtered = scores[indices]

        # Compute loss
        # log_scores = torch.log_softmax(scores_filtered, dim=-1)
        losses = self.loss_func(scores_filtered, heads_flat_filtered)

        return losses

    def predict(self, batch_data, top_n=False):

        (wordforms, sense_sets, _, _) = batch_data
        sense_sets = torch.nn.utils.rnn.pad_sequence(sense_sets, padding_value=-1, batch_first=True)

        all_heads = []
        sense_lens = torch.sum((sense_sets != -1), dim=-1)

        score_matrices = self.forward(sense_sets)

        for (score_matrix, num_senses) in zip(score_matrices, sense_lens):
            size = num_senses + 1

            score_matrix_cropped = score_matrix[:size, :size]

            pred_heads = decode_edmunds_labelless(score_matrix_cropped)

            if top_n:
                top_n_preds = [pred_heads]
                for child, head in enumerate(pred_heads):
                    score_matrix_dupe = score_matrix_cropped.clone()
                    score_matrix_dupe[head, child + 1] = float('-inf')
                    new_pred_heads = decode_edmunds_labelless(score_matrix_dupe)
                    top_n_preds.append(new_pred_heads)

                assert len(top_n_preds) == size
                all_heads.append(top_n_preds)
            else:
                all_heads.append(pred_heads)

        return all_heads, []
