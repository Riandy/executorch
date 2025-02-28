# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.


from typing import List, Type

from executorch.backends.xnnpack.partition.config.gemm_configs import (
    AddmmConfig,
    ConvolutionConfig,
    LinearConfig,
)

from executorch.backends.xnnpack.partition.config.generic_node_configs import (
    AbsConfig,
    AddConfig,
    AvgPoolingConfig,
    CatConfig,
    CeilConfig,
    ClampConfig,
    DeQuantizedPerTensorConfig,
    DivConfig,
    # EluConfig,
    HardtanhConfig,
    MaximumConfig,
    MaxPool2dConfig,
    MulConfig,
    PermuteConfig,
    QuantizedPerTensorConfig,
    ReLUConfig,
    SigmoidConfig,
    SoftmaxConfig,
)
from executorch.backends.xnnpack.partition.config.node_configs import (
    BatchNormConfig,
    MaxDimConfig,
)
from executorch.backends.xnnpack.partition.config.xnnpack_config import (
    XNNPartitionerConfig,
)

ALL_PARTITIONER_CONFIGS: List[Type[XNNPartitionerConfig]] = [
    # GEMM-like Configs
    AddmmConfig,
    LinearConfig,
    ConvolutionConfig,
    # BatchNorm Config
    BatchNormConfig,
    # Single Node Configs
    HardtanhConfig,
    AbsConfig,
    AvgPoolingConfig,
    AddConfig,
    CatConfig,
    CeilConfig,
    ClampConfig,
    DivConfig,
    MaxDimConfig,
    MaxPool2dConfig,
    MaximumConfig,
    MulConfig,
    SoftmaxConfig,
    SigmoidConfig,
    PermuteConfig,
    # EluConfig, # Waiting for PyTorch Pin Update
    ReLUConfig,
    # Quantization Op Configs
    QuantizedPerTensorConfig,
    DeQuantizedPerTensorConfig,
]
