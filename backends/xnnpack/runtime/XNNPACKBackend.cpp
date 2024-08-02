/*
 * Copyright (c) Meta Platforms, Inc. and affiliates.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the
 * LICENSE file in the root directory of this source tree.
 */

#include <executorch/backends/xnnpack/runtime/XNNCompiler.h>
#include <executorch/runtime/backend/interface.h>
#include <executorch/runtime/core/error.h>
#include <executorch/runtime/core/evalue.h>
#include <executorch/runtime/platform/profiler.h>
#include <memory>

#pragma clang diagnostic ignored "-Wglobal-constructors"

namespace torch {
namespace executor {

class XnnpackBackend final : public PyTorchBackendInterface {
 public:
  ~XnnpackBackend() = default;

  XnnpackBackend() {
    // Initialize XNNPACK
    xnn_status status = xnn_initialize(/*allocator=*/nullptr);
    if (status != xnn_status_success) {
      ET_LOG(
          Error, 
          "Failed to initialize, XNNPACK status: 0x%x",
          (unsigned int)status);
      return;
    }

    // Create a workspace for the XNNExecutor to use. This workspace will be
    // shared across all delegate instances.
    status = xnn_create_workspace(&workspace_);
    if (status != xnn_status_success) {
      ET_LOG(
          Error,
          "Failed to create XNN workspace, XNNPACK status: 0x%x",
          (unsigned int)status);
      workspace_ = nullptr;
      return;
    }
    ET_LOG(Debug, "Created XNN workspace: %p", workspace_);
  }

  bool is_available() const override {
    return xnn_status_success == xnn_initialize(/*allocator=*/nullptr);
  }

  Result<DelegateHandle*> init(
      BackendInitContext& context,
      FreeableBuffer* processed,
      ArrayRef<CompileSpec> compile_specs) const override {
    auto executor = ET_ALLOCATE_INSTANCE_OR_RETURN_ERROR(
        context.get_runtime_allocator(), xnnpack::delegate::XNNExecutor);

    // Executor has been allocated but not constructed, ensure that runtime_ is
    // nullptr by constructing it in place here. NOTE: Since we use placement
    // new and since this type is not trivially destructible, we must call the
    // destructor manually in destroy().
    new (executor) xnnpack::delegate::XNNExecutor;
  
    ET_CHECK_OR_RETURN_ERROR(
        workspace_ != nullptr, Internal, "Failed to create XNN workspace");
    Error err = xnnpack::delegate::XNNCompiler::compileModel(
        processed->data(),
        processed->size(),
        executor,
        context.get_runtime_allocator(),
        workspace_);
    // This backend does not need its processed data after compiling the model.
    processed->Free();

    if (err != Error::Ok) {
      // destroy() won't be called on this handle, so we need to clean it up
      // now.
      executor->~XNNExecutor();

      ET_LOG(
          Error, "XNNCompiler::compileModel failed: 0x%x", (unsigned int)err);
      return err;
    }
    return executor;
  }

  Error execute(
      BackendExecutionContext& context,
      DelegateHandle* handle,
      EValue** args) const override {
    auto executor = static_cast<xnnpack::delegate::XNNExecutor*>(handle);

    // Prepare Inputs/Outputs and Propagate Input Shapes
    Error err = executor->prepare_args(args);
    if (err != Error::Ok) {
      return err;
    }

    err = executor->forward(context);

    if (err != Error::Ok) {
      return err;
    }

    // Resize outputs and recast pointers if necessary
    err = executor->resize_outputs(args);

    return err;
  }

  void destroy(DelegateHandle* handle) const override {
    if (handle != nullptr) {
      auto executor = static_cast<xnnpack::delegate::XNNExecutor*>(handle);
#ifdef ENABLE_XNNPACK_PROFILING
      executor->print_avg_op_timings();
#endif
      // XNNExecutor is not trivially destructible. Since this was constructed
      // manually in init(), we must destroy it manually here.
      executor->~XNNExecutor();
    }
  }

 private:
  // Global state for the backend.

  // This is a global workspace for all delegate instances.

  // This needs to be guarded by a mutex to ensure thread safety.
  // But this would come at a performance cost when two otherwise
  // unrelated delegate instances can't go in parallel from two runtimes.

  // TODO - Add a switch to enable/disable this global workspace
  // (and the corrosponding mutex for delegate::execute())
  xnn_workspace_t workspace_;

  // TODO - Add support for weight cache
};

namespace {
auto cls = XnnpackBackend();
Backend backend{"XnnpackBackend", &cls};
static auto success_with_compiler = register_backend(backend);
} // namespace

} // namespace executor
} // namespace torch
