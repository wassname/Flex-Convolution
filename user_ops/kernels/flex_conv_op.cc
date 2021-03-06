/* Copyright 2017 ComputerGraphics Tuebingen. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
==============================================================================*/
//Authors: Fabian Groh, Patrick Wieschollek, Hendrik P.A. Lensch

#include "flex_conv_op.h"

#include <stdio.h>
#include <type_traits>

#include "tensorflow/core/framework/op.h"
#include "tensorflow/core/framework/op_kernel.h"
#include "tensorflow/core/framework/register_types.h"

namespace tensorflow {

// Forward-Pass (CPU, GPU)
// --------------------------------------------------
template <typename Device, typename Dtype>
class FlexConvOp : public OpKernel {
 public:
  explicit FlexConvOp(OpKernelConstruction* ctx) : OpKernel(ctx) {}

  void Compute(OpKernelContext* ctx) override {
    // printf("--> Compute CPU Version <--\n");
    const Tensor& features_ = ctx->input(0);
    const Tensor& theta_ = ctx->input(1);
    const Tensor& bias_ = ctx->input(2);
    const Tensor& neighborhood_ = ctx->input(3);
    const Tensor& positions_ = ctx->input(4);

    const int B = neighborhood_.shape().dim_size(0);
    const int N = neighborhood_.shape().dim_size(2);
    const int Dout = theta_.shape().dim_size(3);

    Tensor* output_ = nullptr;
    OP_REQUIRES_OK(
        ctx, ctx->allocate_output(0, TensorShape({B, Dout, N}), &output_));

    ::tensorflow::functor::FlexConvFunctor<Device, Dtype>()(
        ctx, features_, theta_, bias_, neighborhood_, positions_, output_);
  }

 private:
  TF_DISALLOW_COPY_AND_ASSIGN(FlexConvOp);
};

// Backward-Pass (CPU, GPU)
// --------------------------------------------------
template <typename Device, typename Dtype>
class FlexConvGradOp : public OpKernel {
 public:
  explicit FlexConvGradOp(OpKernelConstruction* ctx) : OpKernel(ctx) {}

  void Compute(OpKernelContext* ctx) override {
    // printf("--> Compute CPU Version <--\n");
    const Tensor& features_ = ctx->input(0);
    const Tensor& theta_ = ctx->input(1);
    const Tensor& bias_ = ctx->input(2);
    const Tensor& neighborhood_ = ctx->input(3);
    const Tensor& positions_ = ctx->input(4);

    const Tensor& topdiff_ = ctx->input(5);

    // specify output shape
    Tensor* grad_features_ = nullptr;
    Tensor* grad_theta_ = nullptr;
    Tensor* grad_bias_ = nullptr;

    const int Degree = theta_.shape().dim_size(0);

    OP_REQUIRES_OK(ctx,
                   ctx->allocate_output(0, features_.shape(), &grad_features_));
    OP_REQUIRES_OK(ctx, ctx->allocate_output(1, theta_.shape(), &grad_theta_));
    OP_REQUIRES_OK(ctx, ctx->allocate_output(2, bias_.shape(), &grad_bias_));

    ::tensorflow::functor::FlexConvGrad<Device, Dtype>()(
        ctx, features_, theta_, bias_, neighborhood_, positions_, topdiff_,
        grad_features_, grad_theta_, grad_bias_);
  }
};

// Register the CPU kernels.
#define REGISTER_FLEXCONV_OP_CPU(T)                                   \
  REGISTER_KERNEL_BUILDER(                                            \
      Name("FlexConv").Device(DEVICE_CPU).TypeConstraint<T>("T"),     \
      FlexConvOp<CPUDevice, T>)                                       \
  REGISTER_KERNEL_BUILDER(                                            \
      Name("FlexConvGrad").Device(DEVICE_CPU).TypeConstraint<T>("T"), \
      FlexConvGradOp<CPUDevice, T>)

TF_CALL_float(REGISTER_FLEXCONV_OP_CPU);
#undef REGISTER_FLEXCONV_OP_CPU

// Register the GPU kernels.
// #ifdef GOOGLE_CUDA

#define REGISTER_FLEXCONV_OP_GPU(T)                                   \
  REGISTER_KERNEL_BUILDER(                                            \
      Name("FlexConv").Device(DEVICE_GPU).TypeConstraint<T>("T"),     \
      FlexConvOp<GPUDevice, T>)                                       \
  REGISTER_KERNEL_BUILDER(                                            \
      Name("FlexConvGrad").Device(DEVICE_GPU).TypeConstraint<T>("T"), \
      FlexConvGradOp<GPUDevice, T>)

TF_CALL_float(REGISTER_FLEXCONV_OP_GPU);
#undef REGISTER_FLEXCONV_OP_GPU

// #endif  // GOOGLE_CUDA

}  // namespace tensorflow
