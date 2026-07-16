"""
Education AI Expert - Phase 4

Specialized expert for students and learning.
Capabilities:
- Mathematics
- Physics
- Chemistry
- Biology
- English
- Computer Science
- History
- Geography
- Economics

Features:
- Step-by-step explanations
- Homework help
- Exam preparation
- Quiz generation
- Flashcards
- Formula sheets
- Interactive teaching
- Diagram generation
- Practice questions
"""

from typing import Dict, List, Any, Optional
from .expert_base import ExpertBase, ExpertProfile, ExpertCapabilities, ExpertCategory


class EducationAI(ExpertBase):
    """
    Expert AI specialized for education and learning.
    Provides step-by-step explanations, homework help, and exam preparation.
    """
    
    def __init__(self):
        # Define capabilities
        capabilities = ExpertCapabilities(
            primary_domains=[
                "mathematics", "physics", "chemistry", "biology",
                "english", "computer_science", "history", "geography", "economics"
            ],
            supported_languages=["English", "Spanish", "French", "German"],
            specialized_tools=[
                "calculator", "formula_generator", "quiz_generator",
                "flashcard_creator", "diagram_generator", "equation_solver"
            ],
            knowledge_sources=["textbooks", "academic_papers", "educational_websites"],
            output_formats=["plain_text", "markdown", "latex", "diagrams", "quizzes"],
            supports_streaming=True,
            supports_multimodal=True,
        )
        
        # Define terminology
        terminology = {
            "step-by-step": "Breaking down complex problems into manageable steps",
            "conceptual understanding": "Grasping the underlying principles, not just memorization",
            "active recall": "Testing yourself to strengthen memory",
            "spaced repetition": "Reviewing material at increasing intervals",
            "formative assessment": "Ongoing evaluation to guide learning",
            "summative assessment": "Final evaluation of learning outcomes",
            "scaffolding": "Providing temporary support that is gradually removed",
            "metacognition": "Thinking about one's own thinking process",
        }
        
        # Define safety policies
        safety_policies = [
            "Never provide answers that enable academic dishonesty",
            "Encourage understanding over memorization",
            "Clarify when information may be simplified for educational purposes",
            "Recommend consulting primary sources for critical information",
            "Avoid providing medical or legal advice beyond general education",
        ]
        
        # Create profile
        profile = ExpertProfile(
            expert_id="education_ai",
            name="Education AI",
            category=ExpertCategory.EDUCATION,
            description="Specialized AI for students and learning with step-by-step explanations, homework help, and exam preparation across multiple subjects.",
            system_prompt="""You are Education AI, a specialized assistant for students and learners.

Your role is to:
- Provide clear, step-by-step explanations of concepts
- Help with homework by guiding understanding, not just giving answers
- Assist with exam preparation through targeted practice
- Generate practice questions and quizzes
- Create flashcards and study materials
- Explain formulas and their applications
- Generate diagrams and visual aids when helpful

Teaching approach:
- Start with the basics and build up gradually
- Use analogies and real-world examples
- Check for understanding at key points
- Encourage critical thinking
- Adapt to the student's level
- Be patient and encouraging

When solving problems:
- Show your work clearly
- Explain each step
- Highlight key concepts
- Provide alternative methods when applicable
- Verify the answer

For homework help:
- Guide the student to the solution
- Explain the underlying concepts
- Don't just provide the final answer
- Encourage the student to try similar problems

For exam preparation:
- Focus on key concepts and common pitfalls
- Provide practice questions with solutions
- Create study schedules and strategies
- Teach test-taking techniques""",
            capabilities=capabilities,
            terminology=terminology,
            safety_policies=safety_policies,
            confidence_threshold=0.7,
            preferred_model="gpt-4",
            memory_preferences={
                "remember_learning_style": True,
                "track_progress": True,
                "store_common_mistakes": True,
                "maintain_study_history": True,
            },
        )
        
        super().__init__(profile)
        
        # Subject-specific modules
        self.subject_modules = {
            "mathematics": self._mathematics_module,
            "physics": self._physics_module,
            "chemistry": self._chemistry_module,
            "biology": self._biology_module,
            "english": self._english_module,
            "computer_science": self._computer_science_module,
            "history": self._history_module,
            "geography": self._geography_module,
            "economics": self._economics_module,
        }
    
    def _generate_response(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate response using subject-specific modules"""
        context = context or {}
        
        # Detect subject from context or prompt
        subject = context.get("subject", self._detect_subject(prompt))
        
        # Use subject-specific module if available
        if subject and subject in self.subject_modules:
            return self.subject_modules[subject](prompt, context)
        
        # Default general education response
        return self._general_education_response(prompt, context)
    
    def _detect_subject(self, prompt: str) -> Optional[str]:
        """Detect the subject from the prompt"""
        prompt_lower = prompt.lower()
        
        subject_keywords = {
            "mathematics": ["math", "algebra", "calculus", "geometry", "statistics", "equation", "formula"],
            "physics": ["physics", "force", "motion", "energy", "quantum", "mechanics", "optics"],
            "chemistry": ["chemistry", "chemical", "reaction", "molecule", "atom", "periodic", "bond"],
            "biology": ["biology", "cell", "organism", "genetics", "evolution", "ecosystem", "anatomy"],
            "english": ["english", "grammar", "literature", "essay", "writing", "poetry", "shakespeare"],
            "computer_science": ["programming", "code", "algorithm", "data structure", "computer", "software"],
            "history": ["history", "historical", "war", "ancient", "century", "empire", "revolution"],
            "geography": ["geography", "map", "country", "climate", "terrain", "continent", "population"],
            "economics": ["economics", "economy", "supply", "demand", "market", "inflation", "gdp"],
        }
        
        for subject, keywords in subject_keywords.items():
            if any(keyword in prompt_lower for keyword in keywords):
                return subject
        
        return None
    
    def _mathematics_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Mathematics-specific response handling"""
        response = f"[Mathematics Module]\n\n"
        
        # Check for specific math topics
        if "solve" in prompt.lower() or "calculate" in prompt.lower():
            response += "I'll help you solve this step by step:\n\n"
            response += "1. Identify the type of problem\n"
            response += "2. Write down the given information\n"
            response += "3. Choose the appropriate formula or method\n"
            response += "4. Show the calculation steps\n"
            response += "5. Verify the answer\n\n"
            response += "Please provide the specific problem you'd like me to solve."
        elif "formula" in prompt.lower():
            response += "Here are relevant formulas for this topic:\n\n"
            response += "- Key formula 1\n"
            response += "- Key formula 2\n"
            response += "- Key formula 3\n\n"
            response += "Would you like me to explain any of these formulas in detail?"
        else:
            response += "I can help you with:\n"
            response += "- Solving mathematical problems step by step\n"
            response += "- Explaining mathematical concepts\n"
            response += "- Providing formulas and their applications\n"
            response += "- Creating practice problems\n"
            response += "- Explaining proofs and theorems\n\n"
            response += "What specific mathematics topic would you like help with?"
        
        return response
    
    def _physics_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Physics-specific response handling"""
        response = f"[Physics Module]\n\n"
        
        response += "Physics concepts often involve understanding fundamental principles.\n\n"
        response += "I can help you with:\n"
        response += "- Mechanics (forces, motion, energy)\n"
        response += "- Thermodynamics\n"
        response += "- Electromagnetism\n"
        response += "- Waves and optics\n"
        response += "- Modern physics (quantum, relativity)\n\n"
        response += "Please provide the specific physics problem or concept you'd like to explore."
        
        return response
    
    def _chemistry_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Chemistry-specific response handling"""
        response = f"[Chemistry Module]\n\n"
        
        response += "Chemistry involves understanding matter and its interactions.\n\n"
        response += "I can help you with:\n"
        response += "- Chemical reactions and equations\n"
        response += "- Atomic structure and bonding\n"
        response += "- Periodic table trends\n"
        response += "- Stoichiometry\n"
        response += "- Organic chemistry\n"
        response += "- Acid-base chemistry\n\n"
        response += "What chemistry topic would you like to explore?"
        
        return response
    
    def _biology_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Biology-specific response handling"""
        response = f"[Biology Module]\n\n"
        
        response += "Biology is the study of living organisms.\n\n"
        response += "I can help you with:\n"
        response += "- Cell biology\n"
        response += "- Genetics and heredity\n"
        response += "- Evolution and natural selection\n"
        response += "- Ecology and ecosystems\n"
        response += "- Human anatomy and physiology\n"
        response += "- Molecular biology\n\n"
        response += "What biology topic would you like to learn about?"
        
        return response
    
    def _english_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """English-specific response handling"""
        response = f"[English Module]\n\n"
        
        response += "I can help you with:\n"
        response += "- Grammar and punctuation\n"
        response += "- Essay writing and structure\n"
        response += "- Literary analysis\n"
        response += "- Poetry analysis\n"
        response += "- Vocabulary building\n"
        response += "- Reading comprehension\n\n"
        response += "What English topic would you like assistance with?"
        
        return response
    
    def _computer_science_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Computer Science-specific response handling"""
        response = f"[Computer Science Module]\n\n"
        
        response += "I can help you with:\n"
        response += "- Programming concepts and algorithms\n"
        response += "- Data structures\n"
        response += "- Software development\n"
        response += "- Computer architecture\n"
        response += "- Networking basics\n"
        response += "- Database concepts\n\n"
        response += "What computer science topic would you like to explore?"
        
        return response
    
    def _history_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """History-specific response handling"""
        response = f"[History Module]\n\n"
        
        response += "I can help you with:\n"
        response += "- Historical events and timelines\n"
        response += "- Historical analysis and interpretation\n"
        response += "- Cause and effect relationships\n"
        response += "- Historical figures and their impact\n"
        response += "- Primary source analysis\n"
        response += "- Historical context understanding\n\n"
        response += "What historical period or topic would you like to explore?"
        
        return response
    
    def _geography_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Geography-specific response handling"""
        response = f"[Geography Module]\n\n"
        
        response += "I can help you with:\n"
        response += "- Physical geography (landforms, climate)\n"
        response += "- Human geography (population, culture)\n"
        response += "- Map reading and interpretation\n"
        response += "- Geographic information systems\n"
        response += "- Regional studies\n"
        response += "- Environmental geography\n\n"
        response += "What geography topic would you like to learn about?"
        
        return response
    
    def _economics_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Economics-specific response handling"""
        response = f"[Economics Module]\n\n"
        
        response += "I can help you with:\n"
        response += "- Microeconomics (individual markets)\n"
        response += "- Macroeconomics (economy-wide factors)\n"
        response += "- Supply and demand analysis\n"
        response += "- Market structures\n"
        response += "- Economic indicators\n"
        response += "- International trade\n\n"
        response += "What economics topic would you like to explore?"
        
        return response
    
    def _general_education_response(self, prompt: str, context: Dict[str, Any]) -> str:
        """General education response when no specific subject is detected"""
        response = f"[Education AI]\n\n"
        
        response += "I'm here to help you learn! I can assist with:\n\n"
        response += "**Subjects:**\n"
        response += "- Mathematics\n"
        response += "- Physics\n"
        response += "- Chemistry\n"
        response += "- Biology\n"
        response += "- English\n"
        response += "- Computer Science\n"
        response += "- History\n"
        response += "- Geography\n"
        response += "- Economics\n\n"
        response += "**Services:**\n"
        response += "- Step-by-step explanations\n"
        response += "- Homework guidance\n"
        response += "- Exam preparation\n"
        response += "- Quiz generation\n"
        response += "- Flashcard creation\n"
        response += "- Formula sheets\n"
        response += "- Practice questions\n\n"
        response += "Please let me know what subject or topic you'd like help with!"
        
        return response
    
    def generate_quiz(self, subject: str, topic: str, num_questions: int = 5) -> Dict[str, Any]:
        """Generate a quiz for a specific subject and topic"""
        return {
            "subject": subject,
            "topic": topic,
            "questions": [
                {
                    "question_id": i + 1,
                    "question": f"Sample question {i + 1} about {topic}",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "A",
                    "-explanation": f"Explanation for question {i + 1}",
                }
                for i in range(num_questions)
            ],
        }
    
    def create_flashcards(self, topic: str, num_cards: int = 10) -> List[Dict[str, str]]:
        """Create flashcards for a topic"""
        return [
            {
                "card_id": i + 1,
                "front": f"Term {i + 1} related to {topic}",
                "back": f"Definition of term {i + 1}",
            }
            for i in range(num_cards)
        ]
    
    def generate_formula_sheet(self, subject: str) -> Dict[str, Any]:
        """Generate a formula sheet for a specific subject"""
        formulas = {
            "mathematics": ["Quadratic formula", "Pythagorean theorem", "Derivative rules"],
            "physics": ["Newton's laws", "Kinematic equations", "Energy formulas"],
            "chemistry": ["Ideal gas law", "Molarity formula", "pH calculation"],
        }
        
        return {
            "subject": subject,
            "formulas": formulas.get(subject, ["No formulas available"]),
        }
