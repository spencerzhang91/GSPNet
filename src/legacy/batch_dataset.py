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
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

import numpy as np
import pandas as pd
import torch
import glob
from torch.utils.data import TensorDataset, DataLoader


# generate training pair from tensors
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


if __name__ == '__main__':

    # tests:
    tensor_dir = 'tensor_dataset/nn_test_15min/tensors'
    visual_dir = 'tensor_dataset/nn_test_15min/viz_images'

    tensor_iter = iglob(tensor_dir + '/*')
    states = []

    for state in tensor_iter:
        state = torch.load(state).numpy()
        states.append(state)

    states = np.array(states)

    states = states.reshape((2976, -1))
    states = states.astype('float32')
    states.shape

    data_loader = batch_dataset(states, 12, 2)
