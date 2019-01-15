import tensorflow as tf
import numpy as np

from finetune.base import BaseModel
from finetune.target_encoders import OrdinalRegressionEncoder
from finetune.network_modules import ordinal_regressor, regressor
from finetune.input_pipeline import BasePipeline
from finetune.regressor import RegressionPipeline
from finetune.network_modules import multi_classifier
from comparison_regressor import ComparisonRegressionPipeline

class OrdinalRegressionPipeline(BasePipeline):
    def _target_encoder(self):
        return OrdinalRegressionEncoder()
    
class MultiOrdinalRegressionPipeline(ComparisonRegressionPipeline):
    def _target_encoder(self):
        return OrdinalRegressionEncoder()

class OrdinalRegressor(BaseModel):
    """ 
    Regresses one or more floating point values given a single document.

    For a full list of configuration options, see `finetune.config`.

    :param config: A config object generated by `finetune.config.get_config` or None (for default config).
    :param \**kwargs: key-value pairs of config items to override.
    """        
    def _get_input_pipeline(self):
        return OrdinalRegressionPipeline(self.config)

    def featurize(self, X):
        """
        Embeds inputs in learned feature space. Can be called before or after calling :meth:`finetune`.

        :param X: list or array of text to embed.
        :returns: np.array of features of shape (n_examples, embedding_size).
        """
        return self._featurize(X)

    def predict(self, X):
        """
        Produces a list of most likely class labels as determined by the fine-tuned model.

        :param X: list or array of text to embed.
        :returns: list of class labels.
        """
        return super().predict(X).tolist()

    def predict_proba(self, X):
        """
        Produces a probability distribution over classes for each example in X.

        :param X: list or array of text to embed.
        :returns: list of dictionaries.  Each dictionary maps from a class label to its assigned class probability.
        """
        raise AttributeError("`Regressor` model does not support `predict_proba`.")

    def finetune(self, X, Y=None, batch_size=None):
        """
        :param X: list or array of text.
        :param Y: floating point targets
        :param batch_size: integer number of examples per batch. When N_GPUS > 1, this number
                           corresponds to the number of training examples provided to each GPU.
        """
        return super().finetune(X, Y=Y, batch_size=batch_size)


    def _target_model(self, featurizer_state, targets, n_outputs, train=False, reuse=None, **kwargs):
        return ordinal_regressor(
            hidden=featurizer_state['features'],
            targets=targets,
            n_targets=n_outputs,
            config=self.config,
            train=train,
            reuse=reuse,
            **kwargs
        )

    def _predict_op(self, logits, **kwargs):
        return logits

    def _predict_proba_op(self, logits, **kwargs):
        return logits
    
class MultiOrdinalRegressor(OrdinalRegressor):
    """
    for comparison
    """
    def _get_input_pipeline(self):
        return MultiOrdinalRegressionPipeline(self.config)
    
    def _target_model(self, featurizer_state, targets, n_outputs, train=False, reuse=None, **kwargs):
        featurizer_state["sequence_features"] = tf.abs(tf.reduce_sum(featurizer_state["sequence_features"], 1))
        featurizer_state["features"] = tf.abs(tf.reduce_sum(featurizer_state["features"], 1))
        return ordinal_regressor(
            hidden=featurizer_state['features'],
            targets=targets,
            n_targets=n_outputs,
            config=self.config,
            train=train,
            reuse=reuse,
            **kwargs
        )
    
