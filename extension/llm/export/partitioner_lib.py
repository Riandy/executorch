# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import Optional


def get_xnnpack_partitioner():
    from executorch.backends.xnnpack.partition.xnnpack_partitioner import (
        XnnpackDynamicallyQuantizedPartitioner,
    )

    # Following changes due to.
    # 1. We need dynamically quantized partitioner for both pt2e_quantize options
    #    as well as "qmode 8da4w" which is also dynamic quantizes linear layers.
    # 2. XNNPACK partitioner seems to result in seg fault for non dqlinear ops.
    return XnnpackDynamicallyQuantizedPartitioner()


def get_vulkan_partitioner(
    dtype_override: Optional[str] = None, quantization_mode: Optional[str] = None
):
    assert (
        dtype_override == "fp32" or dtype_override is None
    ), "Vulkan backend does not support non fp32 dtypes at the moment"
    assert (
        quantization_mode is None
    ), "Vulkan backend does not support quantization at the moment"
    from executorch.backends.vulkan.partitioner.vulkan_partitioner import (
        VulkanPartitioner,
    )

    return VulkanPartitioner({"require_dynamic_shapes": True})


def get_mps_partitioner(use_kv_cache: bool = False):
    from executorch.exir.backend.backend_details import CompileSpec

    assert (
        use_kv_cache is True
    ), "MPS backend currently only supports static shape and use_kv_cache=True is the only way to support it at the moment"
    try:
        # pyre-ignore Undefined import [21]: Could not find a module corresponding to import `executorch.backends.apple.mps.partition.mps_partitioner`.
        from executorch.backends.apple.mps.partition.mps_partitioner import (
            MPSPartitioner,
        )
    except ImportError:
        raise ImportError(
            "Please install the MPS backend follwing https://pytorch.org/executorch/main/build-run-mps.html"
        )

    compile_specs = [CompileSpec("use_fp16", bytes([True]))]
    return MPSPartitioner(compile_specs)


def get_coreml_partitioner(
    use_kv_cache: bool = False, pt2e_quantize: Optional[str] = None
):
    assert (
        use_kv_cache is True
    ), "CoreML backend currently only supports static shape and use_kv_cache=True is the only way to support it at the moment"
    try:
        import coremltools as ct
        from executorch.backends.apple.coreml.compiler import (  # pyre-ignore
            CoreMLBackend,
        )
        from executorch.backends.apple.coreml.partition import (  # pyre-ignore
            CoreMLPartitioner,
        )
    except ImportError:
        raise ImportError(
            "Please install the CoreML backend follwing https://pytorch.org/executorch/main/build-run-coreml.html"
        )

    minimum_deployment_target = ct.target.iOS15
    # In Core ML, quantization in introduced in iOS 16
    if pt2e_quantize is not None:
        minimum_deployment_target = max(minimum_deployment_target, ct.target.iOS16)
    # In Core ML, 8-bit activation quantization is introduced in iOS 17
    if pt2e_quantize in ("coreml_8a_c8w", "coreml_baseline_8a_c8w"):
        minimum_deployment_target = max(minimum_deployment_target, ct.target.iOS17)
    # In Core ML, 4-bit weight compression is introduced in iOS 18
    if pt2e_quantize in ("coreml_c4w", "coreml_8a_c4w", "coreml_baseline_8a_c4w"):
        minimum_deployment_target = max(minimum_deployment_target, ct.target.iOS18)
    # In Core ML, stateful execution is introduced in iOS 18
    # TODO (https://github.com/pytorch/executorch/issues/4209)
    # For now, since mutable buffer is kept in executorch runtime,
    # state is out of place and can be handled by older iOS.
    # Once mutable buffer can be handed over to delegate, i.e. state becomes in-place, we will have
    # if use_kv_cache:
    #     minimum_deployment_target = max(minimum_deployment_target, ct.target.iOS18)

    compile_specs = CoreMLBackend.generate_compile_specs(
        minimum_deployment_target=minimum_deployment_target,
        compute_precision=ct.precision(ct.precision.FLOAT16.value),
        # using `ComputeUnit.ALL` can increase the model load time, default to `ComputeUnit.CPU_AND_GPU`
        compute_unit=ct.ComputeUnit[ct.ComputeUnit.CPU_AND_GPU.name.upper()],
        model_type=CoreMLBackend.MODEL_TYPE.MODEL,
    )
    return CoreMLPartitioner(
        compile_specs=compile_specs,
    )


def get_qnn_partitioner(
    quant_dtype, use_kv_cache: bool = False, pt2e_quantize: Optional[str] = None
):
    assert (
        use_kv_cache is True
    ), "Qualcomm backend currently only supports static shape and use_kv_cache=True is the only way to support it at the moment"
    try:
        # pyre-ignore: Undefined import [21]: Could not find a module corresponding to import `executorch.backends.qualcomm.partition.qnn_partitioner`
        from executorch.backends.qualcomm.partition.qnn_partitioner import (
            QnnPartitioner,
        )

        # pyre-ignore: Undefined import [21]: Could not find a module corresponding to import `executorch.backends.qualcomm.quantizer.quantizer`
        from executorch.backends.qualcomm.quantizer.quantizer import QuantDtype

        # pyre-ignore: Undefined import [21]: Could not find a module corresponding to import `executorch.backends.qualcomm.serialization.qnn_compile_spec_schema`
        from executorch.backends.qualcomm.serialization.qnn_compile_spec_schema import (
            QcomChipset,
        )

        # pyre-ignore: Undefined import [21]: Could not find a module corresponding to import `executorch.backends.qualcomm.utils.utils`
        from executorch.backends.qualcomm.utils.utils import (
            generate_htp_compiler_spec,
            generate_qnn_executorch_compiler_spec,
        )
    except ImportError:
        raise ImportError(
            "Please install the Qualcomm backend follwing https://pytorch.org/executorch/main/build-run-qualcomm-ai-engine-direct-backend.html"
        )

    use_fp16 = True
    skip_node_op_set = {}
    if pt2e_quantize is not None:
        use_fp16 = False
        # TODO: fix the lowering error without skipping nodes

        if quant_dtype == QuantDtype.use_8a8w:
            raise NotImplementedError("8a8w for llama is still under development")

        elif quant_dtype == QuantDtype.use_16a16w:
            raise NotImplementedError("16a16w for llama is still under development")

        elif quant_dtype == QuantDtype.use_16a4w:
            raise NotImplementedError("16a4w for llama is still under development")

    return QnnPartitioner(
        generate_qnn_executorch_compiler_spec(
            soc_model=QcomChipset.SM8650,  # default to SM8650
            backend_options=generate_htp_compiler_spec(use_fp16=use_fp16),
            debug=False,
            saver=False,
        ),
        skip_node_id_set={},
        skip_node_op_set=skip_node_op_set,
    )
