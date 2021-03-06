## CS598DLH_Final_Project

# Reproducibility of Learning Patient Representations from Text
This repository is the implementation of Reproducibility of Learning Patient Representations, published by Dligach and Miller in 2018.(https://arxiv.org/pdf/1805.02096.pdf). T. Dligach, D. & Miller. 2018. Learning patient representations from text. Association for Computational
Linguistic, pages 119–123.

Link to Original Paper's Code Repo: https://github.com/dmitriydligach/starsem2018-patient-representations

## Requirements

### Access to data:
- Access to MIMIC-III data is required. You should complete the CITI training and evaluation to request for access. (https://www.citiprogram.org/)
- Access to Informatics for Integrating Biology and the Bedside (i2b2)'s 2008 Obesity Challenge data is required. You can request access here: https://portal.dbmi.hms.harvard.edu/projects/n2c2-nlp/

### For Concept Unique Identifiers (CUI) extraction:
- Apache cTAKES with version 4.0.0.1 is required. 
- You will also need to install the latest cTAKES UMLS dictionary.
You can find download links at https://ctakes.apache.org/downloads.cgi. Note that in order to use UMLS dictionary, you will also need to request a UMLS license at https://uts.nlm.nih.gov/uts/. This will give you an API key to access the dictionaries.
To run the script to extract CUIs, 
```
bin/runPiperFile -p path_to_cui_script\Cui_Yunxuan.piper -i path_to_input_dir --xmiOut path_to_output_dir --key yourAPIKeyValue
```
You should refer to Obesity_data_preprocessing.py and mimiciii_data_preprocessing.py to first prepare the data before feeding them into the cTAKES pipeline.

### For model development:
- The versions of packages used are listed in requirements.txt.
- We use Google Colab to develop our code, so if you upload the notebooks under the Notebooks directory and run them on Google Colab, you should automatically get packages that satisfy the requirements installed and imported.

## How to follow this repo

We recommend running our notebooks on Google Colab, which requires minimal effort to set up environment. Please take the follow steps to reproduce our results (don't forget to change file paths!):
### Data preparation
1. Check out Data_preprocessing.ipynb to clean raw MIMIC clinical texts and obesity data.
3. (In your local) Run cTAKES pipeline to get xmi files containing CUIs for each patient.
4. Checkout the last section in Data_preprocessing.ipynb to extract CUI tokens out of xmi files.

### Modeling and Evaluation:
1. Run MIMICIII_pretrain_embeddings.ipynb to pretrain embedding models.
2. Run NNModels.ipynb to train the NN model with MIMIC-III data, evaluate the initial performance, and save the model. (Can use USE_WORD2VEC variable to toggle between training with CUI Word2Vec pretrained embeddings vs. randomly initialized embeddings)
3. Execute SVM_Models.ipynb to train and evaluate the performances of baseline models, proposed models, and models from ablation study.

## Results

Result 1:

Original vs. Replicated F1 Scores for ICD9 Billing Code Prediction task. We compare between random initialization for NN model vs. pretrained CUI Word2Vec embedding initialization.
| Initialization  | Original F1 | Replicated F1  |
| ------------- | ------------- | ------------- |
| Random  | 0.447 | 0.390  |
| Word2Vec  | 0.473  | 0.177  |

Result 2:

Original vs. Replicated F1 Scores, averaged over all diseases, for obesity comorbidity prediction. Models are SVM models with sparse (BoW) features, SVD features, and learned dense patient representation features.

| Orig/Rep | Sparse  | SVD | Learned |
| ------------- | ------------- | ------------- | ------------- |
| Orig | 0.675 | 0.674  | 0.715
| Rep  | 0.672  | 0.645  | 0.695

## Contribution
This is a final project for 2022S CS598 Deep Learning for Healthcare, developed by Michael Huang and Yunxuan Li. 
