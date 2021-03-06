# -*- coding: utf-8 -*-

# Copyright 2017 ComputerGraphics Tuebingen. All Rights Reserved.
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
# Authors: Fabian Groh, Patrick Wieschollek, Hendrik P.A. Lensch


import tensorflow as tf
from user_ops import flex_convolution as _flex_convolution
from user_ops import flex_pooling as _flex_pooling
from user_ops import flex_convolution_transpose as _flex_convolution_transpose

from tensorflow.python.keras import activations
from tensorflow.python.keras import initializers
from tensorflow.python.keras.engine.base_layer import Layer
from tensorflow.python.util.tf_export import tf_export
from tensorflow.python.framework import tensor_shape
from tensorflow.python.framework import ops


all = ['FlexPooling', 'FlexConvolution', 'FlexConvolutionTranspose',
       'flex_pooling', 'flex_convolution', 'flex_convolution_transpose']


def _remove_dim(x, axis=2):
  return tf.squeeze(x, axis=axis)


@tf_export('keras.layers.FlexPooling')
class FlexPooling(Layer):
  """flex pooling layer.

  This layer performs a max-pooling operation over elements in arbitrary
  neighborhoods. When `data_format` is 'simple', the input shape should
  have rank 3, otherwise rank 4 and dimension 2 should be 1.

  Remarks:
      In contrast to traditional pooling, this operation has no option for
      sub-sampling.

  Arguments:
      features: A `Tensor` of the format [B, Din, (1), N].
      neighborhoods: A `Tensor` of the format [B, K, (1), N] (tf.int32).
      name: A string, the name of the layer.

  """

  def __init__(self,
               features,
               neighborhoods,
               data_format='simple',
               name=None):

    super(FlexPooling, self).__init__(name=name)
    self.features = features
    self.neighborhoods = neighborhoods
    self.data_format = data_format

  def compute_output_shape(self, input_shape):
    return tensor_shape.TensorShape(input_shape)

  def build(self, input_shape):
    self.built = True

  def call(self, inputs):
    if not isinstance(inputs, list):
      raise ValueError('A flexconv layer should be called '
                       'on a list of inputs.')

    features = ops.convert_to_tensor(inputs[0], dtype=self.dtype)
    neighborhoods = ops.convert_to_tensor(inputs[1], dtype=tf.int32)

    if self.data_format == 'expanded':
      features = _remove_dim(features, 2)
      neighborhoods = _remove_dim(neighborhoods, 2)

    y, _ = _flex_pooling(features, neighborhoods)

    if self.data_format == 'expanded':
      y = tf.expand_dims(y, axis=2)

    return y


def flex_pooling(features,
                 neighborhoods,
                 data_format='simple',
                 name=None):

  layer = FlexPooling(features,
                      neighborhoods,
                      data_format=data_format,
                      name=name)

  return layer.apply([features, neighborhoods])


@tf_export('keras.layers.FlexConvolution')
class FlexConvolution(Layer):
  """flex convolution layer.

  This layer convolves elements in arbitrary neighborhoods with a kernel to
  produce a tensor of outputs.
  If `use_feature_bias` is True (and a `features_bias_initializer` is provided),
  a bias vector is created and added to the outputs after te convolution.
  Finally, if `activation` is not `None`, it is applied to the outputs as well.
  When `data_format` is 'simple', the input shape should have rank 3,
  otherwise rank 4 and dimension 2 should be 1.

  Remarks:
      In contrast to traditional convolutions, this operation has two
      bias terms:
        - bias term when dynamically computing the weight [Din, Dout]
        - bias term which is added tot the features [Dout]

  Arguments:
      features: A `Tensor` of the format [B, Din, (1), N].
      positions: A `Tensor` of the format [B, Dp, (1), N].
      neighborhoods: A `Tensor` of the format [B, K, (1), N] (tf.int32).
      filters: Integer, the dimensionality of the output space (i.e. the number
        of filters in the convolution).
      activation: Activation function. Set it to None to maintain a
        linear activation.
      kernel_initializer: An initializer for the convolution kernel.
      position_bias_initializer: An initializer for the bias vector within
        the convolution. If None, the default initializer will be used.
      features_bias_initializer: An initializer for the bias vector after
        the convolution. If None, the default initializer will be used.
      use_feature_bias: Boolean, whether the layer uses a bias.
      data_format: A string, one of `simple` (default) or `expaned`.
        If `simple` the shapes are [B, Din, N], when `expanded` the shapes
        are assumed to be [B, Din, 1, N] to match `channels_first` in trad
        convolutions.
      trainable: Boolean, if `True` also add variables to the graph collection
        `GraphKeys.TRAINABLE_VARIABLES` (see `tf.Variable`).
      name: A string, the name of the layer.

  """

  def __init__(self,
               features,
               positions,
               neighborhoods,
               filters,
               activation=None,
               kernel_initializer=None,
               position_bias_initializer=tf.zeros_initializer(),
               features_bias_initializer=tf.zeros_initializer(),
               use_feature_bias=True,
               data_format='simple',
               trainable=True,
               name=None):

    super(FlexConvolution, self).__init__(trainable=trainable,
                                          name=name)
    self.features = features
    self.positions = positions
    self.neighborhoods = neighborhoods

    self.filters = int(filters)
    self.activation = activations.get(activation)
    self.use_feature_bias = use_feature_bias
    self.data_format = data_format
    self.kernel_initializer = initializers.get(kernel_initializer)
    self.position_bias_initializer = initializers.get(position_bias_initializer)
    self.features_bias_initializer = initializers.get(features_bias_initializer)

  def compute_output_shape(self, input_shape):
    input_shape = tensor_shape.TensorShape(input_shape)
    input_shape[1] = self.filters
    return input_shape

  def build(self, input_shape):
    if self.data_format == 'expanded':
      features = _remove_dim(self.features, 2)
      positions = _remove_dim(self.positions, 2)
    else:
      features = self.features
      positions = self.positions
    [B, Din, N] = features.shape
    Din = int(Din)
    N = int(N)
    Dp = int(positions.shape[1])
    Dout = self.filters

    self.position_theta = self.add_weight(
        'position_theta',
        shape=[1, Dp, Din, Dout],
        initializer=self.kernel_initializer,
        dtype=self.dtype,
        trainable=True)

    self.position_bias = self.add_weight(
        'position_bias',
        shape=[Din, Dout],
        initializer=self.position_bias_initializer,
        dtype=self.dtype,
        trainable=True)

    if self.use_feature_bias:
      self.feature_bias = self.add_weight(
          'feature_bias',
          shape=[Dout, 1],
          initializer=self.features_bias_initializer,
          dtype=self.dtype,
          trainable=True)
    else:
      self.feature_bias = None
    self.built = True

  def call(self, inputs):

    if not isinstance(inputs, list):
      raise ValueError('A flexconv layer should be called '
                       'on a list of inputs.')

    features = ops.convert_to_tensor(inputs[0], dtype=self.dtype)
    positions = ops.convert_to_tensor(inputs[1], dtype=self.dtype)
    neighborhoods = ops.convert_to_tensor(inputs[2], dtype=tf.int32)

    if self.data_format == 'expanded':
      features = _remove_dim(features, 2)
      positions = _remove_dim(positions, 2)
      neighborhoods = _remove_dim(neighborhoods, 2)

    y = _flex_convolution(features, positions, neighborhoods,
                          self.position_theta, self.position_bias)

    if self.use_feature_bias:
      y = tf.add(y, self.feature_bias)

    if self.activation is not None:
      y = self.activation(y)

    if self.data_format == 'expanded':
      y = tf.expand_dims(y, axis=2)

    return y


def flex_convolution(features,
                     positions,
                     neighborhoods,
                     filters,
                     activation=None,
                     kernel_initializer=None,
                     position_bias_initializer=tf.zeros_initializer(),
                     features_bias_initializer=tf.zeros_initializer(),
                     use_feature_bias=True,
                     data_format='simple',
                     trainable=True,
                     name=None):

  layer = FlexConvolution(features,
                          positions,
                          neighborhoods,
                          filters,
                          activation=activation,
                          kernel_initializer=kernel_initializer,
                          position_bias_initializer=position_bias_initializer,
                          features_bias_initializer=features_bias_initializer,
                          use_feature_bias=use_feature_bias,
                          data_format=data_format,
                          trainable=trainable,
                          name=name)

  return layer.apply([features, positions, neighborhoods])


@tf_export('keras.layers.FlexConvolutionTranspose')
class FlexConvolutionTranspose(FlexConvolution):
  """flex convolution-transpose layer.

  This layer applies a transpose convolution to elements in arbitrary
  neighborhoods.
  If `use_feature_bias` is True (and a `features_bias_initializer` is provided),
  a bias vector is created and added to the outputs after te convolution.
  Finally, if `activation` is not `None`, it is applied to the outputs as well.
  When `data_format` is 'simple', the input shape should have rank 3,
  otherwise rank 4 and dimension 2 should be 1.

  Remarks:
      In contrast to traditional transposed convolutions, this operation has two
      bias terms:
        - bias term when dynamically computing the weight [Din, Dout]
        - bias term which is added tot the features [Dout]

  Arguments:
      features: A `Tensor` of the format [B, Din, (1), N].
      positions: A `Tensor` of the format [B, Dp, (1), N].
      neighborhoods: A `Tensor` of the format [B, K, (1), N] (tf.int32).
      filters: Integer, the dimensionality of the output space (i.e. the number
        of filters in the convolution).
      activation: Activation function. Set it to None to maintain a
        linear activation.
      kernel_initializer: An initializer for the convolution kernel.
      position_bias_initializer: An initializer for the bias vector within
        the convolution. If None, the default initializer will be used.
      features_bias_initializer: An initializer for the bias vector after
        the convolution. If None, the default initializer will be used.
      use_feature_bias: Boolean, whether the layer uses a bias.
      data_format: A string, one of `simple` (default) or `expaned`.
        If `simple` the shapes are [B, Din, N], when `expanded` the shapes
        are assumed to be [B, Din, 1, N] to match `channels_first` in trad
        convolutions.
      trainable: Boolean, if `True` also add variables to the graph collection
        `GraphKeys.TRAINABLE_VARIABLES` (see `tf.Variable`).
      name: A string, the name of the layer.

  """

  def call(self, inputs):

    if not isinstance(inputs, list):
      raise ValueError('A flexconv layer should be called '
                       'on a list of inputs.')

    features = ops.convert_to_tensor(inputs[0], dtype=self.dtype)
    positions = ops.convert_to_tensor(inputs[1], dtype=self.dtype)
    neighborhoods = ops.convert_to_tensor(inputs[2], dtype=tf.int32)

    if self.data_format == 'expanded':
      features = _remove_dim(features, 2)
      positions = _remove_dim(positions, 2)
      neighborhoods = _remove_dim(neighborhoods, 2)

    y = _flex_convolution_transpose(features, positions, neighborhoods,
                                    self.position_theta, self.position_bias)

    if self.use_feature_bias:
      y = tf.add(y, self.feature_bias)

    if self.activation is not None:
      y = self.activation(y)

    if self.data_format == 'expanded':
      y = tf.expand_dims(y, axis=2)

    return y


def flex_convolution_transpose(features,
                               positions,
                               neighborhoods,
                               filters,
                               activation=None,
                               kernel_initializer=None,
                               position_bias_initializer=tf.zeros_initializer(),
                               features_bias_initializer=tf.zeros_initializer(),
                               use_feature_bias=True,
                               data_format='simple',
                               trainable=True,
                               name=None):

  layer = FlexConvolutionTranspose(features,
                                   positions,
                                   neighborhoods,
                                   filters,
                                   activation=activation,
                                   kernel_initializer=kernel_initializer,
                                   position_bias_initializer=position_bias_initializer,
                                   features_bias_initializer=features_bias_initializer,
                                   use_feature_bias=use_feature_bias,
                                   data_format=data_format,
                                   trainable=trainable,
                                   name=name)

  return layer.apply([features, positions, neighborhoods])
