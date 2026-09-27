import os
import sys
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main(config_path: str = "models/llm/configs/config_10b.yaml", resume_from: Optional[str] = None):
    from models.llm.training.pretrain import PretrainPipeline
    pipeline = PretrainPipeline(config_path)
    try:
        history = pipeline.run(resume_from=resume_from)
        logger.info("Training completed successfully")
        logger.info(f"Final metrics: {history}")
    except RuntimeError as exc:
        if "not enough memory" in str(exc):
            logger.error("Insufficient memory for 10B model training on this machine.")
            logger.info("Falling back to scaled-down config for demonstration.")
            fallback = "models/llm/configs/config_4b.yaml"
            pipeline = PretrainPipeline(fallback)
            history = pipeline.run(resume_from=resume_from)
            logger.info("Fallback training completed")
        else:
            raise


if __name__ == "__main__":
    main()
