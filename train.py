'''
Copyright <2019> <COPYRIGHT Pingcheng Zhang>

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

##============================================================================##

'''
import numpy as np
import pandas as pd
import pickle as pkl
import matplotlib.pyplot as plt
import os
import time
import torch

from torch import nn, optim
from torch.utils.data import TensorDataset, DataLoader
from glob import iglob

# import models
from models import *


# helper functions
def save_model(filename:str, model):
    '''
    Save model to local file.

    Args:
        filename: file name string
        model: trained model
    '''
    save_filename = os.path.splitext(os.path.basename(filename))[0] + '.pt'
    torch.save(model, save_filename)


def load_model(filename:str):
    '''
    Load trained model.

    Args:
        filename: file name string

    Returns:
        loaded torch model
    '''
    save_filename = os.path.splitext(os.path.basename(filename))[0] + '.pt'
    return torch.load(save_filename)


def batch_dataset(states, sequence_length, batch_size):
    """
    Batch the neural network data using DataLoader

    Args:
        states:
        sequence_length: The sequence length of each batch
        batch_size: The size of each batch; the number of sequences in a batch

    Return:
        DataLoader with batched data
    """
    num_batches = len(states) // batch_size

    # only full batches
    states = states[: num_batches * batch_size]

    # TODO: Implement function
    features, targets = [], []

    for idx in range(0, (len(states) - sequence_length)):
        features.append(states[idx: idx + sequence_length])
        targets.append(states[idx + sequence_length])

    data = TensorDataset(torch.from_numpy(np.array(features)),
                         torch.from_numpy(np.array(targets)))

    data_loader = torch.utils.data.DataLoader(
        data, shuffle=False, batch_size=batch_size, num_workers=0)

    # return a dataloader
    return data_loader


def forward_back_prop(model, optimizer, criterion, inp, target, hidden, clip):
    """
    Forward and backward propagation on the neural network.

    Args:
        model:     The PyTorch Module that holds the neural network
        optimizer: The PyTorch optimizer for the neural network
        criterion: The PyTorch loss function
        inp:       A batch of input to the neural network
        target:    The target output for the batch of input
        hidden:    Hidden state
        clip:      Clip the overly large gradient

    Returns:
        The loss and the latest hidden state Tensor
    """
    # Creating new variables for the hidden state, otherwise
    # we'd backprop through the entire training history
    h = tuple([each.data for each in hidden])

    # zero accumulated gradients
    model.zero_grad()

    # print(f'input shape: {inp}, target shape: {target}')
    # get the output from the model
    output, h = model(inp, h)

    # perform backpropagation and optimization
    # calculate the loss and perform backprop
    loss = criterion(output, target)
    loss.backward()

    # 'clip_grad_norm' helps prevent the exploding gradient problem in RNNs / LSTMs
    nn.utils.clip_grad_norm_(model.parameters(), clip)
    optimizer.step()

    # return the loss over a batch and the hidden state produced by our model
    return loss.item(), h


def train_lstm(model, batch_size, optimizer, criterion, n_epochs,
              train_loader, valid_loader, hyps,
              clip=5, stop_criterion=5,
              show_every_n_batches=100):
    '''
    Train a LSTM model with the given hyperparameters.

    Args:
        model:              The PyTorch Module that holds the neural network
        batch_size:         batch size, integer
        optimizer:          The PyTorch optimizer for the neural network
        criterion:          The PyTorch loss function
        n_epochs:           Total go through of entire dataset
        train_loader:       Training data loader
        valid_loader:       Validation data loader
        hyps:               A dict containing model parameters
        clip:               Clip the overly large gradient
        show_every_batches: Display loss every this number of time steps

    Returns:
        A trained model. The best model will also be saved locally.
    '''
    # clear cache
    torch.cuda.empty_cache()
    # start timing
    start = time.time()
    print(f'Training started at {time.ctime()}')
    # validation constants
    early_stop_count = 0
    valid_loss_min = np.inf

    train_losses = []

    model.train()

    print("Training for %d epoch(s)..." % n_epochs)
    for epoch_i in range(1, n_epochs + 1):

        hidden = model.init_hidden(batch_size)

        for batch_i, (inputs, labels) in enumerate(train_loader, 1):

            # make sure you iterate over completely full batches, only
            n_batches = len(train_loader.dataset) // batch_size
            if(batch_i > n_batches):
                break

            # forward, back prop
            # print(f'inputs shape: {inputs.shape} labels shape: {labels.shape}')
            # print(f'inputs dtype: {inputs[0][0][0].dtype} label shape: {labels[0][0].dtype}')
            inputs, labels = inputs.cuda(), labels.cuda()

            loss, hidden = forward_back_prop(
                model, optimizer, criterion, inputs, labels, hidden, clip
            )

            # record loss
            train_losses.append(loss)

            # print loss every show_every_n_batches batches
            # including validation loss
            if batch_i % show_every_n_batches == 0:
                # get validation loss
                val_h = model.init_hidden(batch_size)
                valid_losses = []

                # switch to validation mode
                model.eval()

                for v_inputs, v_labels in valid_loader:

                    v_inputs, v_labels = v_inputs.cuda(), v_labels.cuda()

                    # Creating new variables for the hidden state, otherwise
                    # we'd backprop through the entire training history
                    val_h = tuple([each.data for each in val_h])

                    v_output, val_h = model(v_inputs, val_h)
                    val_loss = criterion(v_output, v_labels)

                    valid_losses.append(val_loss.item())

                model.train()
                avg_val_loss = np.mean(valid_losses)
                # printing loss stats
                print(f'Epoch: {epoch_i:>4}/{n_epochs:<4}  Loss: {np.mean(batch_losses)}  Val Loss {avg_val_loss}')

                # decide whether to save model or not:
                if avg_val_loss < valid_loss_min:
                    print(f'Valid Loss {valid_loss_min:4f} -> {avg_val_loss:4f}. Saving...')

                    torch.save(model.state_dict(),
                               f'trained_models/LSTM-sl{hyps["sl"]}-bs{hyps["bs"]}-lr{hyps["lr"]}-nl{hyps["nl"]}-dp{hyps["dp"]}.pt')

                train_losses = []
                valid_losses = []

    # returns a trained model
    end = time.time()
    print(f'Training ended at {time.ctime()}, took {end-start:2f} seconds.')
    return model


if __name__ == '__main__':

    # Data params
    # Sequence Length
    sequence_length = 12  # of time slices in a sequence
    # Batch Size
    batch_size = 2
    # Gradient clip
    clip = 5

    # Training parameters
    # Number of Epochs
    epochs = 20
    # Learning Rate
    learning_rate = 0.001

    # Model parameters
    # Vocab size
    input_size = 69*69*3
    # Output size
    output_size = input_size
    # Hidden Dimension
    hidden_dim = 256
    # Number of RNN Layers
    n_layers = 2
    # Dropout probability
    drop_prob = 0.5
    # Show stats for every n number of batches
    senb = 3000

    # wrap essential info into dictionary:
    hyps = {
        'sl': sequence_length,
        'bs': batch_size,
        'lr': learning_rate,
        'hd': hidden_dim,
        'nl': n_layers,
        'dp': drop_prob
    }

    # Environment parameter
    train_on_gpu = torch.cuda.is_available()

    # Initialize data loaders
    train_dir = 'tensor_dataset/nn_test_15min/tensors'
    valid_dir = 'tensor_dataset/nn_test_15min_val/tensors'

    train_iter = iglob(train_dir + '/*')
    valid_iter = iglob(valid_dir + '/*')

    train_states = []
    valid_states = []

    for state in train_iter:
        state = torch.load(state).numpy()
        train_states.append(state)

    for state in valid_iter:
        state = torch.load(state).numpy()
        valid_states.append(state)

    train_states = np.array(train_states)
    valid_states = np.array(valid_states)

    train_states = train_states.reshape((len(train_states), -1))
    valid_states = valid_states.reshape((len(valid_states), -1))
    train_states = train_states.astype('float32')
    valid_states = valid_states.astype('float32')

    train_loader = batch_data(train_states, sequence_length, batch_size)
    valid_loader = batch_data(valid_states, sequence_length, batch_size)

    # initialize model
    model = VanillaStateRNN(input_size, output_size, hidden_dim,
                            n_layers=n_layers, drop_prob=drop_prob,
                            lr=learning_rate)
    if train_on_gpu:
        model = model.cuda()

    # optimizer and criterion(loss function)
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    criterion = nn.MSELoss()

    # start training
    trained_model = train_lstm(model, batch_size, optimizer, criterion, epochs,
                               train_loader, valid_loader, hyps)
