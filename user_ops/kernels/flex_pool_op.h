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

#ifndef USER_OPS_KERNELS_FLEX_POOL_OP_H_
#define USER_OPS_KERNELS_FLEX_POOL_OP_H_

#include "tensorflow/core/framework/op_kernel.h"

namespace tensorflow {
class OpKernelContext;
class Tensor;

using CPUDevice = Eigen::ThreadPoolDevice;
using GPUDevice = Eigen::GpuDevice;
}  // namespace tensorflow

namespace tensorflow {
namespace functor {

template <typename Device, typename Dtype>
struct FlexPoolFunctor {
  void operator()(::tensorflow::OpKernelContext* ctx, const Tensor& features_,
                  const Tensor& neighborhood_, Tensor* output_,
                  Tensor* argmax_);
};

template <typename Device, typename Dtype>
struct FlexPoolGrad {
  void operator()(::tensorflow::OpKernelContext* ctx, const Tensor& features_,
                  const Tensor& neighborhood_, const Tensor& topdiff_,
                  const Tensor& argmax_, Tensor* grad_features_);
};

}  // namespace functor
}  // namespace tensorflow

#endif  // USER_OPS_KERNELS_FLEX_POOL_OP_H_
