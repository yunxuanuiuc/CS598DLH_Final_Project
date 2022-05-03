## CS598DLH_Final_Project

# Reproducibility of Learning Patient Representations from Text
This repository is the implementation of Reproducibility of Learning Patient Representations from Text(to add: link). 

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




## Results

TBA

## Contribution
This is a final project for 2022S CS598 Deep Learning for Healthcare, developed by Michael Huang and Yunxuan Li. 
