import tensorflow as tf

from finetune.base import BaseModel, DROPOUT_OFF
from finetune.target_encoders import MultilabelClassificationEncoder
from finetune.network_modules import multi_classifier

import warnings


class MultiLabelClassifier(BaseModel):
    """ 
    Classifies a single document into upto N of N categories.
    
    :param config: A :py:class:`finetune.config.Settings` object or None (for default config).
    :param \**kwargs: key-value pairs of config items to override.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.threshold_placeholder = None

    def featurize(self, X, max_length=None):
        """
        Embeds inputs in learned feature space. Can be called before or after calling :meth:`finetune`.

        :param X: list or array of text to embed.
        :param max_length: the number of tokens to be included in the document representation.
                           Providing more than `max_length` tokens as input will result in truncation.
        :returns: np.array of features of shape (n_examples, embedding_size).
        """
        return super().featurize(X, max_length=max_length)

    def predict(self, X, threshold=None, max_length=None):
        """
        Produces a list of most likely class labels as determined by the fine-tuned model.

        :param X: list or array of text to embed.
        :param max_length: the number of tokens to be included in the document representation.
                           Providing more than `max_length` tokens as input will result in truncation.
        :returns: list of class labels.
        """
        threshold = threshold or self.config.multi_label_threshold
        return self._predict(X, threshold=threshold, max_length=max_length)

    def predict_proba(self, X, max_length=None):
        """
        Produces a probability distribution over classes for each example in X.

        :param X: list or array of text to embed.
        :param max_length: the number of tokens to be included in the document representation.
                           Providing more than `max_length` tokens as input will result in truncation.
        :returns: list of dictionaries.  Each dictionary maps from a class label to its assigned class probability.
        """
        return super().predict_proba(X, max_length=max_length)

    def finetune(self, X, Y=None, batch_size=None):
        """
        :param X: list or array of text.
        :param Y: A list of lists containing labels for the corresponding X
        :param batch_size: integer number of examples per batch. When N_GPUS > 1, this number
                           corresponds to the number of training examples provided to each GPU.
        """
        return super().finetune(X, Y=Y, batch_size=batch_size)

    def _target_encoder(self):
        return MultilabelClassificationEncoder()

    def _target_model(self, featurizer_state, targets, n_outputs, train=False, reuse=None, **kwargs):
        return multi_classifier(
            hidden=featurizer_state['features'],
            targets=targets,
            n_targets=n_outputs,
            dropout_placeholder=self.do_dropout,
            config=self.config,
            train=train,
            reuse=reuse,
            **kwargs
        )

    def _predict_op(self, logits, **kwargs):
        self.threshold_placeholder = tf.placeholder(tf.float32)
        return tf.cast(tf.nn.sigmoid(logits) > self.threshold_placeholder, tf.int32)

    def _predict_proba_op(self, logits, **kwargs):
        return tf.nn.sigmoid(logits)

    def _predict(self, X, threshold, max_length=None):
        predictions = []
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            max_length = max_length or self.config.max_length
            for xmb, mmb in self._infer_prep(X, max_length=max_length):
                output = self._eval(
                    self.predict_op,
                    feed_dict={
                        self.X: xmb,
                        self.M: mmb,
                        self.do_dropout: DROPOUT_OFF,
                        self.threshold_placeholder: threshold
                    }
                )
                prediction = output.get(self.predict_op)
                formatted_predictions = self.label_encoder.inverse_transform(prediction)
                predictions.extend(formatted_predictions)
        return predictions
