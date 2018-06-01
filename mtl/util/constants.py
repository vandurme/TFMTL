# Copyright 2018 Johns Hopkins University. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================

# -*- coding: utf-8 -*-


"""Constants used in TFMTL"""

"""Splits"""
TRAIN_RATIO = 0.8  # train out of all
VALID_RATIO = 0.1  # valid out of all / valid out of train
RANDOM_SEED = 42

"""Special Symbols"""
OLD_LINEBREAKS = ['<br /><br />', '\n', '\r']  # all the line break marks
# appearing in the unpreprocessed dataset

LINEBREAK = ' brbrbr '  # linebreak mark used to replace all kinds of
# linebreaks; surrounded with whitespaces because replacing linebreaks
# happens before tokenizing
EOS = '<EOS>'  # end of sentence symbol
BOS = '<BOS>'  # beginning of sentence symbol
OOV = '<UNK>'  # out of vocabulary symbol

"""Valid vocabulary names to load"""
VOCAB_NAMES = [
  'vocab_freq.json',  # when merging vocabularies of multiple datasets
  'vocab_v2i.json',  # when directly loading word-id mapping
  'glove.6B.50d.txt',  # when using(init only / expand vocab) Glove's
  # pre-trained word embeddings
  'glove.6B.100d.txt',
  'glove.6B.200d.txt',
  'glove.6B.300d.txt',
  'glove.42B.300d.txt',
  'glove.840B.300d.txt',
  'glove.twitter.27B.25d.txt',
  'glove.twitter.27B.50d.txt',
  'glove.twitter.27B.100d.txt',
  'glove.twitter.27B.200d.txt'
]

"""Experiment names"""


class EXP_NAMES():
  RUDER_NAACL_18 = EMNLP_18 = "RUDER_NAACL_18"
