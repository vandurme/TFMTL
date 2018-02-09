#!/usr/bin/env bash
set -e
mkdir data
mkdir data/raw
mkdir data/json

mkdir data/raw/SSTb
mkdir data/json/SSTb
mkdir data/raw/LMRD
mkdir data/json/LMRD


echo "Downloading the SSTb data..."
wget -nc https://nlp.stanford.edu/sentiment/trainDevTestTrees_PTB.zip

unzip trainDevTestTrees_PTB.zip
mv -f trainDevTestTrees_PTB.zip data/raw/SSTb/

echo "Converting the SSTb data to json..."
python3 ../../tasks/datasets/sentiment/SSTb/convert_SSTb_to_JSON.py ./
mv -f trees data/raw/SSTb/
mv -f data.json.gz data/json/SSTb/
mv -f index.json.gz data/json/SSTb/

echo "Downloading the LMRD data..."
wget -nc http://ai.stanford.edu/~amaas/data/sentiment/aclImdb_v1.tar.gz

echo "Untarring the LMRD data..."
tar zxvf aclImdb_v1.tar.gz
mv -f aclImdb_v1.tar.gz data/raw/LMRD/

echo "Converting the LMRD data to json..."
python3 ../../tasks/datasets/sentiment/LMRD/convert_LMRD_to_JSON.py ./

mv -f aclImdb data/raw/LMRD/
mv -f data.json.gz data/json/LMRD/
mv -f index.json.gz data/json/LMRD/


python write_tfrecords.py