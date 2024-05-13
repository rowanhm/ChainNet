from python.common.global_variables import device
import numpy as np
from ufal.chu_liu_edmonds import chu_liu_edmonds


def decode_edmunds_labelless(score_matrix):
    # Input: a floating point score tensor [num_senses+1 x num_senses+1 x 3]
    # Output: a boolean connection tensor [num_senses+1 x num_senses+1 x 3]

    score_matrix = score_matrix.detach().cpu().numpy()

    # Nullify edges that don't exist
    score_matrix[:, 0] = np.nan
    np.fill_diagonal(score_matrix, np.nan)

    # Get tree
    heads, tree_score = chu_liu_edmonds(score_matrix.astype(np.double).transpose())
    heads = heads[1:]  # exclude root

    return heads

def lst_tns_to_dev(list_tensor):
    return [y.to(device=device) for y in list_tensor]


def simple_collate_fn(data):

    wordforms, x, y_heads, y_labels = zip(*data)
    return wordforms, lst_tns_to_dev(x), lst_tns_to_dev(y_heads), lst_tns_to_dev(y_labels)


def initialise_model(model_name, embeddings):
    if model_name == 'contextless_label':
        from python.u3_parsing.models.label.contextless_label import ContextlessLabel
        model = ContextlessLabel(sense_embedding_dict=embeddings)
    elif model_name == 'biaffine_label':
        from python.u3_parsing.models.label.biaffine_label import BiaffineLabel
        model = BiaffineLabel(sense_embedding_dict=embeddings)
    else:
        assert model_name == 'biaffine_edge'
        from python.u3_parsing.models.edge.biaffine_edge import BiaffineEdge
        model = BiaffineEdge(sense_embedding_dict=embeddings)
    return model