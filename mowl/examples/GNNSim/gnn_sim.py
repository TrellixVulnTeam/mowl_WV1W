#!/usr/bin/env python

import click as ck
import numpy as np
import pandas as pd
import pickle
import gzip
import os
import sys
import logging
import yaml



logging.basicConfig(level=logging.INFO)   
sys.path.insert(0, '')
sys.path.append('../../../')

from mowl.datasets.base  import PathDataset
from mowl.gnn_sim.model import GNNSim

@ck.command()
@ck.option(
    '--config', '-c', help="Configuration file in config/")

def main(config):
    logging.info(f"Number of cores detected: {os.cpu_count()}")


    params = parseYAML(config)

    graph_method = params["general"]["graph-gen-method"]
    ontology = params["general"]["ontology"]
    
    n_hidden = params["rgcn-params"]["n-hidden"]
    dropout = params["rgcn-params"]["dropout"]
    lr = params["rgcn-params"]["lr"]
    num_bases = params["rgcn-params"]["num-bases"]
    batch_size = params["rgcn-params"]["batch-size"]
    epochs = params["rgcn-params"]["epochs"]
    normalize =  params["rgcn-params"]["normalization"]
    self_loop =  params["rgcn-params"]["self-loop"]
    seed =  params["rgcn-params"]["seed"]
    
    file_params = params["files"]


    ds = PathDataset(ontology, "", "")
        
    model = GNNSim(ds, # dataset
                   n_hidden,
                   dropout,
                   lr,
                   num_bases,
                   batch_size,
                   epochs,
                   graph_generation_method = graph_method,
                   normalize = normalize,
                   self_loop = self_loop,
                   seed = seed,
                   file_params = file_params
                   )


    model.train()
    model.evaluate()


def parseYAML(yaml_path):
    with open(yaml_path, 'r') as f:
        params = yaml.load(f, Loader=yaml.FullLoader)

    return params

if __name__ == '__main__':
    main()