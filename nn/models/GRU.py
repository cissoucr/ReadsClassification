from . import model, AbstractNN

import os
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.utils import plot_model

@model('gru')
class GRU(AbstractNN):
    def __init__(self, hparams):
        super(GRU, self).__init__(hparams)
        hparams = self.check_hparams(hparams)
        num_classes = len(hparams.class_mapping)

        # Create the model
        self._model = keras.Sequential(
            [
                layers.Embedding(input_dim=hparams.num_kmers, output_dim=hparams.embedding_size,
                                 input_length=hparams.vector_size, trainable=True),
                layers.RNN(layers.GRUCell(hparams.hidden_size)),
                layers.Dense(num_classes, activation='softmax')
            ]
        )
        # Output model summary to a file
        with open(os.path.join(hparams.output, 'metrics.txt'), 'w+') as f:
            self._model.summary(print_fn=lambda x: f.write(x + '\n'))
        plot_model(self._model, to_file=os.path.join(hparams.output, 'gru-model.png'),
                   show_shapes=True, show_layer_names=True)

    def call(self, strategy):
        self.running_loop(strategy)
