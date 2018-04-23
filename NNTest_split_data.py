
# coding: utf-8

import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.nn import functional as F
from torch.autograd import Variable
from torch import optim
import numpy as np
import math, random,datetime,os
import matplotlib.pyplot as plt


# ---------------------------- PARAMS  ------------------------------- #
EPOCHS = 1000
LEARNING_RATE = 0.1
HIDDEN_DIMS = 1
NUM_LSTM_CELLS = 1


# ------------------------ Define Network  --------------------------- #
class LSTM(torch.nn.Module):
    def __init__(self, input_dimensions, hidden_dimensions, num_lstm_cells=1, lstm_dropout=0.1):
        super(LSTM, self).__init__()

        # Parameters
        self.input_dim = input_dimensions
        self.hidden_dim = hidden_dimensions
        self.num_lstm_cells = num_lstm_cells
        self.lstm_dropout = lstm_dropout

        # Network layers
        self.lstm = nn.LSTM(input_dimensions, hidden_dimensions, dropout=0.1, num_layers=num_lstm_cells)
        self.c1 = nn.Linear(hidden_dimensions, hidden_dimensions)
        self.out = nn.Linear(hidden_dimensions, 1, bias=False)

    def forward(self, x):
        h_1, c_1 = self.lstm(x)
        output = self.c1(h_1.squeeze(1))
        output = self.out(output)
        return output


# ---------------------- Load and Process Data  ---------------------- #
data = pd.read_csv('full_data.csv', index_col=0)
cols = ['apparentTemperature', 'dewPoint', 'humidity',
        'pressure', 'temperature', 'MWh']
df = data[cols]

df = (df - df.min())/(df.max()-df.min())  # Min-Max Normalization
# df = (df - df.mean())/df.std() ##Gaussian normalization

inputs = df[:-1]
targets = data['MWh'][1:]  # Un-normalized targets

# Percentage of samples to use as training data
TRAINING_SAMPLE_RATIO = 0.7
num_training_samples = round(len(inputs)*TRAINING_SAMPLE_RATIO)

# Splits data samples
(training_inputs,test_inputs) = np.split(inputs.values,[num_training_samples])
(training_targets,test_targets) = np.split(targets.values,[num_training_samples])

# Prepares training data for input to network
training_inputs = Variable(torch.from_numpy(training_inputs).float()).unsqueeze(1).cuda()
training_targets = Variable(torch.from_numpy(training_targets).float()).cuda()
test_inputs = Variable(torch.from_numpy(test_inputs).float()).unsqueeze(1).cuda()
test_targets = Variable(torch.from_numpy(test_targets).float()).cuda()


# -------------------- Instantiate LSTM Network  --------------------- #
# Model Params
input_dim = training_inputs.shape[2]
hidden_dim = HIDDEN_DIMS

# Create model and necessary functions
model = LSTM(input_dim, HIDDEN_DIMS, num_lstm_cells=NUM_LSTM_CELLS).cuda()
criterion = nn.MSELoss()
optimizer = optim.SGD(model.parameters(), lr=LEARNING_RATE)


# --------------------------- Train Network -------------------------= #
losses = []
test_losses = []
# Train loop
for epoch in range(EPOCHS):
    # Zero gradients
    optimizer.zero_grad()

    # Update weights
    outputs = model(training_inputs)
    loss = criterion(outputs, training_targets)
    loss.backward()
    optimizer.step()

    # Apply test data
    test_outputs = model(test_inputs)
    test_mse = criterion(test_outputs,test_targets).data[0]
    test_losses.append(test_mse)
    
    # Print stats
    mse = loss.data[0]
    losses.append(mse)
    print('Epoch: {0}/{1},Training Loss: {2}, Test Loss: {3}'.format(epoch, EPOCHS, mse,test_mse))     
    

# Generate date tag and path for outputs
time = datetime.datetime.now()
date_tag = '{0}{1}_{2}{3}'.format(time.month, time.day, time.hour, time.minute)
preds_path = os.getcwd() + '/predictions/{}.csv'.format(date_tag)
model_path = os.getcwd() + '/models/model_{}.pkl'.format(date_tag)
model_dict_path = os.getcwd() + '/models/model_{}_state_dict.pkl'.format(date_tag)
loss_path = os.getcwd() + '/losses/loss_{}.csv'.format(date_tag)

# Save outputs
torch.save(model, model_path)
torch.save(model.state_dict(), model_dict_path.format(date_tag))
pd.DataFrame(outputs.cpu().data.numpy()).to_csv(preds_path)
pd.DataFrame(losses).to_csv(loss_path)
