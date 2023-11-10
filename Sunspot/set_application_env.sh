#!/bin/bash

module unload oneapi
module load intel_compute_runtime/release/agama-devel-627
#module load gcc/12.1.0
export HF_HOME=/gila/Aurora_deployment/70B-acc_fix_for_ppi/huggingface
export HF_DATASETS_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_EVALUATE_OFFLINE=1

export SYCL_PI_LEVEL_ZERO_USE_IMMEDIATE_COMMANDLISTS=2
export ENABLE_SDP_FUSION=1
export COL_MAJOR=0

export ZE_ENABLE_PCI_ID_DEVICE_ORDER=1
export CCL_OP_SYNC=1
export CCL_PROCESS_LAUNCHER=pmix
export FI_PROVIDER=cxi
export PALS_PMI=pmix
export CCL_ATL_TRANSPORT=mpi # Required by Aurora mpich
export FI_MR_CACHE_MONITOR=disabled # Required by Aurora mpich (HPCS-6501)
export CCL_ZE_CACHE_OPEN_IPC_HANDLES_THRESHOLD=32768
export I_MPI_ROOT=/opt/cray/pe/pals/1.2.12/bin/mpiexec
export MAX_OUT_SEQ_LEN=1024
export NUMEXPR_MAX_THREADS=224
export TOKENIZERS_PARALLELISM=false
#module load intel_compute_runtime/release/agama-devel-627
#source /home/ftartagl/oneapi/inteloneapi-basekit-hpckit.2023.2.003/compiler/2023.2.0/env/vars.sh
#source /home/ftartagl/oneapi/inteloneapi-basekit-hpckit.2023.2.003/dnnl/2023.2.0/env/vars.sh

#source /home/ftartagl/oneapi/inteloneapi-basekit-hpckit.2023.2.003/mkl/2023.2.0/env/vars.sh
#source /home/ftartagl/oneapi/inteloneapi-basekit-hpckit.2023.2.003/tbb/latest/env/vars.sh
#source /soft/datascience/conda-2023-01-31/miniconda3/bin/activate
#conda activate anl_llma70_acc_fix
#conda activate /gila/Aurora_deployment/atanikanti/environments/balsam_llama_env
module use -a /gila/Aurora_deployment/70B-acc_fix_for_ppi/modulefiles
module load oneapi-testing/2023.2.003.PUBLIC_IDP49422
source /gila/Aurora_deployment/atanikanti/70B-acc_fix/frameworks.ai.pytorch.torch-ccl/third_party/oneCCL/build/_install/env/vars.sh
