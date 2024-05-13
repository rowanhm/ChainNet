import os

import torch
from sklearn.metrics import accuracy_score
from torch.utils.data import DataLoader

from python.common.common import info, open_pickle, warn, flatten
from python.common.global_variables import device, BATCH_SIZE, EARLY_STOPPING, TESTING, seed, RESTART_WITH_DIVISOR, \
    LEARNING_RATE, BETAS
from python.u3_parsing.utils.training_utils import simple_collate_fn, initialise_model

torch.manual_seed(seed=seed)


info('Loading embeddings')
embeddings = open_pickle('bin/parsing/sensembert_embeddings.pkl')

if not TESTING:
    train = open_pickle('bin/parsing/data/train.pkl')
    dev = open_pickle('bin/parsing/data/dev.pkl')
else:
    warn('Training mode')
    dev = open_pickle('bin/parsing/data/dev.pkl')[:1]
    train = dev

def get_connections(senses, heads):
    connections = set()
    root = torch.tensor([-1]).to(device=device)
    for s, h in zip(senses, heads):
        assert len(s) == len(h)
        rooted_s = torch.cat((root, s), dim=0)
        assert len(rooted_s) == len(h) + 1
        head_senses = rooted_s[h]
        for h, c in zip(head_senses.tolist(), s.tolist()):
            connections.add(frozenset({h, c}))
    return connections

info(f'Training on {device}')

for model_name in ['biaffine_edge', 'biaffine_label', 'contextless_label']:

    info(f'Training {model_name}')

    model = initialise_model(model_name, embeddings)
    lr = LEARNING_RATE
    betas = BETAS

    info('Initialising training setup')
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, betas=betas)

    dev_loader = DataLoader(dev, batch_size=BATCH_SIZE, collate_fn=simple_collate_fn)
    train_loader = DataLoader(train, shuffle=True, batch_size=BATCH_SIZE, collate_fn=simple_collate_fn)


    def get_dev_loss():
        dev_loss = torch.tensor([]).to(device=device)
        for batch_data in dev_loader:
            dev_loss = torch.cat((dev_loss, model.batch_loss(batch_data)))
        return dev_loss.mean()

    def get_dev_acc():
        if '_label' not in model_name:
            return 'N/A'

        all_pairs = []
        for batch_data in dev_loader:
            pred_labels = model.predict(batch_data)[1]
            (_, _, all_heads, all_labels) = batch_data
            pairs = [[(pred_labels[batch][child][head], label) for child, (head, label) in
                      enumerate(zip(heads.tolist(), labels.tolist()))] for batch, (heads, labels) in
                      enumerate(zip(all_heads, all_labels))]
            all_pairs.extend(pairs)

        preds, gold = zip(*flatten(pairs))
        preds = list(preds)
        gold = list(gold)
        return accuracy_score(gold, preds)


    def get_dev_uuas():
        if '_edge' not in model_name:
            return 'N/A'

        gold_connections = set()
        pred_connections = set()

        for batch_data in dev_loader:
            (_, senses, heads, _) = batch_data
            pred_heads = model.predict(batch_data)[0]

            gold_connections.update(get_connections(senses, heads))
            pred_connections.update(get_connections(senses, pred_heads))

        assert len(gold_connections) == len(pred_connections)
        uuas = len(gold_connections.intersection(pred_connections)) / len(gold_connections)
        return uuas


    # Calculating initial loss
    model.eval()
    info(f'Model parameters: {[p.shape for p in model.parameters()]}')

    dev_uuas = get_dev_uuas()
    dev_acc = get_dev_acc()
    best_dev_loss = get_dev_loss()
    model.set_best()

    info(f'Initial dev loss {best_dev_loss} | UUAS: {dev_uuas} | LAcc: {dev_acc}')

    info('Commencing training loop')
    epoch = 1
    stable_iterations = 0
    restarted = 0
    terminated = False
    while not terminated:

        info(f'[{restarted+1}/{RESTART_WITH_DIVISOR+1}] On epoch {epoch}')
        model.train()

        for step, batch_data in enumerate(train_loader):

            loss = model.batch_loss(batch_data).mean()
            assert loss >= 0

            # Process
            loss.backward()
            optimizer.step()

        # End of epoch
        epoch += 1

        # Calculate dev loss
        model.eval()
        dev_loss = get_dev_loss()
        dev_uuas = get_dev_uuas()
        dev_acc = get_dev_acc()

        # Check for early stopping
        if dev_loss < best_dev_loss:
            info(f'Dev loss: {dev_loss} | UUAS: {dev_uuas} | LAcc: {dev_acc} (improvement from {best_dev_loss})')

            stable_iterations = 0
            best_dev_loss = dev_loss
            model.set_best()
        else:
            # Stable
            stable_iterations += 1

            info(f'Dev loss: {dev_loss} | UUAS: {dev_uuas} | LAcc: {dev_acc} (stable {stable_iterations}/{EARLY_STOPPING})')

            if stable_iterations == EARLY_STOPPING:
                restarted += 1
                if restarted > RESTART_WITH_DIVISOR:
                    terminated = True
                else:
                    stable_iterations = 0
                    model.recover_best()
                    lr /= 10
                    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, betas=betas)

    info('Saving model')
    model.recover_best()
    torch.save(model.state_dict(), os.path.join(f'bin/parsing/models/{model_name}.pth'))

info('Training complete')
