import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Agent:
    name: str
    description: str
    capabilities: list[str]
    system_prompt: str
    max_tokens: int = 4096
    temperature: float = 0.7
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentRegistry:
    def __init__(self):
        self.agents: dict[str, Agent] = {}
        self._register_defaults()

    def _register_defaults(self):
        defaults = [
            Agent("SocraticTutor", "Asks guiding questions to help learners discover answers", ["tutoring", "socratic", "guided-learning"], "You are a Socratic tutor. Ask probing questions to guide the student.", 2048, 0.8),
            Agent("QuizGenerator", "Creates quizzes from content", ["quiz", "assessment", "generation"], "Generate a quiz based on the provided content.", 2048, 0.7),
            Agent("StudyPlanner", "Creates personalized study plans", ["planning", "study", "scheduling"], "Create a study plan tailored to the user's goals.", 2048, 0.6),
            Agent("Visualizer", "Generates visual descriptions and diagram specs", ["visualization", "diagrams", "concepts"], "Describe visualizations and diagram structures.", 4096, 0.7),
            Agent("Conceptualizer", "Breaks complex topics into concepts", ["concepts", "simplification", "learning"], "Break down complex topics into understandable concepts.", 4096, 0.7),
            Agent("FeedbackAnalyzer", "Analyzes user responses for improvement", ["feedback", "analysis", "improvement"], "Analyze the user's response and provide constructive feedback.", 2048, 0.6),
            Agent("FlashcardMaker", "Creates flashcards for memorization", ["flashcards", "memorization", "study-aids"], "Generate flashcards from the given content.", 1024, 0.7),
            Agent("Summarizer", "Summarizes long content", ["summarization", "condensing", "review"], "Summarize the provided text concisely.", 2048, 0.5),
            Agent("Explainer", "Explains concepts step by step", ["explanation", "tutorial", "step-by-step"], "Explain the concept in clear, step-by-step terms.", 2048, 0.7),
            Agent("Debugger", "Helps debug code", ["debugging", "code", "troubleshooting"], "Help identify and fix bugs in the provided code.", 4096, 0.6),
            Agent("Proofreader", "Reviews and corrects text", ["proofreading", "grammar", "writing"], "Review the text for grammar, clarity, and style.", 2048, 0.5),
            Agent("Analyst", "Analyzes data and trends", ["analysis", "data", "insights"], "Analyze the data and provide insights.", 4096, 0.6),
            Agent("CreativeWriter", "Generates creative content", ["creative", "writing", "storytelling"], "Generate creative and engaging content.", 4096, 0.9),
            Agent("MathSolver", "Solves mathematical problems", ["math", "calculation", "problem-solving"], "Solve the math problem step by step.", 2048, 0.3),
            Agent("CodeReviewer", "Reviews code for best practices", ["code-review", "best-practices", "security"], "Review the code for best practices and security issues.", 4096, 0.5),
            Agent("InterviewCoach", "Prepares users for interviews", ["interview", "career", "preparation"], "Help the user prepare for interviews with questions and feedback.", 2048, 0.8),
            Agent("LanguageTutor", "Teaches new languages", ["language", "tutoring", "grammar"], "Teach the language concept with examples and exercises.", 2048, 0.7),
            Agent("ResearchAssistant", "Helps with research tasks", ["research", "literature-review", "sources"], "Assist with research by finding and summarizing sources.", 4096, 0.6),
            Agent("IdeaGenerator", "Generates ideas and brainstorming", ["ideation", "brainstorming", "creativity"], "Generate creative ideas and suggestions.", 2048, 0.9),
            Agent("Prioritizer", "Helps prioritize tasks", ["prioritization", "productivity", "planning"], "Help prioritize tasks based on importance and urgency.", 2048, 0.5),
            Agent("Reflector", "Encourages reflective thinking", ["reflection", "metacognition", "learning"], "Ask reflective questions to deepen understanding.", 2048, 0.8),
            Agent("DebateCoach", "Prepares arguments for debates", ["debate", "argumentation", "critical-thinking"], "Help construct and refine arguments for debate.", 2048, 0.7),
            Agent("DiagramExpert", "Creates ASCII and structured diagrams", ["diagrams", "ascii", "structure"], "Generate diagram descriptions and ASCII representations.", 4096, 0.6),
            Agent("NoteTaker", "Organizes notes and outlines", ["notes", "organization", "outlining"], "Organize information into clear notes and outlines.", 2048, 0.5),
            Agent("RubricBuilder", "Creates grading rubrics", ["rubric", "grading", "assessment"], "Create a detailed grading rubric.", 2048, 0.6),
            Agent("CaseStudyWriter", "Writes case studies", ["case-study", "writing", "analysis"], "Write a case study based on the scenario.", 4096, 0.7),
            Agent("GoalSetter", "Helps set SMART goals", ["goals", "planning", "smart-goals"], "Help formulate SMART goals.", 1024, 0.6),
            Agent("Motivator", "Provides encouragement and motivation", ["motivation", "encouragement", "mindset"], "Motivate and encourage the learner.", 1024, 0.8),
            Agent("MetacognitionCoach", "Teaches learning how to learn", ["metacognition", "learning-strategies", "self-awareness"], "Teach strategies for effective learning.", 2048, 0.7),
            Agent("PeerReviewer", "Simulates peer review feedback", ["peer-review", "feedback", "collaboration"], "Provide peer-review style feedback.", 2048, 0.6),
            Agent("CareerAdvisor", "Advises on career paths", ["career", "guidance", "professional-development"], "Provide career advice and path suggestions.", 2048, 0.7),
            Agent("TimeManager", "Teaches time management", ["time-management", "productivity", "scheduling"], "Teach time management techniques.", 2048, 0.6),
            Agent("StressManager", "Helps manage stress and burnout", ["stress", "wellbeing", "mental-health"], "Provide stress management techniques.", 1024, 0.8),
            Agent("NoteSummarizer", "Summarizes notes into key points", ["summarization", "notes", "key-points"], "Summarize notes into bullet key points.", 2048, 0.5),
            Agent("QuestionAnswerer", "Answers questions directly", ["qa", "direct", "knowledge"], "Answer the user's question directly and accurately.", 2048, 0.5),
            Agent("ConceptMapper", "Creates concept maps", ["concept-map", "relationships", "structure"], "Describe a concept map for the topic.", 4096, 0.6),
            Agent("AnalogyMaker", "Creates analogies for understanding", ["analogy", "comparison", "understanding"], "Create analogies to explain concepts.", 2048, 0.8),
            Agent("ScenarioDesigner", "Designs learning scenarios", ["scenario", "design", "learning"], "Design a realistic learning scenario.", 4096, 0.7),
            Agent("Facilitator", "Facilitates group discussions", ["facilitation", "discussion", "collaboration"], "Facilitate a productive discussion.", 2048, 0.7),
            Agent("ReflectionPrompter", "Prompts reflective journaling", ["reflection", "journaling", "prompts"], "Prompt reflective journaling entries.", 1024, 0.8),
            Agent("KnowledgeGapFinder", "Identifies knowledge gaps", ["knowledge-gap", "diagnostic", "assessment"], "Identify potential knowledge gaps.", 2048, 0.6),
            Agent("StudyBuddy", "Acts as a friendly study companion", ["companion", "study", "support"], "Be a friendly study companion.", 2048, 0.8),
            Agent("Simulator", "Creates simulations and role-plays", ["simulation", "role-play", "practice"], "Create a simulation or role-play scenario.", 4096, 0.8),
            Agent("Critic", "Provides constructive criticism", ["critique", "feedback", "improvement"], "Provide constructive criticism.", 2048, 0.6),
            Agent("Encourager", "Gives positive reinforcement", ["encouragement", "positive-reinforcement", "mindset"], "Give positive reinforcement and encouragement.", 1024, 0.9),
            Agent("ChallengeMaster", "Presents challenges and puzzles", ["challenges", "puzzles", "critical-thinking"], "Present challenges and puzzles.", 2048, 0.8),
            Agent("Connector", "Connects ideas across domains", ["connections", "interdisciplinary", "synthesis"], "Connect ideas across different domains.", 4096, 0.7),
            Agent("Storyteller", "Narrates content as stories", ["storytelling", "narrative", "engagement"], "Narrate content as an engaging story.", 4096, 0.9),
            Agent("GlossaryBuilder", "Builds glossaries and definitions", ["glossary", "definitions", "reference"], "Build a glossary of key terms.", 2048, 0.5),
            Agent("LearningPathDesigner", "Designs end-to-end learning paths", ["learning-path", "curriculum", "sequencing"], "Design a complete learning path.", 4096, 0.6),
            Agent("Mentor", "Provides mentorship and guidance", ["mentorship", "guidance", "support"], "Provide mentorship and guidance.", 2048, 0.7),
        ]
        for agent in defaults:
            self.register(agent)

    def register(self, agent: Agent):
        self.agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name}")

    def get_agent(self, name: str) -> Agent | None:
        return self.agents.get(name)

    def list_agents(self) -> list[Agent]:
        return list(self.agents.values())


_registry_instance: AgentRegistry | None = None


def get_registry() -> AgentRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = AgentRegistry()
    return _registry_instance
