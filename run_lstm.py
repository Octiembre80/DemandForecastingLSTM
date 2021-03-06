import pandas as pd
import os
import datetime

import torch
import torch.nn as nn
from torch.autograd import Variable
from torch import optim
import numpy as np
import random

# ---------------------------- PARAMS  ------------------------------- #
EPOCHS = 1000
LEARNING_RATE = 0.2
HIDDEN_DIMS = 25
NUM_LSTM_CELLS = 1
NUM_WINDOWS = 5
WINDOW_LENGTH = 8760  # 1-year windows
FORECAST_HORIZON = 24


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
cols = ['apparentTemperature', 'humidity', 'MWh']
df = data[cols]

df = (df - df.min())/(df.max()-df.min())  # Min-Max Normalization

inputs = df
targets = df['MWh']  # Un-normalized targets

# Percentage of samples to use as training data
TRAINING_SAMPLE_RATIO = 0.7
num_training_samples = round(len(inputs)*TRAINING_SAMPLE_RATIO)

# Splits data samples
(training_inputs, test_inputs) = np.split(inputs.values, [num_training_samples])
(training_targets, test_targets) = np.split(targets.values, [num_training_samples])

# Prepares training data for input to network
training_inputs = Variable(torch.from_numpy(training_inputs).float()).cuda()
training_targets = Variable(torch.from_numpy(training_targets).float()).cuda()
test_inputs = Variable(torch.from_numpy(test_inputs).float()).cuda()
test_targets = Variable(torch.from_numpy(test_targets).float()).cuda()

# -------------------- Instantiate LSTM Network  --------------------- #
# Model Params
input_dim = training_inputs.shape[1]
hidden_dim = HIDDEN_DIMS

# Create model and necessary functions
model = LSTM(input_dim, HIDDEN_DIMS, num_lstm_cells=NUM_LSTM_CELLS).cuda()
criterion = nn.MSELoss()
optimizer = optim.SGD(model.parameters(), lr=LEARNING_RATE)

# --------------------------- Train Network -------------------------= #
losses = []

# Train loop
for epoch in range(EPOCHS):
    mse = 0

    for i in range(NUM_WINDOWS):
        index = round(random.random() * (len(training_inputs) - WINDOW_LENGTH - FORECAST_HORIZON))
        window = training_inputs[index:index + WINDOW_LENGTH].unsqueeze(1)
        target = training_targets[index + FORECAST_HORIZON:index + WINDOW_LENGTH + FORECAST_HORIZON]

        # Zero gradients
        optimizer.zero_grad()

        # Update weights
        outputs = model(window)
        loss = criterion(outputs, target)
        loss.backward()
        optimizer.step()

        # Print stats
        mse = mse + loss.data[0]

    losses.append(mse)
    print('Epoch: {0}/{1},Training Loss: {2}'.format(epoch, EPOCHS, mse))


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
