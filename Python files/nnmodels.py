# -*- coding: utf-8 -*-
"""NNModels.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1jMlGkZnZ5IUPHXCe6cx5P3RBHC6uI8AA
"""

from google.colab import drive
drive.mount('/content/drive')

"""# Constructing the Neural Network model proposed
In this notebook, we construct the NN model as discussed in section 2.1 of the original paper. We build the model, and fit the model with MIMIC-III data to try to predict ICD9 codes.
The model will be used later to generate patient representations (from the hidden layer) for disease prediction task.
"""

import numpy as np
import pandas as pd
import os
import re

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import DataLoader, Dataset
from torch.nn.modules.activation import ReLU
import sklearn
from sklearn.metrics import precision_recall_fscore_support, accuracy_score, f1_score
from sklearn.model_selection import train_test_split
import pickle
from gensim.models import Word2Vec
import warnings
warnings.filterwarnings('ignore')

# extraction configs:
MIN_TOKEN_FREQ = 100
MAX_TOKENS_IN_FILE = 10000
MIN_EXAMPLES_PER_CODE = 1000
TEST_SIZE = 0.2

#yunxuan's
CPT_FILE_PATH = "drive/MyDrive/MIMIC/mimic-iii/CPTEVENTS.csv"
DIAGNOSIS_FILE_PATH = "drive/MyDrive/MIMIC/mimic-iii/DIAGNOSES_ICD.csv"
PROCEDURES_FILE_PATH = "drive/MyDrive/MIMIC/mimic-iii/PROCEDURES_ICD.csv"
CORPUS_FILE_PATH = "drive/MyDrive/MIMIC/output_first_half_selected_cuis/" #FILL IN PATH

CPT_FILE_PATH = "drive/MyDrive/mimic-iii/CPTEVENTS.csv"
DIAGNOSIS_FILE_PATH = "drive/MyDrive/mimic-iii/DIAGNOSES_ICD.csv"
PROCEDURES_FILE_PATH = "drive/MyDrive/mimic-iii/PROCEDURES_ICD.csv"
CORPUS_FILE_PATH = "drive/MyDrive/mimic-iii/cuis/" #FILL IN PATH

# model configs
criterion = nn.BCELoss()
n_epochs = 75
batch_size = 50

#word2vec config
USE_PRETRAINED_W2V = False
RUN_LOADER = False



"""# Load the MIMIC-III data
Note that clinical notes were preprocessed via apache ctakes (check ctakes script and , and Concept Unique Identifiers (CUIs) were already extracted. The ICDLoader takes each patient's file of CUIs and loads the data.
"""

class ICDLoader: 
  """Load ICD billing codes labels for each patient"""

  def __init__(self, corpus_file_path, cpt_file_path, diagnosis_file_path, procedures_file_path, min_examples_per_code, min_token_freq, max_tokens_in_file):
    self.corpus_path = corpus_file_path
    self.cpt_path = cpt_file_path
    self.diagnosis_path = diagnosis_file_path
    self.procedures_path = procedures_file_path
   
    self.max_tokens_in_file = max_tokens_in_file
    self.min_examples_per_code = min_examples_per_code
    self.min_token_freq = min_token_freq
    self.patient2label_dict = None #mapping from patient -> ICD9 label codes
    self.label2idx_dict = None #mapping from ICD9 label code -> embedding idx

    self.token2int = {}

  def df_make_code(self, df, icd_type, code_len, code_col):
    #making special short string for codes
    df['short_code'] = icd_type + "_" + df[code_col].astype(str).str[:code_len]
    return df
  
  def get_label2freq_df(self, df, min_examples_per_code):
    #get a filtered label codes -> frequency mapping table 
    label2freq_df = df[["SUBJECT_ID", "short_code"]].groupby("short_code").nunique()
    label2freq_df = label2freq_df[label2freq_df["SUBJECT_ID"]>min_examples_per_code]
    label2freq_df.rename({"SUBJECT_ID": "freq"}, axis=1, inplace=True)
    return label2freq_df.reset_index()

  def get_patient2label_df(self, df, label2freq_df):
    #get df of patient mapping to all their filtered ICD9 code labels (filtered by freq)
    df_filtered = df[df["short_code"].isin(label2freq_df["short_code"])] 
    patient2label_df = df_filtered[["SUBJECT_ID", "short_code"]]\
                          .groupby("SUBJECT_ID")\
                          .agg({'short_code':lambda sf: set(sf)})
    patient2label_df.rename({"short_code":"short_codes"}, axis=1, inplace=True)          
    return patient2label_df.reset_index()

  def create_patient_label_vec(self, subj_id, patient2label_dict, label2idx_dict):
    #make patient label vector
    code_vec = [0]*len(label2idx_dict)
    codes = patient2label_dict[subj_id]
    for code in codes:
      code_vec[label2idx_dict[code]] = 1
    return code_vec

  def make_cui_token2int_mapping(self):
    #count tokens
    token_count_dict = {}
    for file in os.listdir(self.corpus_path):
      text = open(os.path.join(self.corpus_path,file)).read()
      tokens = [token for token in text.split()] #assume all cui in file splitted by space
      if len(tokens) > self.max_tokens_in_file:
        continue
      else:
        for token in tokens:
          if token in token_count_dict:
            token_count_dict[token] += 1
          else:
            token_count_dict[token] = 1
    
    #make token2int mapping
    oov_idx = 0
    idx = 1
    self.token2int['oov_word'] = 0
    for token, count in token_count_dict.items():
      if count > self.min_token_freq:
        self.token2int[token] = idx
        idx += 1
  
  def create_cui_input_sequence(self, tokens):
    #create cui_input_sequence from cui tokens
    input = []
    tokens_set = set(tokens)

    for token in tokens_set:
      if token in self.token2int:
        input.append(self.token2int[token])
      else:
        input.append(self.token2int['oov_word'])

    return input

  def run(self):
    #run everything

    #codes init
    cpt = pd.read_csv(self.cpt_path)
    diagnosis = pd.read_csv(self.diagnosis_path)
    procedures = pd.read_csv(self.procedures_path)

    #codes init
    cpt = self.df_make_code(cpt, 'cpt', 5, 'CPT_NUMBER')
    diagnosis = self.df_make_code(diagnosis, 'diag', 3, 'ICD9_CODE')
    procedures = self.df_make_code(procedures, 'proc', 2, 'ICD9_CODE')

    #codes init
    all_codes = cpt[["SUBJECT_ID", "short_code"]]\
              .append(diagnosis[["SUBJECT_ID", "short_code"]], ignore_index=True)\
              .append(procedures[["SUBJECT_ID", "short_code"]], ignore_index=True)

    #codes init
    label2freq_df = self.get_label2freq_df(all_codes, self.min_examples_per_code)
    patient2label_df = self.get_patient2label_df(all_codes, label2freq_df)
    
    #codes init
    self.label2idx_dict = dict(label2freq_df.reset_index()[["short_code", "index"]].values)
    self.patient2label_dict = dict(patient2label_df.values)

    #cui init
    # self.make_cui_token2int_mapping()
    with open("drive/MyDrive/mimic-iii/token2int_dict.pkl", "rb") as fp:
      self.token2int = pickle.load(fp)

    codes = []
    cui_inputs = []

    #processing
    for file in os.listdir(self.corpus_path): #list files to run
      text = open(os.path.join(self.corpus_path, file)).read()
      tokens = [token for token in text.split()]
      if len(tokens) > self.max_tokens_in_file: #cui filter
        continue

      subj_id = int(re.findall('\d+(?=.txt)', file)[0])
      if subj_id not in self.patient2label_dict: #icd9 filter
        continue

      #icd9 process  
      code_vec = self.create_patient_label_vec(subj_id, self.patient2label_dict, 
                                               self.label2idx_dict)
      if sum(code_vec) == 0:
        continue
      codes.append(code_vec)

      #cui process
      cui_input = self.create_cui_input_sequence(tokens)
      cui_inputs.append(cui_input)

    return cui_inputs, codes

# after the first run, we dumped all critical attributes of ICDLoader so we only need to load them later, avoiding processing the giant MIMIC-III dataset again and again.
if RUN_LOADER:
  loader = ICDLoader(CORPUS_FILE_PATH, CPT_FILE_PATH, DIAGNOSIS_FILE_PATH, PROCEDURES_FILE_PATH, MIN_EXAMPLES_PER_CODE, MIN_TOKEN_FREQ, MAX_TOKENS_IN_FILE)
  cui_inputs, codes = loader.run()

with open("drive/MyDrive/mimic-iii/token2int_dict.pkl", "rb") as fp:
  token2int = pickle.load(fp)

with open("drive/MyDrive/mimic-iii/cui_inputs.pkl", "rb") as fp:   #Pickling
  cui_inputs = pickle.load(fp)

with open("drive/MyDrive/mimic-iii/icd9codes.pkl", "rb") as fp:   #Pickling
  codes = pickle.load(fp)

with open("drive/MyDrive/mimic-iii/patient2label_dict.pkl", "rb") as fp:   #Pickling
  patient2label_dict = pickle.load(fp)

with open("drive/MyDrive/mimic-iii/label2idx_dict.pkl", "rb") as fp:   #Pickling
  label2idx_dict = pickle.load(fp)



"""# Constructing the model"""

maxlen = max([len(patient) for patient in cui_inputs])
emb_dim = len(token2int)
n_class = len(label2idx_dict)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

X_train, X_test, y_train, y_test = train_test_split(cui_inputs,codes, test_size=0.2, random_state=42)

class customDataset(Dataset):
    def __init__(self, x, y):
        self.x = x # shape n_sample x padded length
        self.y = y # shape n_sample x n classes [[0,1,0,0], [1,1,1,0]]
    def __len__(self):
        return len(self.x)
    def __getitem__(self, index):
        return(self.x[index], self.y[index])

train_dataset = customDataset(X_train, y_train)
test_dataset = customDataset(X_test, y_test)

# the paper discussed training 2 versions of the model: (1) with randomly initialized CUI embeddings, (2) with word2vec-pretrained CUI embeddings
if USE_PRETRAINED_W2V:
  w2v_model = Word2Vec.load("drive/MyDrive/mimic-iii/word2vec.model")

def collate_fn(data):
    sequences, labels = zip(*data)
    y = torch.tensor(labels, dtype=torch.float).to(device)

    n = len(sequences)
    x = torch.zeros((n, maxlen), dtype=torch.long).to(device)
    
    for patient, cuis in enumerate(sequences):
      len_cuis = len(cuis)
      x[patient][:len_cuis] = torch.tensor(cuis).to(device)
      
    return x, y

def collate_fn_w2v(data):
    sequences, labels = zip(*data)
    y = torch.tensor(labels, dtype=torch.float).to(device)

    n = len(sequences)
    x = torch.zeros((n, maxlen), dtype=torch.long).to(device)
    
    for patient, cuis in enumerate(sequences):
      len_cuis = len(cuis)
      cui_w2v_idx = [w2v_model.wv.vocab[str(token)].index for token in cuis]
      x[patient][:len_cuis] = torch.tensor(cui_w2v_idx).to(device)
    return x, y

if not USE_PRETRAINED_W2V:
  train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, collate_fn=collate_fn)
  test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=True, collate_fn=collate_fn)
else:
  train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, collate_fn=collate_fn_w2v)
  test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=True, collate_fn=collate_fn_w2v)

class NN_representation(nn.Module):
  def __init__(self, in_dim, n_diseases, w2v_model=None):
    super(NN_representation, self).__init__()
    if w2v_model:
      weights = torch.FloatTensor(w2v_model.wv.vectors)
      self.emb = nn.Embedding(num_embeddings= in_dim, embedding_dim= 300).from_pretrained(weights, freeze=False)
    else:
      self.emb = nn.Embedding(num_embeddings= in_dim, embedding_dim= 300)
    self.avg = nn.AdaptiveMaxPool1d(1)
    
    self.hidden = nn.Linear(300, 1000)
    self.act1 = nn.ReLU()
    self.final = nn.Linear(1000, n_diseases)
    self.act2 = nn.Sigmoid()

  def get_hidden(self, x):
    temp = self.emb(x)
    #print(f"after emb, {temp.shape}")
    temp = torch.permute(temp, (0,2,1))
    #print(f"after permute, {temp.shape}")
    temp = self.avg(temp)
    #print(f"after avg, {temp.shape}")
    temp = temp.squeeze(-1)
    #print(f"after squeeze, {temp.shape}")
    h = self.hidden(temp)
    return h

  def forward(self, x):
    temp = self.emb(x)
    #print(f"after emb, {temp.shape}")
    temp = torch.permute(temp, (0,2,1))
    #print(f"after permute, {temp.shape}")
    temp = self.avg(temp)
    #print(f"after avg, {temp.shape}")
    temp = temp.squeeze(-1)
    #print(f"after squeeze, {temp.shape}")
    temp = self.hidden(temp)
    #print(f"after hidden, {temp.shape}")
    temp = self.act1(temp)
    #print(f"after relu, {temp.shape}")
    temp = self.final(temp)
    #print(f"after linear hidden, {temp.shape}")
    res = self.act2(temp)
    return res

if not USE_PRETRAINED_W2V:
  nnmodel =NN_representation(emb_dim, n_class).to(device)
else:
  nnmodel =NN_representation(emb_dim, n_class, w2v_model).to(device)
optimizer = torch.optim.RMSprop(nnmodel.parameters(), lr=0.001)



"""# Model Training and Evaluation"""

def train(model, loader, n_epochs):
  model.train()
  for epoch in range(n_epochs):
    current_loss = 0
    for current_x, current_y in loader:
      pred = model(current_x)
      loss = criterion(pred, current_y)
      optimizer.zero_grad()
      loss.backward()
      optimizer.step()
      current_loss += loss.item()
    train_loss = current_loss/len(loader)
    print(f"after epoch {epoch}, the training loss is {train_loss}")

train(nnmodel, train_loader, n_epochs)

def test(model, loader):
  model.eval()
  y_pred = []
  y_true = []
  for current_x, current_y in loader:
      preds = model(current_x).cpu().detach().numpy()
      preds_labels = preds>0.5
      y_pred.append(preds_labels)
      y_true.append(current_y.cpu().numpy())
  y_pred = np.vstack(y_pred)  
  y_true = np.vstack(y_true)        

  p,r,f,_ = precision_recall_fscore_support(y_pred, y_true, average='macro')
  acc = accuracy_score(y_pred, y_true)
  return p,r,f,acc

precision, recall, f1, accuracy = test(nnmodel, test_loader)

precision, recall, f1, accuracy

precision_train, recall_train, f1_train, accuracy_train = test(nnmodel, train_loader)

precision_train, recall_train, f1_train, accuracy_train



"""# Saving the model for tasks in SVM_Models notebook."""

# torch.save(nnmodel.state_dict(), "drive/MyDrive/mimic-iii/nnmodel_pretrained_w2v_state_dict.pt")
nnmodel_new =NN_representation(emb_dim, n_class).to(device)
nnmodel_new.load_state_dict(torch.load("drive/MyDrive/mimic-iii/nnmodel_pretrained_w2v_state_dict.pt"))
