# -*- coding: UTF-8 -*-
# @Time    : 2019/1/11 1:47 PM
# @File    : branch.py
# @Author  : jian<jian@mltalker.com>
from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function
from antgo.automl.basestublayers import *
import random


class Branch(StubLayer):
  LAYER_ENCODER_RANGE = (0.01, 0.09)

  def __init__(self, input=None, output=None, **kwargs):
    super(Branch, self).__init__(input, output, **kwargs)
    self.branch_name = kwargs.get('branch_name', '')

  def encoder_scale(self, value, bias):
    # value in [0,1]
    return value * (Branch.LAYER_ENCODER_RANGE[1] - Branch.LAYER_ENCODER_RANGE[0]) + Branch.LAYER_ENCODER_RANGE[0] + bias

class DummyNode(object):
  def __init__(self, shape, id=-1):
    self.shape = shape
    self.id = id


class ConvBnBranch(Branch):
  def __init__(self, output_channel, input=None, output=None, **kwargs):
    super(ConvBnBranch, self).__init__(input, output, **kwargs)
    self.layer_name = 'convbn_branch'

    self.output_channel = output_channel
    self.layer_1 = BaseStubConv2d(None,
                                  self.output_channel,
                                  1,
                                  1,
                                  cell_name=self.cell_name,
                                  block_name=self.block_name,
                                  group=self)
    self.layer_2 = BaseStubBatchNormalization2d(cell_name=self.cell_name,
                                                block_name=self.block_name,
                                                group=self)
    self.layer_3 = BaseStubReLU(cell_name=self.cell_name,
                                block_name=self.block_name,
                                group=self)

  @property
  def output_shape(self):
    self.layer_1.input = self.input
    self.layer_2.input = DummyNode(self.layer_1.output_shape)
    self.layer_3.input = DummyNode(self.layer_2.output_shape)
    return self.layer_3.output_shape

  def flops(self):
    self.layer_1.input = self.input
    self.layer_2.input = DummyNode(self.layer_1.output_shape)
    self.layer_3.input = DummyNode(self.layer_2.output_shape)
    return self.layer_1.flops() + self.layer_2.flops() + self.layer_3.flops()

  def __call__(self, *args, **kwargs):
    # layer_1_c = self.layer_factory.conv2d(None, self.output_channel, 1, 1, cell_name=self.cell_name, block_name=self.block_name)
    # layer_1 = layer_1_c(*args, **kwargs)
    #
    # layer_2_c = self.layer_factory.bn2d(cell_name=self.cell_name, block_name=self.block_name)
    # layer_2 = layer_2_c(layer_1)
    #
    # layer_3_c = self.layer_factory.relu(cell_name=self.cell_name, block_name=self.block_name)
    # layer_3 = layer_3_c(layer_2)
    # return layer_3

    layer_1_tensor = self.layer_1(*args, **kwargs)
    layer_2_tensor = self.layer_2(layer_1_tensor)
    layer_3_tensor = self.layer_3(layer_2_tensor)
    return layer_3_tensor

  @property
  def layer_type_encoder(self):
    # 0 ~ 0.1
    return 0.05


class SeperableConvBranch(Branch):
  def __init__(self, output_channel, input=None, output=None, **kwargs):
    super(SeperableConvBranch, self).__init__(input, output, **kwargs)
    self.layer_name = 'seperableconv_branch'

    # 3x3 atrous separable convolution
    # rate 1,3,6,9,12,15,18,21
    if 'rate_h' not in kwargs:
      rate_list = [1, 3, 6, 9, 12, 15, 18, 21]
      self.rate_h_index = random.randint(0, len(rate_list) - 1)
      self.rate_h = rate_list[self.rate_h_index]
      self.rate_w_index = random.randint(0, len(rate_list) - 1)
      self.rate_w = rate_list[self.rate_w_index]
    else:
      self.rate_h = kwargs['rate_h']
      self.rate_w = kwargs['rate_w']
      self.rate_h_index = kwargs['rate_h_index']
      self.rate_w_index = kwargs['rate_w_index']

    self.output_channel = output_channel
    self.layer_1 = BaseStubSeparableConv2d(input_channel=None,
                                           filters=self.output_channel,
                                           kernel_size_h=3,
                                           kernel_size_w=3,
                                           rate_h=self.rate_h,
                                           rate_w=self.rate_w,
                                           cell_name=self.cell_name,
                                           block_name=self.block_name,
                                           group=self)

    self.layer_2 = BaseStubBatchNormalization2d(cell_name=self.cell_name,
                                                block_name=self.block_name,
                                                group=self)
    self.layer_3 = BaseStubReLU(cell_name=self.cell_name,
                                block_name=self.block_name,
                                group=self)

  @property
  def output_shape(self):
    self.layer_1.input = self.input
    self.layer_2.input = DummyNode(self.layer_1.output_shape)
    self.layer_3.input = DummyNode(self.layer_2.output_shape)
    return self.layer_3.output_shape

  def flops(self):
    self.layer_1.input = self.input
    self.layer_2.input = DummyNode(self.layer_1.output_shape)
    self.layer_3.input = DummyNode(self.layer_2.output_shape)
    return self.layer_1.flops() + self.layer_2.flops() + self.layer_3.flops()

  def __call__(self, *args, **kwargs):
    # layer_1_c = self.layer_factory.separable_conv2d(input_channel=None,
    #                                                 filters=self.output_channel,
    #                                                 kernel_size_h=3,
    #                                                 kernel_size_w=3,
    #                                                 rate_h=self.rate_h,
    #                                                 rate_w=self.rate_w,
    #                                                 cell_name=self.cell_name,
    #                                                 block_name=self.block_name)
    # layer_1 = layer_1_c(*args, **kwargs)
    #
    # layer_2_c = self.layer_factory.bn2d(cell_name=self.cell_name, block_name=self.block_name)
    # layer_2 = layer_2_c(layer_1)
    #
    # layer_3_c = self.layer_factory.relu(cell_name=self.cell_name, block_name=self.block_name)
    # layer_3 = layer_3_c(layer_2)

    layer_1_tensor = self.layer_1(*args, **kwargs)
    layer_2_tensor = self.layer_2(layer_1_tensor)
    layer_3_tensor = self.layer_3(layer_2_tensor)

    return layer_3_tensor

  @property
  def layer_type_encoder(self):
    # 0.1 ~ 0.2
    return self.encoder_scale((self.rate_h_index * 8 + self.rate_w_index) / 63.0, 0.1)


class SPPBranch(Branch):
  def __init__(self, input=None, output=None, **kwargs):
    super(SPPBranch, self).__init__(input, output, **kwargs)
    # spatial pyramid pooling
    # shape = clone_graph.node_list[output_node_id].shape
    # min_hw = min(shape[1], shape[2])
    self.layer_name = 'spp_branch'

    if 'grid_h' not in kwargs:
      gh = [1, 2, 4, 8]
      # gh = [n for n in gh if n < min_hw]
      self.grid_h_index = random.randint(0, len(gh) - 1)
      self.grid_h = gh[self.grid_h_index]

      gw = [1, 2, 4, 8]
      # gw = [n for n in gw if n < min_hw]
      self.grid_w_index = random.randint(0, len(gw) - 1)
      self.grid_w = gw[self.grid_w_index]
    else:
      self.grid_h = kwargs['grid_h']
      self.grid_w = kwargs['grid_w']
      self.grid_h_index = kwargs['grid_h_index']
      self.grid_w_index = kwargs['grid_w_index']

    self.layer_1 = BaseStubSPP(grid_h=self.grid_h,
                               grid_w=self.grid_w,
                               cell_name=self.cell_name,
                               block_name=self.block_name,
                               group=self)

  @property
  def output_shape(self):
    self.layer_1.input = self.input
    return self.layer_1.output_shape

  def flops(self):
    self.layer_1.input = self.input
    return self.layer_1.flops()

  def __call__(self, *args, **kwargs):
    # layer_1_c = self.layer_factory.spp(grid_h=self.grid_h,
    #                                    grid_w=self.grid_w,
    #                                    cell_name=self.cell_name,
    #                                    block_name=self.block_name)
    # layer_1_c.input = self.input
    # layer_1 = layer_1_c(*args, **kwargs)
    self.layer_1.input = self.input
    layer_1_tensor = self.layer_1(*args, **kwargs)
    return layer_1_tensor

  @property
  def layer_type_encoder(self):
    # 0.2 ~ 0.3
    return self.encoder_scale((self.grid_h_index * 4 + self.grid_w_index) / 15.0, 0.2)


class FocusBranch(Branch):
  def __init__(self, output_channel, input=None, output=None, **kwargs):
    super(FocusBranch, self).__init__(input, output, **kwargs)
    self.layer_name = 'focus_branch'

    self.output_channel = output_channel
    if 'rate_list' not in kwargs:
      candidate_rate_list = [1, 2, 4, 6, 8]
      self.rate_list = random.sample(candidate_rate_list, 3)
      self.rate_list = sorted(self.rate_list)
    else:
      self.rate_list = kwargs['rate_list']

    self.group_1_conv = BaseStubSeparableConv2d(input_channel=None,
                                                filters=self.output_channel,
                                                kernel_size_h=3,
                                                kernel_size_w=3,
                                                rate_h=self.rate_list[0],
                                                rate_w=self.rate_list[0],
                                                cell_name=self.cell_name,
                                                block_name=self.block_name,
                                                group=self)

    self.group_1_bn = BaseStubBatchNormalization2d(cell_name=self.cell_name,block_name=self.block_name,group=self)
    self.group_1_relu = BaseStubReLU(cell_name=self.cell_name, block_name=self.block_name,group=self)

    self.group_2_conv = BaseStubSeparableConv2d(input_channel=None,
                                                filters=self.output_channel,
                                                kernel_size_h=3,
                                                kernel_size_w=3,
                                                rate_h=self.rate_list[1],
                                                rate_w=self.rate_list[1],
                                                cell_name=self.cell_name,
                                                block_name=self.block_name,
                                                group=self)
    self.group_2_bn = BaseStubBatchNormalization2d(cell_name=self.cell_name,block_name=self.block_name,group=self)
    self.group_2_relu = BaseStubReLU(cell_name=self.cell_name, block_name=self.block_name, group=self)

    self.group_12_add = BaseStubAdd(group=self)
    self.group_3_conv = BaseStubSeparableConv2d(input_channel=None,
                                                filters=self.output_channel,
                                                kernel_size_h=3,
                                                kernel_size_w=3,
                                                rate_h=self.rate_list[2],
                                                rate_w=self.rate_list[2],
                                                cell_name=self.cell_name,
                                                block_name=self.block_name,
                                                group=self)
    self.group_3_bn = BaseStubBatchNormalization2d(cell_name=self.cell_name,block_name=self.block_name,group=self)
    self.group_3_relu = BaseStubReLU(cell_name=self.cell_name, block_name=self.block_name, group=self)

    self.group_4_12_add = BaseStubAdd(group=self)
    self.group_4_123_add = BaseStubAdd(group=self)

  @property
  def output_shape(self):
    return (self.input.shape[0], self.input.shape[1], self.input.shape[2], self.output_channel)

  def flops(self):
    self.group_1_conv.input = self.input
    self.group_1_bn.input = DummyNode(self.group_1_conv.output_shape)
    self.group_1_relu.input = DummyNode(self.group_1_bn.output_shape)

    self.group_2_conv.input = DummyNode(self.group_1_relu.output_shape)
    self.group_2_bn.input = DummyNode(self.group_2_conv.output_shape)
    self.group_2_relu.input = DummyNode(self.group_2_bn.output_shape)

    self.group_12_add.input = [DummyNode(self.group_1_relu.output_shape), DummyNode(self.group_2_relu.output_shape)]
    self.group_3_conv.input = DummyNode(self.group_12_add.output_shape)
    self.group_3_bn.input = DummyNode(self.group_3_conv.output_shape)
    self.group_3_relu.input = DummyNode(self.group_3_bn.output_shape)

    self.group_4_12_add.input = [DummyNode(self.group_1_relu.output_shape), DummyNode(self.group_2_relu.output_shape)]
    self.group_4_123_add.input = [DummyNode(self.group_3_relu.output_shape), DummyNode(self.group_4_12_add.output_shape)]

    return self.group_1_conv.flops() + \
           self.group_1_bn.flops() + \
           self.group_1_relu.flops() +\
           self.group_2_conv.flops() + \
           self.group_2_bn.flops() +\
           self.group_2_relu.flops() +\
           self.group_12_add.flops()+ \
           self.group_3_conv.flops()+\
           self.group_3_bn.flops()+\
           self.group_3_relu.flops()+\
           self.group_4_12_add.flops()+\
           self.group_4_123_add.flops()

  def __call__(self, *args, **kwargs):
    # # group 1
    # group_1_conv_c = self.layer_factory.separable_conv2d(input_channel=None,
    #                                                 filters=self.output_channel,
    #                                                 kernel_size_h=3,
    #                                                 kernel_size_w=3,
    #                                                 rate_h=self.rate_list[0],
    #                                                 rate_w=self.rate_list[0],
    #                                                 cell_name=self.cell_name,
    #                                                 block_name=self.block_name)
    # group_1_conv = group_1_conv_c(*args, **kwargs)
    #
    # group_1_bn_c = self.layer_factory.bn2d(cell_name=self.cell_name, block_name=self.block_name)
    # group_1_bn = group_1_bn_c(group_1_conv)
    #
    # group_1_relu_c = self.layer_factory.relu(cell_name=self.cell_name, block_name=self.block_name)
    # group_1_relu = group_1_relu_c(group_1_bn)
    #
    # # group 2
    # group_2_conv_c = self.layer_factory.separable_conv2d(input_channel=None,
    #                                                 filters=self.output_channel,
    #                                                 kernel_size_h=3,
    #                                                 kernel_size_w=3,
    #                                                 rate_h=self.rate_list[1],
    #                                                 rate_w=self.rate_list[1],
    #                                                 cell_name=self.cell_name,
    #                                                 block_name=self.block_name)
    # group_2_conv = group_2_conv_c(group_1_relu)
    #
    # group_2_bn_c = self.layer_factory.bn2d(cell_name=self.cell_name, block_name=self.block_name)
    # group_2_bn = group_2_bn_c(group_2_conv)
    #
    # group_2_relu_c = self.layer_factory.relu(cell_name=self.cell_name, block_name=self.block_name)
    # group_2_relu = group_2_relu_c(group_2_bn)
    #
    # group_12_add_c = self.layer_factory.add(cell_name=self.cell_name, block_name=self.block_name)
    # group_12_add = group_12_add_c(*[[group_1_relu, group_2_relu]])
    #
    # # group 3
    # group_3_conv_c = self.layer_factory.separable_conv2d(input_channel=None,
    #                                                 filters=self.output_channel,
    #                                                 kernel_size_h=3,
    #                                                 kernel_size_w=3,
    #                                                 rate_h=self.rate_list[2],
    #                                                 rate_w=self.rate_list[2],
    #                                                 cell_name=self.cell_name,
    #                                                 block_name=self.block_name)
    # group_3_conv = group_3_conv_c(group_12_add)
    #
    # group_3_bn_c = self.layer_factory.bn2d(cell_name=self.cell_name, block_name=self.block_name)
    # group_3_bn = group_3_bn_c(group_3_conv)
    #
    # group_3_relu_c = self.layer_factory.relu(cell_name=self.cell_name, block_name=self.block_name)
    # group_3_relu = group_3_relu_c(group_3_bn)
    #
    # group_4_12_add_c = self.layer_factory.add(cell_name=self.cell_name, block_name=self.block_name)
    # group_4_12_add = group_4_12_add_c(*[[group_1_relu, group_2_relu]])
    #
    # group_4_123_add_c = self.layer_factory.add(cell_name=self.cell_name, block_name=self.block_name)
    # group_4_123_add = group_4_123_add_c(*[[group_4_12_add, group_3_relu]])

    group_1_conv_tensor = self.group_1_conv(*args, **kwargs)
    group_1_bn_tensor = self.group_1_bn(group_1_conv_tensor)
    group_1_relu_tensor = self.group_1_relu(group_1_bn_tensor)

    group_2_conv_tensor = self.group_2_conv(group_1_relu_tensor)
    group_2_bn_tensor = self.group_2_bn(group_2_conv_tensor)
    group_2_relu_tensor = self.group_2_relu(group_2_bn_tensor)

    group_12_add = self.group_12_add(*[[group_1_relu_tensor, group_2_relu_tensor]])

    group_3_conv_tensor = self.group_3_conv(group_12_add)
    group_3_bn_tensor = self.group_3_bn(group_3_conv_tensor)
    group_3_relu_tensor = self.group_3_relu(group_3_bn_tensor)

    group_4_12_add_tensor = self.group_4_12_add(*[[group_1_relu_tensor, group_2_relu_tensor]])
    group_4_123_add_tensor = self.group_4_123_add(*[[group_4_12_add_tensor, group_3_relu_tensor]])

    return group_4_123_add_tensor

  @property
  def layer_type_encoder(self):
    # 0.3 ~ 0.4
    a, b, c = self.rate_list
    a_i = -1
    b_i = -1
    c_i = -1
    for i, m in enumerate(self.rate_list):
      if m == a:
        a_i = i
      if m == b:
        b_i = i
      if m == c:
        c_i = i

    return self.encoder_scale((a_i * 25 + b_i * 5 + c_i) / 124.0, 0.3)


class SEBranch(Branch):
  def __init__(self, input=None, output=None, **kwargs):
    super(SEBranch, self).__init__(input,output,**kwargs)
    self.layer_name = 'se_branch'

    if 'squeeze_channels' not in kwargs:
      candidate_squeeze_channels = [4, 8, 16]
      self.squeeze_channels = random.choice(candidate_squeeze_channels)
    else:
      self.squeeze_channels = kwargs['squeeze_channels']

    self.group_1 = BaseStubAvgPooling2d(kernel_size_h=None, kernel_size_w=None, group=self)
    self.group_1_conv = BaseStubConv2d(input_channel=None,
                                       filters=self.squeeze_channels,
                                       kernel_size_h=1,
                                       kernel_size_w=1,
                                       rate_h=1,
                                       rate_w=1,
                                       cell_name=self.cell_name,
                                       block_name=self.block_name,
                                       group=self)

    self.group_1_bn = BaseStubBatchNormalization2d(cell_name=self.cell_name, block_name=self.block_name, group=self)
    self.group_1_relu = BaseStubReLU(cell_name=self.cell_name, block_name=self.block_name, group=self)

    self.group_2_conv = BaseStubConv2d(input_channel=None,
                                       filters=None,
                                       kernel_size_h=1,
                                       kernel_size_w=1,
                                       rate_h=1,
                                       rate_w=1,
                                       cell_name=self.cell_name,
                                       block_name=self.block_name,
                                       group=self)

    self.group_2_bn = BaseStubBatchNormalization2d(cell_name=self.cell_name, block_name=self.block_name, group=self)
    self.group_3_sigmoid = BaseStubSigmoid(cell_name=self.cell_name, block_name=self.block_name, group=self)
    self.group_4_multiply = BaseStubDot(cell_name=self.cell_name, block_name=self.block_name, group=self)


  @property
  def output_shape(self):
    self.group_1.input = self.input
    self.group_1.kernel_size_h = self.input.shape[1]
    self.group_1.kernel_size_w = self.input.shape[2]

    self.group_1_conv.input = DummyNode(self.group_1.output_shape)
    self.group_1_bn.input = DummyNode(self.group_1_conv.output_shape)
    self.group_1_relu.input = DummyNode(self.group_1_bn.output_shape)

    self.group_2_conv.input = DummyNode(self.group_1_relu.output_shape)
    self.group_2_conv.filters = self.input.shape[-1]
    self.group_2_bn.input = DummyNode(self.group_2_conv.output_shape)
    self.group_3_sigmoid.input = DummyNode(self.group_2_bn.output_shape)

    self.group_4_multiply.input = [self.input, DummyNode(self.group_3_sigmoid.output_shape)]

    return self.group_4_multiply.output_shape

  def flops(self):
    self.group_1.input = self.input
    self.group_1.kernel_size_h = self.input.shape[1]
    self.group_1.kernel_size_w = self.input.shape[2]

    self.group_1_conv.input = DummyNode(self.group_1.output_shape)
    self.group_1_bn.input = DummyNode(self.group_1_conv.output_shape)
    self.group_1_relu.input = DummyNode(self.group_1_bn.output_shape)

    self.group_2_conv.input = DummyNode(self.group_1_relu.output_shape)
    self.group_2_conv.filters = self.input.shape[-1]
    self.group_2_bn.input = DummyNode(self.group_2_conv.output_shape)
    self.group_3_sigmoid.input = DummyNode(self.group_2_bn.output_shape)

    self.group_4_multiply.input = [self.input, DummyNode(self.group_3_sigmoid.output_shape)]

    return self.group_1.flops()+\
           self.group_1_conv.flops()+\
           self.group_1_bn.flops()+\
           self.group_1_relu.flops()+\
           self.group_2_conv.flops()+\
           self.group_2_bn.flops()+\
           self.group_3_sigmoid.flops()+\
           self.group_4_multiply.flops()

  def __call__(self, *args, **kwargs):
    # group_1_layer_c = self.layer_factory.avg_pool2d(kernel_size_h=self.input.shape[1], kernel_size_w=self.input.shape[2])
    # group_1_layer = group_1_layer_c(*args, **kwargs)
    #
    # group_1_conv_c = self.layer_factory.conv2d(None,
    #                                            filters=self.squeeze_channels,
    #                                            kernel_size_h=1,
    #                                            kernel_size_w=1,
    #                                            cell_name=self.cell_name,
    #                                            block_name=self.block_name
    #                                            )
    # group_1_conv = group_1_conv_c(group_1_layer)
    #
    # group_1_bn_c = self.layer_factory.bn2d(cell_name=self.cell_name, block_name=self.block_name)
    # group_1_bn = group_1_bn_c(group_1_conv)
    #
    # group_1_relu_c = self.layer_factory.relu(cell_name=self.cell_name, block_name=self.block_name)
    # group_1_relu = group_1_relu_c(group_1_bn)
    #
    # group_2_conv_c = self.layer_factory.conv2d(None,
    #                                        filters=self.input.shape[-1],
    #                                        kernel_size_h=1,
    #                                        kernel_size_w=1,
    #                                        rate_h=1,
    #                                        rate_w=1,
    #                                        cell_name=self.cell_name,
    #                                        block_name=self.block_name)
    # group_2_conv = group_2_conv_c(group_1_relu)
    #
    # group_2_bn_c = self.layer_factory.bn2d(cell_name=self.cell_name, block_name=self.block_name)
    # group_2_bn = group_2_bn_c(group_2_conv)
    #
    # group_3_sigmoid_c = self.layer_factory.sigmoid(cell_name=self.cell_name, block_name=self.block_name)
    # group_3_sigmoid = group_3_sigmoid_c(group_2_bn)
    #
    # group_4_multiply_c = self.layer_factory.dot(cell_name=self.cell_name, block_name=self.block_name)
    # group_4_multiply = group_4_multiply_c(*[[group_3_sigmoid, args[0]]], **kwargs)

    self.group_1.kernel_size_h = self.input.shape[1]
    self.group_1.kernel_size_w = self.input.shape[2]
    group_1_tensor = self.group_1(*args, **kwargs)
    group_1_conv_tensor = self.group_1_conv(group_1_tensor)
    group_1_bn_tensor = self.group_1_bn(group_1_conv_tensor)
    group_1_relu_tensor = self.group_1_relu(group_1_bn_tensor)

    self.group_2_conv.filters = self.input.shape[-1]
    group_2_conv_tensor = self.group_2_conv(group_1_relu_tensor)
    group_2_bn_tensor = self.group_2_bn(group_2_conv_tensor)

    group_3_sigmoid_tensor = self.group_3_sigmoid(group_2_bn_tensor)
    group_4_multiply_tensor = self.group_4_multiply(*[[group_3_sigmoid_tensor, args[0]]], **kwargs)

    return group_4_multiply_tensor

  @property
  def layer_type_encoder(self):
    # 0.4 ~ 0.5
    if self.squeeze_channels == 4:
      return 0.43
    elif self.squeeze_channels == 8:
      return 0.46
    else:
      return 0.49


class RegionSEBranch(Branch):
  def __init__(self, input=None, output=None, **kwargs):
    super(RegionSEBranch, self).__init__(input, output, **kwargs)
    self.layer_name = 'regionse_branch'

    if 'squeeze_channels' not in kwargs:
      candidate_squeeze_channels = [4, 8, 16]
      self.squeeze_channels = random.choice(candidate_squeeze_channels)
    else:
      self.squeeze_channels = kwargs['squeeze_channels']

    if 'region_size' not in kwargs:
      candidate_region_sizes = [2, 4, 6, 8]
      self.region_size = random.choice(candidate_region_sizes)
    else:
      self.region_size = kwargs['region_size']

    self.group_1 = BaseStubAvgPooling2d(kernel_size_h=self.region_size, kernel_size_w=self.region_size, group=self)
    self.group_1_conv = BaseStubConv2d(input_channel=None,
                                       filters=self.squeeze_channels,
                                       kernel_size_h=3,
                                       kernel_size_w=3,
                                       cell_name=self.cell_name,
                                       block_name=self.block_name,
                                       group=self)

    self.group_1_bn = BaseStubBatchNormalization2d(cell_name=self.cell_name, block_name=self.block_name, group=self)
    self.group_1_relu = BaseStubReLU(cell_name=self.cell_name, block_name=self.block_name, group=self)

    self.group_2_conv = BaseStubConv2d(input_channel=None,
                                       filters=None,
                                       kernel_size_h=3,
                                       kernel_size_w=3,
                                       cell_name=self.cell_name,
                                       block_name=self.block_name,
                                       group=self)

    self.group_2_bn = BaseStubBatchNormalization2d(cell_name=self.cell_name, block_name=self.block_name, group=self)
    self.group_3_sigmoid = BaseStubSigmoid(cell_name=self.cell_name, block_name=self.block_name, group=self)
    self.group_resize = BaseStubBilinearResize(height=None, width=None, group=self)
    self.group_4_multiply = BaseStubDot(cell_name=self.cell_name, block_name=self.block_name, group=self)

  @property
  def output_shape(self):
    self.group_1.input = self.input
    self.group_1_conv.input = DummyNode(self.group_1.output_shape)
    self.group_1_bn.input = DummyNode(self.group_1_conv.output_shape)
    self.group_1_relu.input = DummyNode(self.group_1_bn.output_shape)

    self.group_2_conv.input = DummyNode(self.group_1_relu.output_shape)
    self.group_2_conv.filters = self.input.shape[-1]

    self.group_2_bn.input = DummyNode(self.group_2_conv.output_shape)
    self.group_3_sigmoid.input = DummyNode(self.group_2_bn.output_shape)

    self.group_resize.input = DummyNode(self.group_3_sigmoid.output_shape)
    self.group_resize.height = self.input.shape[1]
    self.group_resize.width = self.input.shape[2]

    self.group_4_multiply.input = [self.input, DummyNode(self.group_resize.output_shape)]

    return self.group_4_multiply.output_shape

  def flops(self):
    self.group_1.input = self.input
    self.group_1_conv.input = DummyNode(self.group_1.output_shape)
    self.group_1_bn.input = DummyNode(self.group_1_conv.output_shape)
    self.group_1_relu.input = DummyNode(self.group_1_bn.output_shape)

    self.group_2_conv.input = DummyNode(self.group_1_relu.output_shape)
    self.group_2_conv.filters = self.input.shape[-1]

    self.group_2_bn.input = DummyNode(self.group_2_conv.output_shape)
    self.group_3_sigmoid.input = DummyNode(self.group_2_bn.output_shape)

    self.group_resize.input = DummyNode(self.group_3_sigmoid.output_shape)
    self.group_resize.height = self.input.shape[1]
    self.group_resize.width = self.input.shape[2]

    self.group_4_multiply.input = [self.input, DummyNode(self.group_resize.output_shape)]

    return self.group_1.flops()+\
           self.group_1_conv.flops()+\
           self.group_1_bn.flops()+\
           self.group_1_relu.flops()+\
           self.group_2_conv.flops()+\
           self.group_2_bn.flops()+\
           self.group_3_sigmoid.flops()+ \
           self.group_resize.flops()+\
           self.group_4_multiply.flops()

  def __call__(self, *args, **kwargs):
    # group_1_layer_c = self.layer_factory.avg_pool2d(kernel_size_h=self.region_size, kernel_size_w=self.region_size)
    # group_1_layer = group_1_layer_c(*args, **kwargs)
    #
    # group_1_conv_c = self.layer_factory.conv2d(None,
    #                                            filters=self.squeeze_channels,
    #                                            kernel_size_h=3,
    #                                            kernel_size_w=3,
    #                                            cell_name=self.cell_name,
    #                                            block_name=self.block_name
    #                                            )
    # group_1_conv = group_1_conv_c(group_1_layer)
    #
    # group_1_bn_c = self.layer_factory.bn2d(cell_name=self.cell_name, block_name=self.block_name)
    # group_1_bn = group_1_bn_c(group_1_conv)
    #
    # group_1_relu_c = self.layer_factory.relu(cell_name=self.cell_name, block_name=self.block_name)
    # group_1_relu = group_1_relu_c(group_1_bn)
    #
    # group_2_conv_c = self.layer_factory.conv2d(None,
    #                                        filters=self.input.shape[-1],
    #                                        kernel_size_h=3,
    #                                        kernel_size_w=3,
    #                                        cell_name=self.cell_name,
    #                                        block_name=self.block_name)
    # group_2_conv = group_2_conv_c(group_1_relu)
    #
    # group_2_bn_c = self.layer_factory.bn2d(cell_name=self.cell_name, block_name=self.block_name)
    # group_2_bn = group_2_bn_c(group_2_conv)
    #
    # group_3_sigmoid_c = self.layer_factory.sigmoid(cell_name=self.cell_name, block_name=self.block_name)
    # group_3_sigmoid = group_3_sigmoid_c(group_2_bn)
    #
    # group_resize_c = self.layer_factory.bilinear_resize(height=self.input.shape[1], width=self.input.shape[2])
    # group_resize = group_resize_c(group_3_sigmoid)
    #
    # group_4_multiply_c = self.layer_factory.dot(cell_name=self.cell_name, block_name=self.block_name)
    # group_4_multiply = group_4_multiply_c(*[[group_resize, args[0]]], **kwargs)

    group_1_tensor = self.group_1(*args, **kwargs)
    group_1_conv_tensor = self.group_1_conv(group_1_tensor)
    group_1_bn_tensor = self.group_1_bn(group_1_conv_tensor)
    group_1_relu_tensor = self.group_1_relu(group_1_bn_tensor)

    self.group_2_conv.filters = self.input.shape[-1]
    group_2_conv_tensor = self.group_2_conv(group_1_relu_tensor)
    group_2_bn_tensor = self.group_2_bn(group_2_conv_tensor)

    group_3_sigmoid_tensor = self.group_3_sigmoid(group_2_bn_tensor)

    self.group_resize.height = self.input.shape[1]
    self.group_resize.width = self.input.shape[2]
    group_resize_tensor = self.group_resize(group_3_sigmoid_tensor)
    group_4_multiply_tensor = self.group_4_multiply(*[[group_resize_tensor, args[0]]], **kwargs)

    return group_4_multiply_tensor

  @property
  def layer_type_encoder(self):
    # 0.4 ~ 0.5
    # region_size: 2, 4, 6, 8; squeeze_channels: 4, 8, 16
    sc_i = -1
    for i, s in enumerate([4, 8, 16]):
      if self.squeeze_channels == s:
        sc_i = i

    rs_i = -1
    for j,r in enumerate([2, 4, 6, 8]):
      if self.region_size == r:
        rs_i = j

    return self.encoder_scale((sc_i * 4 + rs_i) / 11.0, 0.4)


class ResBranch(Branch):
  def __init__(self, output_channel, input=None, output=None, **kwargs):
    super(ResBranch, self).__init__(input, output, **kwargs)
    self.layer_name = 'res_branch'
    self.output_channel = output_channel

    self.group_0_short_cut = None
    self.group_1_conv = BaseStubConv2d(None,
                                       self.output_channel,
                                       3,
                                       3,
                                       cell_name=self.cell_name,
                                       block_name=self.block_name,
                                       group=self)
    self.group_1_bn = BaseStubBatchNormalization2d(cell_name=self.cell_name, block_name=self.block_name, group=self)
    self.group_1_relu = BaseStubReLU(cell_name=self.cell_name, block_name=self.block_name, group=self)

    self.group_2_conv = BaseStubConv2d(None,
                                       self.output_channel,
                                       3,
                                       3,
                                       cell_name=self.cell_name,
                                       block_name=self.block_name,
                                       group=self)
    self.group_2_bn = BaseStubBatchNormalization2d(cell_name=self.cell_name, block_name=self.block_name, group=self)

    self.group_3 = BaseStubAdd(cell_name=self.cell_name, block_name=self.block_name, group=self)
    self.group_4 = BaseStubReLU(cell_name=self.cell_name, block_name=self.block_name, group=self)

  @property
  def output_shape(self):
    return (self.input.shape[0], self.input.shape[1], self.input.shape[2], self.output_channel)

  def flops(self):
    self.group_0_short_cut = None
    if self.input.shape[-1] != self.output_channel:
      self.group_0_short_cut = BaseStubConv2d(None, self.output_channel, 1, 1, cell_name=self.cell_name, block_name=self.block_name)
      self.group_0_short_cut.input = self.input

    self.group_1_conv.input = self.input
    self.group_1_bn.input = DummyNode(self.group_1_conv.output_shape)
    self.group_1_relu.input = DummyNode(self.group_1_bn.output_shape)

    self.group_2_conv.input = DummyNode(self.group_1_relu.output_shape)
    self.group_2_bn.input = DummyNode(self.group_2_conv.output_shape)

    if self.input.shape[-1] != self.output_channel:
      self.group_3.input = [DummyNode(self.group_0_short_cut.output_shape), DummyNode(self.group_2_bn.output_shape)]
    else:
      self.group_3.input = [self.input, DummyNode(self.group_2_bn.output_shape)]

    self.group_4.input = DummyNode(self.group_3.output_shape)

    total_flops = self.group_1_conv.flops() + \
           self.group_1_bn.flops() +\
           self.group_1_relu.flops() +\
           self.group_2_conv.flops() +\
           self.group_2_bn.flops() + \
           self.group_3.flops() + \
           self.group_4.flops()

    if self.group_0_short_cut is not None:
      total_flops += self.group_0_short_cut.flops()
    return total_flops

  def __call__(self, *args, **kwargs):
    group_0_short_cut = None
    if args[0].shape[-1] != self.output_channel:
      group_0_short_cut_c = self.layer_factory.conv2d(None, self.output_channel, 1, 1, cell_name=self.cell_name, block_name=self.block_name)
      group_0_short_cut = group_0_short_cut_c(*args, **kwargs)

    group_1_conv_tensor = self.group_1_conv(*args, **kwargs)
    group_1_bn_tensor = self.group_1_bn(group_1_conv_tensor)
    group_1_relu_tensor = self.group_1_relu(group_1_bn_tensor)

    group_2_conv_tensor = self.group_2_conv(group_1_relu_tensor)
    group_2_bn_tensor = self.group_2_bn(group_2_conv_tensor)

    group_3_tensor = None
    if group_0_short_cut is None:
      group_3_tensor = self.group_3(*[[group_2_bn_tensor, args[0]]], **kwargs)
    else:
      group_3_tensor = self.group_3(*[[group_2_bn_tensor, group_0_short_cut]], **kwargs)

    group_4_tensor = self.group_4(group_3_tensor)

    return group_4_tensor

  @property
  def layer_type_encoder(self):
    # 0.5 ~ 0.6
    return 0.55


class BottleNeckResBranch(Branch):
  def __init__(self, output_channel, input=None, output=None, **kwargs):
    super(BottleNeckResBranch, self).__init__(input, output, **kwargs)
    self.layer_name = 'bottleneck_res_branch'
    self.output_channel = output_channel

    self.candidate_bottleneck = [8, 16, 32, 64]
    if 'bottleneck' not in kwargs:
      self.bottleneck = random.choice(self.candidate_bottleneck)
    else:
      self.bottleneck = kwargs['bottleneck']

    self.group_0_short_cut = None
    self.group_1_conv = BaseStubConv2d(None,
                                       self.bottleneck,
                                       1,
                                       1,
                                       cell_name=self.cell_name,
                                       block_name=self.block_name,
                                       group=self)
    self.group_1_bn = BaseStubBatchNormalization2d(cell_name=self.cell_name, block_name=self.block_name,group=self)
    self.group_1_relu = BaseStubReLU(cell_name=self.cell_name, block_name=self.block_name, group=self)

    self.group_2_conv = BaseStubConv2d(None,
                                       self.bottleneck,
                                       3,
                                       3,
                                       cell_name=self.cell_name,
                                       block_name=self.block_name,
                                       group=self)
    self.group_2_bn = BaseStubBatchNormalization2d(cell_name=self.cell_name, block_name=self.block_name,group=self)
    self.group_2_relu = BaseStubReLU(cell_name=self.cell_name, block_name=self.block_name, group=self)

    self.group_3_conv = BaseStubConv2d(None,
                                       self.output_channel,
                                       1,
                                       1,
                                       cell_name=self.cell_name,
                                       block_name=self.block_name,
                                       group=self)
    self.group_3_bn = BaseStubBatchNormalization2d(cell_name=self.cell_name, block_name=self.block_name,group=self)

    self.group_4 = BaseStubAdd(cell_name=self.cell_name, block_name=self.block_name, group=self)
    self.group_5 = BaseStubReLU(cell_name=self.cell_name, block_name=self.block_name, group=self)

  @property
  def output_shape(self):
    return (self.input.shape[0], self.input.shape[1], self.input.shape[2], self.output_channel)

  def flops(self):
    self.group_0_short_cut = None
    if self.input.shape[-1] != self.output_channel:
      self.group_0_short_cut = BaseStubConv2d(None,
                                              self.output_channel,
                                              1,
                                              1,
                                              cell_name=self.cell_name,
                                              block_name=self.block_name)
      self.group_0_short_cut.input = self.input

    self.group_1_conv.input = self.input
    self.group_1_bn.input = DummyNode(self.group_1_conv.output_shape)
    self.group_1_relu.input = DummyNode(self.group_1_bn.output_shape)

    self.group_2_conv.input = DummyNode(self.group_1_relu.output_shape)
    self.group_2_bn.input = DummyNode(self.group_2_conv.output_shape)
    self.group_2_relu.input = DummyNode(self.group_2_bn.output_shape)

    self.group_3_conv.input = DummyNode(self.group_2_relu.output_shape)
    self.group_3_bn.input = DummyNode(self.group_3_conv.output_shape)

    if self.group_0_short_cut is not None:
      self.group_4.input = [DummyNode(self.group_0_short_cut.output_shape), DummyNode(self.group_3_bn.output_shape)]
    else:
      self.group_4.input = [self.input, DummyNode(self.group_3_bn.output_shape)]

    self.group_5.input = DummyNode(self.group_4.output_shape)

    total_flops = self.group_1_conv.flops() + \
           self.group_1_bn.flops() + \
           self.group_1_relu.flops() + \
           self.group_2_conv.flops() + \
           self.group_2_bn.flops() + \
           self.group_2_relu.flops() + \
           self.group_3_conv.flops() + \
           self.group_3_bn.flops() +\
           self.group_4.flops() + \
           self.group_5.flops()

    if self.group_0_short_cut is not None:
      total_flops += self.group_0_short_cut.flops()

    return total_flops

  def __call__(self, *args, **kwargs):
    group_0_short_cut = None
    if args[0].shape[-1] != self.output_channel:
      group_0_short_cut_c = self.layer_factory.conv2d(None,
                                                      self.output_channel,
                                                      1,
                                                      1,
                                                      cell_name=self.cell_name,
                                                      block_name=self.block_name)
      group_0_short_cut = group_0_short_cut_c(*args, **kwargs)

    group_1_conv_tensor = self.group_1_conv(*args, **kwargs)
    group_1_bn_tensor = self.group_1_bn(group_1_conv_tensor)
    group_1_relu_tensor = self.group_1_relu(group_1_bn_tensor)

    group_2_conv_tensor = self.group_2_conv(group_1_relu_tensor)
    group_2_bn_tensor = self.group_2_bn(group_2_conv_tensor)
    group_2_relu_tensor = self.group_2_relu(group_2_bn_tensor)

    group_3_conv_tensor = self.group_3_conv(group_2_relu_tensor)
    group_3_bn_tensor = self.group_3_bn(group_3_conv_tensor)

    group_4_tensor = None
    if group_0_short_cut is None:
      group_4_tensor = self.group_4(*[[group_3_bn_tensor, args[0]]], **kwargs)
    else:
      group_4_tensor = self.group_4(*[[group_3_bn_tensor, group_0_short_cut]], **kwargs)

    group_5_tensor = self.group_5(group_4_tensor)
    return group_5_tensor

  @property
  def layer_type_encoder(self):
    # 0.5 ~ 0.6
    mi = -1
    for i, m in enumerate(self.candidate_bottleneck):
      if self.bottleneck == m:
        mi = i

    return self.encoder_scale(float(mi) / len(self.candidate_bottleneck), 0.5)