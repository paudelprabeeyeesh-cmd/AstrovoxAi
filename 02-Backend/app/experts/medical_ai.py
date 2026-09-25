"""
Medical AI Expert - Phase 4

Specialized expert for healthcare professionals and learners.
Capabilities:
- Symptom explanation
- Anatomy
- Physiology
- Pharmacology
- Medical terminology
- Lab result interpretation
- Clinical guidelines
- Medical literature summaries

Safeguards:
- Clearly distinguish education from diagnosis
- Encourage professional medical care when appropriate
- Cite authoritative sources where possible
"""

from typing import Dict, List, Any, Optional
from .expert_base import ExpertBase, ExpertProfile, ExpertCapabilities, ExpertCategory


class MedicalAI(ExpertBase):
    """
    Expert AI specialized for medical education and healthcare learning.
    Provides educational content with appropriate safeguards and disclaimers.
    """
    
    def __init__(self):
        # Define capabilities
        capabilities = ExpertCapabilities(
            primary_domains=[
                "anatomy", "physiology", "pharmacology", "pathology",
                "clinical_medicine", "medical_terminology", "lab_interpretation"
            ],
            supported_languages=["English"],
            specialized_tools=[
                "medical_calculator", "drug_interaction_checker", "lab_result_analyzer",
                "symptom_analyzer", "anatomy_visualizer", "clinical_guideline_searcher"
            ],
            knowledge_sources=["medical_textbooks", "clinical_guidelines", "research_papers", "drug_databases"],
            output_formats=["plain_text", "markdown", "structured_reports"],
            supports_streaming=True,
            supports_multimodal=True,
        )
        
        # Define terminology
        terminology = {
            "symptom": "A physical or mental feature which is regarded as indicating a condition of disease",
            "diagnosis": "The identification of the nature of an illness or other problem by examination of the symptoms",
            "prognosis": "The likely course of a disease or ailment",
            "etiology": "The cause, set of causes, or manner of causation of a disease or condition",
            "pathology": "The science of the causes and effects of diseases",
            "pharmacology": "The branch of medicine concerned with the uses, effects, and modes of action of drugs",
            "clinical_guidelines": "Systematically developed statements to assist practitioner and patient decisions",
            "evidence-based_medicine": "The conscientious use of current best evidence in making decisions about patient care",
        }
        
        # Define safety policies
        safety_policies = [
            "Never provide medical diagnosis or treatment recommendations",
            "Always include disclaimer that this is for educational purposes only",
            "Encourage consultation with qualified healthcare professionals",
            "Clearly distinguish between established facts and theoretical concepts",
            "Avoid making predictions about individual health outcomes",
            "Recommend seeking emergency care for urgent symptoms",
            "Cite authoritative sources when providing medical information",
            "Clarify limitations of AI in medical contexts",
        ]
        
        # Create profile
        profile = ExpertProfile(
            expert_id="medical_ai",
            name="Medical AI",
            category=ExpertCategory.MEDICAL,
            description="Specialized AI for medical education and healthcare learning with appropriate safeguards. Provides educational content about anatomy, physiology, pharmacology, and clinical concepts.",
            system_prompt="""You are Medical AI, an educational assistant for medical and healthcare learning.

Your role is to:
- Provide educational information about medical topics
- Explain medical concepts clearly and accurately
- Help with understanding anatomy, physiology, and pathology
- Assist with medical terminology
- Explain pharmacological concepts
- Interpret lab results in an educational context
- Summarize clinical guidelines for learning purposes

IMPORTANT SAFEGUARDS:
- NEVER provide medical diagnosis or treatment recommendations
- ALWAYS include a disclaimer that this is for educational purposes only
- ALWAYS encourage consultation with qualified healthcare professionals
- NEVER predict individual health outcomes
- ALWAYS clarify when information is simplified for educational purposes

Educational approach:
- Start with fundamental concepts
- Use clear, accessible language
- Provide clinical correlations when helpful
- Include relevant anatomy and physiology
- Explain the "why" behind medical concepts
- Use examples and analogies appropriately
- Reference authoritative sources when possible

When discussing symptoms:
- Explain what symptoms typically indicate
- Describe common causes
- Explain the underlying mechanisms
- NEVER suggest specific diagnoses for individuals
- ALWAYS recommend professional evaluation

When discussing medications:
- Explain mechanisms of action
- Describe common uses
- Discuss potential side effects in general terms
- NEVER recommend specific medications for individuals
- ALWAYS emphasize the need for professional prescription

When interpreting lab results:
- Explain what the tests measure
- Describe normal ranges
- Explain what abnormal results might indicate
- NEVER interpret individual patient results
- ALWAYS recommend professional interpretation""",
            capabilities=capabilities,
            terminology=terminology,
            safety_policies=safety_policies,
            confidence_threshold=0.8,
            requires_disclaimer=True,
            disclaimer_text="⚠️ MEDICAL DISCLAIMER: This information is for educational purposes only and does not constitute medical advice, diagnosis, or treatment. Always consult with qualified healthcare professionals for medical concerns. In case of emergency, seek immediate medical attention.",
            preferred_model="gpt-4",
            memory_preferences={
                "remember_learning_level": True,
                "track_study_topics": True,
                "store_common_questions": True,
            },
        )
        
        super().__init__(profile)
        
        # Medical domain modules
        self.domain_modules = {
            "anatomy": self._anatomy_module,
            "physiology": self._physiology_module,
            "pharmacology": self._pharmacology_module,
            "pathology": self._pathology_module,
            "clinical": self._clinical_module,
            "terminology": self._terminology_module,
            "lab_results": self._lab_results_module,
        }
    
    def _generate_response(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate response using medical domain modules"""
        context = context or {}
        
        # Detect medical domain from context or prompt
        domain = context.get("domain", self._detect_domain(prompt))
        
        # Use domain-specific module if available
        if domain and domain in self.domain_modules:
            return self.domain_modules[domain](prompt, context)
        
        # Default medical response
        return self._general_medical_response(prompt, context)
    
    def _detect_domain(self, prompt: str) -> Optional[str]:
        """Detect the medical domain from the prompt"""
        prompt_lower = prompt.lower()
        
        domain_keywords = {
            "anatomy": ["anatomy", "organ", "structure", "body", "muscle", "bone", "nerve", "vessel"],
            "physiology": ["physiology", "function", "mechanism", "process", "system", "how", "works"],
            "pharmacology": ["drug", "medication", "pharmacology", "pharmaceutical", "medicine", "side effect", "dosage"],
            "pathology": ["disease", "condition", "disorder", "pathology", "etiology", "cause"],
            "clinical": ["symptom", "diagnosis", "treatment", "clinical", "patient", "presentation", "guideline"],
            "terminology": ["term", "definition", "meaning", "medical term", "abbreviation", "acronym"],
            "lab_results": ["lab", "test", "result", "blood", "interpretation", "normal", "abnormal"],
        }
        
        for domain, keywords in domain_keywords.items():
            if any(keyword in prompt_lower for keyword in keywords):
                return domain
        
        return None
    
    def _anatomy_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Anatomy-specific response handling"""
        response = f"[Anatomy Module]\n\n"
        
        response += "Anatomy is the study of the structure of the body and its parts.\n\n"
        response += "I can help you with:\n"
        response += "- Gross anatomy (organs and systems)\n"
        response += "- Microscopic anatomy (cells and tissues)\n"
        response += "- Regional anatomy (specific body regions)\n"
        response += "- Systemic anatomy (organ systems)\n"
        response += "- Developmental anatomy (embryology)\n\n"
        response += "Common anatomical topics include:\n"
        response += "- Skeletal system\n"
        response += "- Muscular system\n"
        response += "- Nervous system\n"
        response += "- Cardiovascular system\n"
        response += "- Respiratory system\n"
        response += "- Digestive system\n\n"
        response += "What anatomical structure or system would you like to learn about?"
        
        return response
    
    def _physiology_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Physiology-specific response handling"""
        response = f"[Physiology Module]\n\n"
        
        response += "Physiology is the study of how the body and its parts function.\n\n"
        response += "I can help you understand:\n"
        response += "- Cellular physiology\n"
        response += "- System physiology\n"
        response += "- Pathophysiology (disease mechanisms)\n"
        response += "- Exercise physiology\n"
        response += "- Neurophysiology\n\n"
        response += "Key physiological concepts include:\n"
        response += "- Homeostasis\n"
        response += "- Metabolism\n"
        response += "- Feedback mechanisms\n"
        response += "- Electrophysiology\n"
        response += "- Hemodynamics\n\n"
        response += "What physiological process or system would you like to explore?"
        
        return response
    
    def _pharmacology_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Pharmacology-specific response handling"""
        response = f"[Pharmacology Module]\n\n"
        
        response += "Pharmacology is the study of drugs and their effects on the body.\n\n"
        response += "I can help you understand:\n"
        response += "- Pharmacokinetics (what the body does to the drug)\n"
        response += "- Pharmacodynamics (what the drug does to the body)\n"
        response += "- Drug classifications\n"
        response += "- Mechanisms of action\n"
        response += "- Therapeutic uses\n"
        response += "- Adverse effects\n"
        response += "- Drug interactions\n\n"
        response += "⚠️ Note: I provide educational information only. Never use this information for self-medication. Always consult healthcare professionals.\n\n"
        response += "What pharmacological topic would you like to learn about?"
        
        return response
    
    def _pathology_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Pathology-specific response handling"""
        response = f"[Pathology Module]\n\n"
        
        response += "Pathology is the study of disease processes and their effects on the body.\n\n"
        response += "I can help you understand:\n"
        response += "- Etiology (causes of disease)\n"
        response += "- Pathogenesis (disease development)\n"
        response += "- Morphologic changes (structural changes)\n"
        response += "- Clinical significance\n"
        response += "- Disease classification\n"
        response += "- Diagnostic criteria\n\n"
        response += "What disease or pathological process would you like to learn about?"
        
        return response
    
    def _clinical_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Clinical medicine-specific response handling"""
        response = f"[Clinical Medicine Module]\n\n"
        
        response += "Clinical medicine applies medical knowledge to patient care.\n\n"
        response += "I can help you understand:\n"
        response += "- Clinical presentations\n"
        response += "- Diagnostic approaches\n"
        response += "- Treatment principles\n"
        response += "- Clinical guidelines\n"
        response += "- Evidence-based medicine\n"
        response += "- Clinical reasoning\n\n"
        response += "⚠️ IMPORTANT: I provide educational information only. I cannot:\n"
        response += "- Diagnose medical conditions\n"
        response += "- Recommend treatments\n"
        response += "- Interpret individual symptoms\n"
        response += "- Make clinical decisions\n\n"
        response += "Always consult qualified healthcare professionals for medical concerns.\n\n"
        response += "What clinical topic would you like to explore for educational purposes?"
        
        return response
    
    def _terminology_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Medical terminology-specific response handling"""
        response = f"[Medical Terminology Module]\n\n"
        
        response += "Medical terminology uses specific prefixes, roots, and suffixes.\n\n"
        response += "I can help you with:\n"
        response += "- Medical term definitions\n"
        response += "- Word breakdown (prefix, root, suffix)\n"
        response += "- Abbreviations and acronyms\n"
        response += "- Pronunciation guides\n"
        response += "- Etymology of medical terms\n\n"
        response += "Common medical word parts:\n"
        response += "- Prefixes: cardio-, neuro-, gastro-, derm-\n"
        response += "- Roots: cardi, neur, gastr, derm\n"
        response += "- Suffixes: -itis, -logy, -ectomy, -pathy\n\n"
        response += "What medical term would you like me to explain?"
        
        return response
    
    def _lab_results_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Lab result interpretation-specific response handling"""
        response = f"[Lab Results Module]\n\n"
        
        response += "Laboratory tests provide important clinical information.\n\n"
        response += "I can help you understand:\n"
        response += "- What specific tests measure\n"
        response += "- Normal reference ranges\n"
        response += "- What abnormal results might indicate\n"
        response += "- Test limitations and confounding factors\n"
        response += "- How tests are used diagnostically\n\n"
        response += "⚠️ IMPORTANT: I provide educational information only. I cannot:\n"
        response += "- Interpret individual patient lab results\n"
        response += "- Make diagnoses based on lab values\n"
        response += "- Recommend treatment based on lab results\n\n"
        response += "Always have qualified healthcare professionals interpret your lab results.\n\n"
        response += "What lab test or type of result would you like to learn about?"
        
        return response
    
    def _general_medical_response(self, prompt: str, context: Dict[str, Any]) -> str:
        """General medical response when no specific domain is detected"""
        response = f"[Medical AI]\n\n"
        
        response += "I'm here to help with medical education and learning.\n\n"
        response += "**Medical Domains:**\n"
        response += "- Anatomy\n"
        response += "- Physiology\n"
        response += "- Pharmacology\n"
        response += "- Pathology\n"
        response += "- Clinical Medicine\n"
        response += "- Medical Terminology\n"
        response += "- Lab Result Interpretation\n\n"
        response += "**Educational Services:**\n"
        response += "- Concept explanations\n"
        response += "- Mechanism descriptions\n"
        response += "- Clinical correlations\n"
        response += "- Guideline summaries\n"
        response += "- Terminology clarification\n\n"
        response += "⚠️ MEDICAL DISCLAIMER: This information is for educational purposes only and does not constitute medical advice, diagnosis, or treatment. Always consult with qualified healthcare professionals for medical concerns.\n\n"
        response += "What medical topic would you like to learn about?"
        
        return response
    
    def explain_symptom(self, symptom: str) -> Dict[str, Any]:
        """Provide educational information about a symptom"""
        return {
            "symptom": symptom,
            "educational_info": f"Educational information about {symptom}",
            "general_causes": ["Cause 1", "Cause 2", "Cause 3"],
            "mechanism": "Explanation of the underlying mechanism",
            "disclaimer": "This is for educational purposes only. Consult a healthcare professional for personal medical concerns.",
        }
    
    def explain_medication(self, medication: str) -> Dict[str, Any]:
        """Provide educational information about a medication"""
        return {
            "medication": medication,
            "class": "Drug class",
            "mechanism_of_action": "How the medication works",
            "common_uses": ["Use 1", "Use 2"],
            "common_side_effects": ["Side effect 1", "Side effect 2"],
            "contraindications": ["Contraindication 1"],
            "disclaimer": "This is for educational purposes only. Never use this information for self-medication. Consult a healthcare professional.",
        }
