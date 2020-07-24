# Copyright 2020 The AutoKeras Authors.
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

import numpy as np
# from tensorflow.python.keras.engine.base_preprocessing_layer import CombinerPreprocessingLayer
import tensorflow as tf
from tensorflow.keras.layers.experimental import preprocessing
from tensorflow.python.util import nest

INT = "int"
NONE = "none"
ONE_HOT = "one-hot"


@tf.keras.utils.register_keras_serializable()
class MultiCategoryEncoding(preprocessing.PreprocessingLayer):
    """Encode the categorical features to numerical features.

    # Arguments
        encoding: A list of strings, which has the same number of elements as the
            columns in the structured data. Each of the strings specifies the
            encoding method used for the corresponding column. Use 'int' for
            categorical columns and 'none' for numerical columns.
    """

    # TODO: Support one-hot encoding.
    # TODO: Support frequency encoding.

    def __init__(self, encoding, **kwargs):
        super().__init__(**kwargs)
        self.encoding = encoding
        self.encoding_layers = []
        for encoding in self.encoding:
            if encoding == NONE:
                self.encoding_layers.append(None)
            elif encoding == INT:
                self.encoding_layers.append(preprocessing.StringLookup())
            elif encoding == ONE_HOT:
                self.encoding_layers.append(None)

    def build(self, input_shape):
        for encoding_layer in self.encoding_layers:
            if encoding_layer is not None:
                encoding_layer.build(tf.TensorShape([1]))

    def call(self, inputs):
        input_nodes = nest.flatten(inputs)[0]
        split_inputs = tf.split(input_nodes, [1] * len(self.encoding), axis=-1)
        output_nodes = []
        for input_node, encoding_layer in zip(split_inputs, self.encoding_layers):
            if encoding_layer is None:
                number = tf.strings.to_number(input_node, tf.float32)
                # Replace NaN with 0.
                imputed = tf.where(
                    tf.math.is_nan(number), tf.zeros_like(number), number
                )
                output_nodes.append(imputed)
            else:
                output_nodes.append(tf.cast(encoding_layer(input_node), tf.float32))
        if len(output_nodes) == 1:
            return output_nodes[0]
        return tf.keras.layers.Concatenate()(output_nodes)

    def adapt(self, data):
        for index, encoding_layer in enumerate(self.encoding_layers):
            if encoding_layer is None:
                continue
            data_column = data.map(lambda x: tf.slice(x, [0, index], [-1, 1]))
            encoding_layer.adapt(data_column)

    def get_config(self):
        config = {
            "encoding": self.encoding,
        }
        base_config = super().get_config()
        return dict(list(base_config.items()) + list(config.items()))


CUSTOM_OBJECTS = {
    'MultiColumnCategoricalEncoding': MultiColumnCategoricalEncoding,
    'IndexLookup': index_lookup.IndexLookup,
}


class TextVectorizationWithTokenizer(preprocessing.PreprocessingLayer):
    """
    tokenizer = bert.tokenization.FullTokenizer(
        vocab_file=os.path.join(gs_folder_bert, "vocab.txt"),
        do_lower_case=True)
    """

    def __init__(self, tokenizer):
        super().__init__()
        self.tokenizer = tokenizer

    def build(self, input_shape):
        print("build function called: ",input_shape)
        # for encoding_layer in self.encoding_layers:
        #     if encoding_layer is not None:
        #         encoding_layer.build(tf.TensorShape([1]))

    def call(self, inputs):

        return self.bert_encode(inputs)

    def encode_sentence(self, s):
        tokens = list(self.tokenizer.tokenize(s))
        tokens.append('[SEP]')  # change these tokens
        return self.tokenizer.convert_tokens_to_ids(tokens)

    def bert_encode(self, input):
        num_examples = len(input)
        print(num_examples, input.shape)
        sentence1 = tf.ragged.constant([
            self.encode_sentence(s)
            for s in np.array(input)])

        cls = [self.tokenizer.convert_tokens_to_ids(
            ['[CLS]'])] * sentence1.shape[0]  # change
        input_word_ids = tf.concat([cls, sentence1], axis=-1)

        input_mask = tf.ones_like(input_word_ids).to_tensor()

        type_cls = tf.zeros_like(cls)
        type_s1 = tf.zeros_like(sentence1)
        input_type_ids = tf.concat(
            [type_cls, type_s1], axis=-1).to_tensor()

        inputs = {
            'input_word_ids': input_word_ids.to_tensor(),
            'input_mask': input_mask,
            'input_type_ids': input_type_ids}

        return inputs
