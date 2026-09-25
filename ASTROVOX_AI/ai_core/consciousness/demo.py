import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

from ASTROVOX_AI.ai_core.consciousness.unified_consciousness import UnifiedConsciousness

logger = logging.getLogger(__name__)


def main():
    mind = UnifiedConsciousness(identity_id="agent_alpha")

    stimuli = [
        ("User requests help with coding", 0.9),
        ("System detects anomaly", 0.7),
        ("Peer agent asks for collaboration", 0.6),
        ("Routine maintenance alert", 0.3),
    ]

    for stimulus, relevance in stimuli:
        result = mind.process_stimulus(stimulus, relevance)
        logger.info("Processed: %s -> %s", stimulus, result.get("broadcast"))

    mind.reflect("Completed processing of multiple stimuli")
    mind.assess_threat("anomaly_001", 0.8, "security")

    report = mind.generate_report()
    logger.info("Consciousness report: %s", report)


if __name__ == "__main__":
    main()
