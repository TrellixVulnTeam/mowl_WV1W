from mowl.model import Model
from mowl.graph.util import gen_factory
import pandas as pd
import click as ck
import os
import pickle as pkl
import dgl
from dgl import nn as dglnn
import torch as th
import numpy as np
from torch import nn
from torch.nn import functional as F
from torch import optim
from .baseRGCN import BaseRGCN
from sklearn.metrics import roc_curve, auc, matthews_corrcoef
from torch.utils.data import DataLoader, IterableDataset
from dgl.nn.pytorch import RelGraphConv
import random
from ray import tune


class GNNSim(Model):
    def __init__(self,
                 dataset,
                 n_hidden,
                 dropout,
                 learning_rate,
                 num_bases,
                 batch_size,
                 epochs,
                 graph_generation_method = "taxonomy", #Default: generate graph taxonomy
                 normalize = False,
                 self_loop = False,
                 min_edges = 0, #Only takes the relation types in which the number of triples is greater than min_edges. If 0 then takes all the relation types
                 seed = -1,
                 file_params = None #Dictionary of data file paths corresponding to the graph generation method (NEEDS REFACTORING)
                 ):
        super().__init__(dataset)
        self.n_hidden = n_hidden
        self.dropout = dropout
        self.learning_rate = learning_rate
        self.num_bases = None if num_bases < 0 else num_bases
        self.batch_size =  batch_size
        self.epochs = epochs
        self.graph_generation_method = graph_generation_method
        self.normalize = normalize
        self.self_loop = self_loop
        self.min_edges = min_edges
        self.file_params = file_params
        
        if seed>=0:
            th.manual_seed(seed)
            np.random.seed(seed)
            random.seed(seed)

        

    def train(self, checkpoint_dir = None, tuning= False):

        g, annots, prot_idx, norm = self.load_graph_data()

        device = "cpu"


        if not norm == None:
            norm = norm.repeat(1, self.batch_size).reshape(-1).view(-1,1)
            norm = norm.to(device)

        print(f"Num nodes: {g.number_of_nodes()}")
        print(f"Num edges: {g.number_of_edges()}")
    
        num_rels = len(g.canonical_etypes)

        if self.num_bases is None:
            self.num_bases = num_rels

        g = dgl.to_homogeneous(g)
        
        num_nodes = g.number_of_nodes()
    
        feat_dim = 2
        loss_func = nn.BCELoss()

        train_df, val_df, _ = self.load_data()

        model = PPIModel(feat_dim, num_rels, self.num_bases, num_nodes, self.n_hidden, self.dropout)

        if th.cuda.is_available():
            device = "cuda:0"
            if th.cuda.device_count() > 1:
                model = nn.DataParallel(model)
            
        annots = th.FloatTensor(annots).to(device)


        model.to(device)
        optimizer = optim.Adam(model.parameters(), lr=self.learning_rate, weight_decay=1e-2)

        if checkpoint_dir:
            model_state, optimizer_state = th.load(
                os.path.join(checkpoint_dir, "checkpoint"))
            model.load_state_dict(model_state)
            optimizer.load_state_dict(optimizer_state)

        train_labels = th.FloatTensor(train_df['labels'].values).to(device)
        val_labels = th.FloatTensor(val_df['labels'].values).to(device)
    
        train_data = GraphDataset(g, train_df, train_labels, annots, prot_idx)
        val_data = GraphDataset(g, val_df, val_labels, annots, prot_idx)
    
        train_set_batches = self.get_batches(train_data, self.batch_size)
        val_set_batches = self.get_batches(val_data, self.batch_size)
    
        best_roc_auc = 0

        for epoch in range(self.epochs):
            epoch_loss = 0
            model.train()

            with ck.progressbar(train_set_batches) as bar:
                for iter, (batch_g, batch_feat, batch_labels) in enumerate(bar):
                    logits = model(batch_g.to(device), batch_feat, norm)

                    labels = batch_labels.unsqueeze(1).to(device)
                    loss = loss_func(logits, labels)
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
                    epoch_loss += loss.detach().item()

                epoch_loss /= (iter+1)
        
            model.eval()
            val_loss = 0
            preds = []
            labels = []
            with th.no_grad():
                optimizer.zero_grad()
                with ck.progressbar(val_set_batches) as bar:
                    for iter, (batch_g, batch_feat, batch_labels) in enumerate(bar):
                        
                        logits = model(batch_g.to(device), batch_feat, norm)
                        lbls = batch_labels.unsqueeze(1).to(device)
                        loss = loss_func(logits, lbls)
                        val_loss += loss.detach().item()
                        labels = np.append(labels, lbls.cpu())
                        preds = np.append(preds, logits.cpu())
                    val_loss /= (iter+1)

            roc_auc = self.compute_roc(labels, preds)
            if not tuning:
                if roc_auc > best_roc_auc:
                    best_roc_auc = roc_auc
                    th.save(model.state_dict(), self.file_params["output_model"])
                print(f'Epoch {epoch}: Loss - {epoch_loss}, \tVal loss - {val_loss}, \tAUC - {roc_auc}')

            else:
                with tune.checkpoint_dir(epoch) as checkpoint_dir:
                    path = os.path.join(checkpoint_dir, "checkpoint")
                    th.save((model.state_dict(), optimizer.state_dict()), path)

                tune.report(loss=(val_loss), auc=roc_auc)
        print("Finished Training")


    def evaluate(self, model=None):

        device = "cpu"
        g, annots, prot_idx, norm = self.load_graph_data()

        if not norm == None:
            norm = norm.repeat(1, self.batch_size).reshape(-1).view(-1,1)
            norm = norm.to(device)
        
        num_nodes = g.number_of_nodes()
        print(f"Num nodes: {g.number_of_nodes()}")
    
        annots = th.FloatTensor(annots).to(device)
        num_rels = len(g.canonical_etypes)

        if self.num_bases is None:
            self.num_bases = num_rels

        g = dgl.to_homogeneous(g)

        feat_dim = 2
        loss_func = nn.BCELoss()


        _,_, test_df = self.load_data()
        test_labels = th.FloatTensor(test_df['labels'].values).to(device)
    
        test_data = GraphDataset(g, test_df, test_labels, annots, prot_idx)
    
        test_set_batches = self.get_batches(test_data, self.batch_size)

        if model == None:
            model = PPIModel(feat_dim, num_rels, self.num_bases, num_nodes, self.n_hidden, self.dropout)
            model.load_state_dict(th.load(self.file_params["output_model"]))
        model.to(device)
        model.eval()
        test_loss = 0

        preds = []
        all_labels = []
        with th.no_grad():
            with ck.progressbar(test_set_batches) as bar:
                for iter, (batch_g, batch_feat, batch_labels) in enumerate(bar):
                    logits = model(batch_g.to(device), batch_feat, norm)
                    labels = batch_labels.unsqueeze(1).to(device)
                    loss = loss_func(logits, labels)
                    test_loss += loss.detach().item()
                    preds = np.append(preds, logits.cpu())
                    all_labels = np.append(all_labels, labels.cpu())
                test_loss /= (iter+1)

        roc_auc = self.compute_roc(all_labels, preds)
        print(f'Test loss - {test_loss}, \tAUC - {roc_auc}')

        return test_loss, roc_auc

    def compute_roc(self, labels, preds):
    # Compute ROC curve and ROC area for each class
        fpr, tpr, _ = roc_curve(labels.flatten(), preds.flatten())
        roc_auc = auc(fpr, tpr)

        return roc_auc

    def get_batches(self, dataset, batch_size):
        return DataLoader(dataset, batch_size=batch_size, shuffle=False, collate_fn=self.collate, drop_last=True)
    
    def collate(self, samples):
        # The input `samples` is a list of pairs
        #  (graph, label).
        graphs, features, labels = map(list, zip(*samples))
        batched_graph = dgl.batch(graphs)
        return batched_graph, th.cat(features, dim=0), th.tensor(labels)



    def load_data(self):
         train_df, val_df, test_df = self.load_ppi_data()
         return train_df, val_df, test_df

    def load_ppi_data(self):
        train_df = pd.read_pickle(self.file_params["train_inter_file"])
        index = np.arange(len(train_df))
        np.random.seed(seed=0)
        np.random.shuffle(index)
        train_df = train_df.iloc[index[:10000]]

        valid_df = pd.read_pickle(self.file_params["valid_inter_file"])
        index = np.arange(len(valid_df))
        np.random.seed(seed=0)
        np.random.shuffle(index)
        valid_df = valid_df.iloc[index[:1000]]
        
        test_df = pd.read_pickle(self.file_params["test_inter_file"])
        index = np.arange(len(test_df))
        np.random.seed(seed=0)
        np.random.shuffle(index)
        test_df = test_df.iloc[index[:1000]]
        return train_df, valid_df, test_df

    def load_graph_data(self):

        data_file = self.file_params["data_file"]

        parser = gen_factory(self.graph_generation_method, self.dataset)

        edges = parser.parseOWL()

        nodes = list({str(e.src()) for e in edges}.union({str(e.dst()) for e in edges}))
        if self.self_loop:
            edges += [Edge(node, "id", node) for node in nodes]


        if self.normalize:
            node_edge = {}
            for edge in edges:
                rel = str(edge.rel())
                dst = edge.dst()
                if (rel, dst) not in node_edge:
                    node_edge[(rel, dst)] = 0
                node_edge[(rel, dst)] += 1

            node_edge = {k: 1/v for k, v in node_edge.items()}

            norm = [node_edge[(str(edge.rel()), edge.dst())] for edge in edges]

            norm = th.Tensor(norm).view(-1, 1)
        else:
            norm = None

        node_idx = {v: k for k, v in enumerate(nodes)}
        g = {}

        for edge in edges:
            go_class_1 = edge.src()
            rel = str(edge.rel())
            go_class_2 = edge.dst()

            key = ("node", rel, "node")

            if not key in g:
                g[key] = set()

            node1 = node_idx[go_class_1]
            node2 = node_idx[go_class_2]

            g[key].add((node1, node2))

        
        g = {k: list(v) for k, v in g.items() if len(v) > self.min_edges}

        rels = {k:len(v) for k, v in g.items()}
        print("Edges in graph:\n", rels)
        g = dgl.heterograph(g)

        
        num_nodes = g.number_of_nodes()
          

        
        prot_idx = {}

        with open(data_file, 'r') as f:
            rows = [line.strip('\n').split('\t') for line in f.readlines()]
            
            annotations = np.zeros((num_nodes, len(rows)), dtype=np.float32)
            
            for i, row  in enumerate(rows):
                prot_id = row[0]
                prot_idx[prot_id] = i
                for go_id in row[1:]:
                    if go_id in node_idx:
                        annotations[node_idx[go_id], i] = 1
        return g, annotations, prot_idx, norm


    
class RGCN(BaseRGCN):

         def build_hidden_layer(self, idx):
             act = F.relu if idx < self.num_hidden_layers - 1 else None
             return RelGraphConv(self.h_dim, self.h_dim, self.num_rels, "basis",
                self.num_bases, activation=act, self_loop=True,
                dropout=self.dropout)

         
class PPIModel(nn.Module):

    def __init__(self, h_dim, num_rels, num_bases, num_nodes, n_hid, dropout):
        super().__init__()

        self.h_dim = h_dim
        self.num_rels = num_rels
        self.num_bases = None if num_bases < 0 else num_bases
        self.num_nodes = num_nodes

        print(f"Num rels: {self.num_rels}")
        print(f"Num bases: {self.num_bases}")

        self.rgcn = RGCN(self.h_dim,
                              self.h_dim, 
                              self.h_dim, 
                              self.num_rels, 
                              self.num_bases,
                              num_hidden_layers=n_hid, 
                              dropout=dropout,
                              use_self_loop=False, 
                              use_cuda=True
                              )


        self.fc = nn.Linear(self.num_nodes*self.h_dim, 1) 

    def forward(self, g, features, norm):

        edge_type = g.edata[dgl.ETYPE].long()

        x = self.rgcn(g, features, edge_type, norm)

        x = th.flatten(x).view(-1, self.num_nodes*self.h_dim)
        return th.sigmoid(self.fc(x))


    

class GraphDataset(IterableDataset):

    def __init__(self, graph, df, labels, annots, prot_idx):
        self.graph = graph
        self.annots = annots
        self.labels = labels
        self.df = df
        self.prot_idx = prot_idx

    def get_data(self):
        for i, row in enumerate(self.df.itertuples()):
            p1, p2 = row.interactions
            label = self.labels[i].view(1, 1)
            if p1 not in self.prot_idx or p2 not in self.prot_idx:
                continue
            pi1, pi2 = self.prot_idx[p1], self.prot_idx[p2]

            feat = self.annots[:, [pi1, pi2]]

            yield (self.graph, feat, label)

    def __iter__(self):
        return self.get_data()

    def __len__(self):
        return len(self.df)



def node_norm_to_edge_norm(g, node_norm):
    g = g.local_var()
    # convert to edge norm
    g.ndata['norm'] = node_norm
    g.apply_edges(lambda edges : {'norm' : edges.dst['norm']})
    return g.edata['norm']
