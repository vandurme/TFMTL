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
# ==============================================================================
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import gzip
import itertools
import json
import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf
from tasks.code.data_prep import tweet_clean
from tasks.code.text import VocabularyProcessor
from tasks.code.util import bag_of_words
from tensorflow.contrib.learn.python.learn.preprocessing import \
    CategoricalVocabulary

flags = tf.flags
logging = tf.logging

FLAGS = flags.FLAGS

TRAIN_RATIO = 0.8
VALID_RATIO = 0.1
RANDOM_SEED = 42


class Dataset():
    def __init__(self, data_dir, vocab_dir=None, tfrecord_dir=None,
                 max_document_length=None,
                 min_frequency=0, max_frequency=-1, encoding=None,
                 text_field_names=None,
                 label_field_name=None,
                 valid_ratio=VALID_RATIO, train_ratio=TRAIN_RATIO,
                 random_seed=RANDOM_SEED,
                 scale_ratio=None, generate_basic_vocab=False,
                 generate_tf_record=True, padding=False):
        """

        :param data_dir: where data.json.gz and index.json.gz are
        located, and vocabulary/tf records built from the single datasets
        are to be saved
        :param vocab_dir: directory of the public vocabulary frequency dict
        pickle file, None if building its own vocabulary
        :param tfrecord_dir: directory to save generated TFRecord files
        :param max_document_length: maximum document length for the mapped
        word ids, computed as the maximum document length of all the
        training data if None
        :param min_frequency: minimum frequency to build the vocabulary,
        words that appear lower than or equal to this number would be discarded
        :param max_frequency: maximum frequency to build the vocabulray,
        words that appear more than or equal to this number would be discarded
        :param encoding: e.g. bow, etc. written to TFRecord files
        :param text_field_names: string of a list of text field names joined
        with spaces, read from data_dir if None
        :param label_field_name: label field name(only 1), read from
        data_dir if None
        :param valid_ratio: how many data to use as valid data if valid
        split not given
        :param train_ratio: how many data to use as train data if train
        split not given
        :param random_seed: random seed used in random spliting, makeing
        sure the same random split is used when given the same random seed
        :param scale_ratio: randomly takes part of the datasets when it's
        too large
        :param generate_basic_vocab: True if the basic vocabulary(which
        shall be used to merge the public vocabulary) needs to be generated
        :param generate_tf_record: True if tf record files need generating
        :param generate_tf_record: True if word_id needs padding to
        max_document_length
        """

        print("data in", data_dir)

        df = pd.read_json(data_dir + "data.json.gz", encoding='utf-8')

        if label_field_name is None:
            label_field_name = 'label'
            if Path(os.path.join(data_dir, "label_field_name")).exists():
                file = open(os.path.join(data_dir, "label_field_name"))
                label_field_name = file.readline().strip()
            print("labels:", label_field_name)

        if text_field_names is None:
            text_field_names = ['text']
            if Path(os.path.join(data_dir, "text_field_names")).exists():
                file = open(os.path.join(data_dir, "text_field_names"))
                text_field_names = file.readline().split()
            print("text:", text_field_names)

        self.label_list = df[label_field_name].tolist()
        self.num_classes = len(set(self.label_list))

        self.text_list = df[text_field_names].astype(str).sum(axis=1).tolist()

        self.encoding = encoding
        self.padding = padding

        # tokenize and reconstruct as string(which vocabulary processor
        # takes as input)
        # TODO more on tokenizer

        self.old_length_list = [len(text) for text in self.text_list]
        self.text_list = [tweet_clean(text) for text in
                          self.text_list]
        self.text_list = [text + " EOS" for text in self.text_list]
        self.new_length_list = [len(text) for text in self.text_list]

        # get index
        index_path = os.path.join(data_dir, "index.json.gz")
        self.train_index, self.valid_index, self.test_index = self.split(
            index_path, train_ratio, valid_ratio, random_seed, scale_ratio)

        if max_document_length is None:
            self.max_document_length = max(
                [len(x.split()) for x in self.text_list])
            print("max document length (computed) =",
                  self.max_document_length)
        else:
            self.max_document_length = max_document_length
            print("max document length (given) =", self.max_document_length)

        self.vocab_dict = None
        self.categorical_vocab = None

        # generate and save the vocabulary which contains all the words
        if generate_basic_vocab:
            print("Generating the basic vocabulary.")
            self.build_save_basic_vocab(
                vocab_dir=os.path.join(data_dir, "single/"))

        if generate_tf_record is False:
            print("No need to generate tf records. Done. ")
            return

        if vocab_dir is None:
            print("No vocabulary given. Generate a new one.")
            vocab_dir = os.path.join(data_dir, "single/")
            self.categorical_vocab = self.build_vocab(
                min_frequency=min_frequency,
                max_frequency=max_frequency, vocab_dir=vocab_dir)
            # save
            self.save_vocab(vocab_dir, min_frequency)

        else:
            print("Public vocabulary given. Use that to build vocabulary "
                  "processor.")
            self.categorical_vocab = self.load_vocab(vocab_dir,
                                                     min_frequency=min_frequency,
                                                     max_frequency=max_frequency)
        # save mapping/reverse mapping to the disk
        # vocab_dir/vocab_freq_dict_(min_freq).pickle
        # vocab_i2v_list_(min_freq).pickle
        # vocab_v2i_dict_(min_freq).pickle
        # save

        self.vocab_size = len(self.categorical_vocab._mapping)
        print("used vocab size =", self.vocab_size)

        # write to tf records
        if tfrecord_dir is None:
            tfrecord_dir = data_dir + 'single/'
        try:
            os.stat(tfrecord_dir)
        except:
            os.mkdir(tfrecord_dir)
        self.train_path = os.path.join(tfrecord_dir, 'train.tf')
        self.valid_path = os.path.join(tfrecord_dir, 'valid.tf')
        self.test_path = os.path.join(tfrecord_dir, 'test.tf')

        self.write_examples(self.train_path, self.train_index)
        self.write_examples(self.valid_path, self.valid_index)
        self.write_examples(self.test_path, self.test_index)

        # save dataset arguments
        args = {
            'num_classes': self.num_classes,
            'max_document_length': self.max_document_length,
            'vocab_size': self.vocab_size,
            'min_frequency': min_frequency,
            'max_frequency': max_frequency,
            'random_seed': random_seed
        }
        args_path = os.path.join(tfrecord_dir, "args_dict.pickle")
        with open(args_path, "wb") as file:
            pickle.dump(args, file)
            print("data arguments saved to", args_path)

    def build_vocab(self, min_frequency, max_frequency, vocab_dir):
        """Builds vocabulary for this dataset only using tensorflow's
        VocabularyProcessor

        This vocabulary is only used for this dataset('s training data)
        """
        vocab_processor = VocabularyProcessor(
            max_document_length=self.max_document_length,
            min_frequency=min_frequency,
            max_frequency=max_frequency)

        # build vocabulary only according to training data
        train_list = [self.text_list[i] for i in self.train_index]

        vocab_processor.fit(train_list)

        if self.padding is True:
            self.word_id_list = list(
                vocab_processor.transform_pad(self.text_list))
        else:
            self.word_id_list = list(
                vocab_processor.transform(self.text_list))
        self.word_id_list = [list(i) for i in self.word_id_list]
        self.vocab_freq_dict = vocab_processor.vocabulary_._freq

        return vocab_processor.vocabulary_

    def save_vocab(self, vocab_dir, min_frequency):

        # save the built vocab to the disk for future use
        try:
            os.stat(vocab_dir)
        except:
            os.mkdir(vocab_dir)
        with open(vocab_dir + "vocab_freq_dict_" + str(
                min_frequency) + ".pickle",
                  "wb") as file:
            pickle.dump(self.vocab_freq_dict, file)
            file.close()
        with open(vocab_dir + "vocab_v2i_dict_" + str(
                min_frequency) + ".pickle",
                  "wb") as file:
            pickle.dump(self.categorical_vocab._mapping, file)
            file.close()
        with open(vocab_dir + "vocab_i2v_list_" + str(
                min_frequency) + ".pickle",
                  "wb") as file:
            pickle.dump(self.categorical_vocab._reverse_mapping, file)
            file.close()

    def build_save_basic_vocab(self, vocab_dir):
        """Bulid vocabulary with min_frequency=0 for this dataset'


        training data only and save to the directory
        minimum frequency is always 0 so that all the words of this dataset(
        's training data) are taken into account when merging with other
        vocabularies"""

        vocab_path = os.path.join(vocab_dir, "vocab_freq_dict.pickle")

        # if Path(vocab_path).exists():
        #     print("vocabulary file already exists!")
        #     return
        # print("vocabulary file doesn't exits. Generate.")

        vocab_processor = VocabularyProcessor(
            max_document_length=self.max_document_length)

        # build vocabulary only according to training data
        train_list = [self.text_list[i] for i in self.train_index][:]

        vocab_processor.fit(train_list)
        vocab_freq_dict = vocab_processor.vocabulary_._freq
        print("total word size =", len(vocab_freq_dict))
        try:
            os.stat(vocab_dir)
        except:
            os.mkdir(vocab_dir)
        with open(vocab_dir + "vocab_freq_dict.pickle", "wb") as file:
            pickle.dump(vocab_freq_dict, file)
            file.close()

    def load_vocab(self, vocab_dir, min_frequency, max_frequency):
        with open(vocab_dir + "vocab_freq_dict.pickle", "rb") as file:
            self.vocab_freq_dict = pickle.load(file)
            file.close()
        categorical_vocab = CategoricalVocabulary()
        for word in self.vocab_freq_dict:
            categorical_vocab.add(word, count=self.vocab_freq_dict[word])
        categorical_vocab.trim(min_frequency=min_frequency,
                               max_frequency=max_frequency)
        categorical_vocab.freeze()

        vocab_processor = VocabularyProcessor(

            vocabulary=categorical_vocab,
            max_document_length=self.max_document_length,
            min_frequency=min_frequency)

        if self.padding is True:
            self.word_id_list = list(
                vocab_processor.transform_pad(self.text_list))
        else:
            self.word_id_list = list(
                vocab_processor.transform(self.text_list))
        self.word_id_list = [list(i) for i in self.word_id_list]
        return vocab_processor.vocabulary_

    def write_examples(self, file_name, split_index):
        # write to TFRecord data file
        tf.logging.info("Writing to: %s", file_name)
        with tf.python_io.TFRecordWriter(file_name) as writer:
            for index in split_index:
                feature = {
                    'label': tf.train.Feature(
                        int64_list=tf.train.Int64List(
                            value=[self.label_list[index]])),
                    'word_id': tf.train.Feature(
                        int64_list=tf.train.Int64List(
                            value=self.word_id_list[index])),
                    'old_length': tf.train.Feature(
                        int64_list=tf.train.Int64List(
                            value=[self.old_length_list[index]])),
                    'new_length': tf.train.Feature(
                        int64_list=tf.train.Int64List(
                            value=[self.new_length_list[index]])),
                }

                if self.encoding == 'bow':
                    feature['bow'] = tf.train.Feature(
                        float_list=tf.train.FloatList(
                            value=bag_of_words(
                                self.word_id_list[index],
                                self.vocab_size).tolist()))

                example = tf.train.Example(
                    features=tf.train.Features(
                        feature=feature))
                writer.write(example.SerializeToString())

    def split(self, index_path, train_ratio, valid_ratio, random_seed,
              scale_ratio):
        if not Path(index_path).exists():
            # no split given
            print("no split given")
            train_index, valid_index, test_index \
                = self.random_split_train_valid_test(len(self.text_list),
                                                     train_ratio, valid_ratio,
                                                     random_seed)

        else:
            index = json.load(gzip.open(index_path, mode='rt'))
            assert 'train' in index and 'test' in index
            train_index = index['train']
            test_index = index['test']
            if 'valid' in index:
                print("train/valid/test splits given")
                valid_index = index['valid']
            else:
                print("train/test splits given")
                train_index, valid_index = self.random_split_train_valid(
                    train_index, valid_ratio, random_seed)

        # no intersection
        assert (len(train_index) == len(set(train_index)))
        assert (len(valid_index) == len(set(valid_index)))
        assert (len(test_index) == len(set(test_index)))
        assert len([i for i in train_index if i in valid_index]) == 0
        assert len([i for i in train_index if i in test_index]) == 0
        assert len([i for i in valid_index if i in test_index]) == 0

        print("train : valid : test = %d : %d : %d" % (len(train_index),
                                                       len(valid_index),
                                                       len(test_index)))

        if scale_ratio is not None and scale_ratio < 1.0:
            train_index = self.scale(train_index, random_seed, scale_ratio)
            valid_index = self.scale(valid_index, random_seed, scale_ratio)
            test_index = self.scale(test_index, random_seed, scale_ratio)
            print("train : valid : test = %d : %d : %d" % (len(train_index),
                                                           len(valid_index),
                                                           len(test_index)))

        return train_index, valid_index, test_index

    def scale(self, index, random_seed, scale_ratio=0.1):
        np.random.seed(random_seed)
        index = np.random.permutation(index)
        return np.split(index, [int(scale_ratio * len(index))])[0]

    def random_split_train_valid_test(self, length, train_ratio, valid_ratio,
                                      random_seed):
        index = np.array(list(range(length)))
        np.random.seed(random_seed)
        index = np.random.permutation(index)

        return np.split(index,
                        [int(train_ratio * len(index)),
                         int((train_ratio + valid_ratio) * len(index))])

    def random_split_train_valid(self, train_index, valid_ratio, random_seed):
        """Takes part of training data to validation data"""
        index = np.array(train_index)
        np.random.seed(random_seed)
        index = np.random.permutation(index)
        return np.split(index, [int(1.0 - valid_ratio * len(index))])


# add the frequencies of each in two vocabulary dictionary
def merge_vocab_dict(vocab_dir_1, vocab_dir_2):
    with open(vocab_dir_1 + "vocab_freq_dict.pickle", "rb") as file:
        vocab_freq_dict_1 = pickle.load(file)
        file.close()
    with open(vocab_dir_2 + "vocab_freq_dict.pickle", "rb") as file:
        vocab_freq_dict_2 = pickle.load(file)
        file.close()
    vocab_freq_dict = combine_dicts(vocab_freq_dict_1, vocab_freq_dict_2)
    return vocab_freq_dict


def merge_save_vocab_dicts(vocab_paths, save_path):
    """
    :param vocab_paths: list of vocabulary paths
    :return:
    """
    merged_vocab_dict = dict()
    for path in vocab_paths:
        vocab_dict = pickle.load(open(path, "rb"))
        merged_vocab_dict = combine_dicts(merged_vocab_dict, vocab_dict)
    pickle.dump(merged_vocab_dict, open(save_path, 'wb'))


def combine_dicts(x, y):
    return {i: x.get(i, 0) + y.get(i, 0) for i in
            set(itertools.chain(x, y))}


def merge_dict_write_tfrecord(data_dirs, new_data_dir,
                              max_document_length=None, min_frequency=0,
                              max_frequency=-1, train_ratio=TRAIN_RATIO,
                              valid_ratio=VALID_RATIO):
    """
    1. generate and save vocab dictionary which contains all the words(
    cleaned) for each dataset
    2. merge the vocabulary
    3. generate and save TFRecord files for each dataset using the merged vocab
    :param data_dirs: list of dataset directories
    :param data_dirs: new directory to save all the data
    :return:
    """
    # generate vocab for every dataset without writing their own TFRecord files
    # the generated vocab freq dicts shall be saved at
    # data_dir/single/vocab_freq_dict.pickle
    max_document_lengths = []
    for data_dir in data_dirs:
        dataset = Dataset(data_dir, generate_basic_vocab=True,
                          generate_tf_record=False)
        max_document_lengths.append(dataset.max_document_length)

    # new data dir based all the datasets' names
    data_names = [os.path.basename(os.path.normpath(data_dir)) for data_dir
                  in data_dirs]
    data_names.sort()
    try:
        os.stat(new_data_dir)
    except:
        os.mkdir(new_data_dir)
    # new_data_dir = new_data_dir + '_'.join(data_names) + '/'
    # try:
    #     os.stat(new_data_dir)
    # except:
    #     os.mkdir(new_data_dir)

    # merge all the vocabularies
    vocab_paths = []
    for data_dir in data_dirs:
        vocab_path = os.path.join(data_dir, "single/vocab_freq_dict.pickle")
        vocab_paths.append(vocab_path)
    merge_save_vocab_dicts(vocab_paths, os.path.join(new_data_dir,
                                                     "vocab_freq_dict.pickle"))

    print("merged public vocabulary saved to path", os.path.join(new_data_dir,
                                                                 "vocab_freq_dict.pickle"))

    # write tf records
    for data_dir in data_dirs:
        tfrecord_dir = os.path.join(new_data_dir, os.path.basename(
            os.path.normpath(data_dir)))
        dataset = Dataset(data_dir,
                          vocab_dir=new_data_dir,
                          tfrecord_dir=tfrecord_dir,
                          min_frequency=min_frequency,
                          max_frequency=max_frequency,
                          max_document_length=max(max_document_lengths),
                          generate_basic_vocab=False,
                          generate_tf_record=True,
                          train_ratio=train_ratio,
                          valid_ratio=valid_ratio)


def main():
    # test
    data_dirs = ["./vocab_test/1/", "./vocab_test/2/", "./vocab_test/3/"]
    merge_dict_write_tfrecord(data_dirs, new_data_dir="./public/")


if __name__ == '__main__':
    main()
