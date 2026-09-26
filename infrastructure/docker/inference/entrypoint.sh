#!/bin/sh
set -e

echo "Starting Astrovox Inference Engine..."
echo "Model: ${MODEL_NAME:-meta-llama/Llama-2-7b-chat-hf}"
echo "Tensor Parallel: ${TENSOR_PARALLEL_SIZE:-1}"
echo "Pipeline Parallel: ${PIPELINE_PARALLEL_SIZE:-1}"
echo "FlashAttention: ${USE_FLASH_ATTENTION:-true}"
echo "PagedAttention: ${USE_PAGED_ATTENTION:-true}"

exec python -m app.inference_platform \
  --model-name "${MODEL_NAME:-meta-llama/Llama-2-7b-chat-hf}" \
  --tensor-parallel-size "${TENSOR_PARALLEL_SIZE:-1}" \
  --pipeline-parallel-size "${PIPELINE_PARALLEL_SIZE:-1}" \
  --max-batch-size "${MAX_BATCH_SIZE:-32}" \
  --max-seq-len "${MAX_SEQ_LEN:-4096}"
