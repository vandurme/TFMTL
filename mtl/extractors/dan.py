# Copyright 2018 Johns Hopkins University. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either exprpress or  implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================

import tensorflow as tf
from six.moves import xrange

from mtl.layers import dense_layer
from mtl.util.common import validate_extractor_inputs
from mtl.util.constants import REDUCERS


def reduce(inputs, lengths, reducer):
    assert reducer in REDUCERS, "unrecognized dan reducer: %s" % reducer

    if len(lengths.get_shape()) == 1:
        lengths = tf.expand_dims(lengths, 1)

    s_embedding = reducer(inputs, lengths=lengths, time_axis=1)

    return s_embedding


def word_dropout(sequence, word_dropout_rate):
    """randomly dropout word tokens in a sequence

    :param sequence: [sequence_length, embed_dim]
    :param word_dropout_rate:
    :return:
    """

    # TODO

    print(sequence.shape)
    mask = None
    return sequence


def dan(inputs,
        lengths,
        word_dropout_rate,
        reducer,
        apply_activation,
        num_layers,
        activation_fns):
    """
    TODO fill out comment
    TODO wordcount too much None
    https://www.cs.umd.edu/~miyyer/pubs/2015_acl_dan.pdf

    :param inputs:
    :param lengths:
    :param word_dropout_rate:
    :param reducer:
    :param apply_activation: whether to add layers
    :param num_layers:
    :param activation_fns:
    :return:
    """
    validate_extractor_inputs(inputs, lengths)

    if apply_activation:
        assert len(activation_fns) == num_layers, \
            'Length of apply_activations ' + str(len(activation_fns)) + \
            ' doesn\'t match num_layers ' + str(num_layers) + '!'

    # TODO word dropout test
    # TODO test two-input sequence
    assert 0.0 <= word_dropout_rate < 1.0, \
        'Word dropout rate must be in [0.0, 1.0) !'

    for i, x in enumerate(inputs):
        input_shape = tf.shape(x)
        batch_size = input_shape[0]
        n_time_steps = input_shape[1]
        mask = tf.random_uniform(
            (batch_size, n_time_steps, 1)) >= word_dropout_rate
        print(mask)
        x = tf.cast(mask, 'float32') * x
        inputs[i] = x

    # all examples must have at least one word
    assert len(inputs) > 0

    num_stages = len(inputs)
    outputs = []
    prev_varscope = None
    for n_stage in xrange(num_stages):
        with tf.variable_scope("dan-seq{}".format(n_stage)) as varscope:
            if prev_varscope is not None:
                prev_varscope.reuse_variables()
            p = reduce(inputs[n_stage],
                       lengths[n_stage],
                       reducer=reducer)
            outputs.append(p)
            prev_varscope = varscope

    ranks = [len(p.get_shape()) for p in outputs]
    assert all(rank == 2 for rank in ranks)  # <batch_size, embed_dim>
    outputs = tf.concat(outputs, axis=1)

    if apply_activation:
        for num_layer, activation_fn in zip(xrange(num_layers),
                                            activation_fns):
            if num_layers == 1:
                layer_name = 'dan-output'
            else:
                layer_name = "dan-output-" + str(num_layer)
            outputs = dense_layer(outputs,
                                  outputs.get_shape().as_list()[1],
                                  # keep same dimensionality
                                  name=layer_name,
                                  activation=activation_fn)

    return outputs