"""
Programming AI Expert - Phase 4

Specialized expert for software development and programming.
Programming languages:
- Python, Java, JavaScript, C, C++, C#, Go, Rust, Kotlin, Swift, PHP

Frameworks:
- React, Vue, Angular, FastAPI, Django, Flask, Node.js, Spring, Laravel

Capabilities:
- Debugging
- Refactoring
- Architecture
- Code review
- Testing
- Documentation
- Deployment
- API generation
"""

from typing import Dict, List, Any, Optional
from .expert_base import ExpertBase, ExpertProfile, ExpertCapabilities, ExpertCategory


class ProgrammingAI(ExpertBase):
    """
    Expert AI specialized for software development and programming.
    Provides comprehensive support for coding, debugging, architecture, and best practices.
    """
    
    def __init__(self):
        # Define capabilities
        capabilities = ExpertCapabilities(
            primary_domains=[
                "software_development", "web_development", "mobile_development",
                "backend", "frontend", "devops", "database", "testing"
            ],
            supported_languages=[
                "Python", "Java", "JavaScript", "TypeScript", "C", "C++", "C#",
                "Go", "Rust", "Kotlin", "Swift", "PHP", "Ruby", "Shell"
            ],
            supported_frameworks=[
                "React", "Vue", "Angular", "Svelte", "FastAPI", "Django", "Flask",
                "Node.js", "Express", "Spring", "Laravel", "Rails", ".NET"
            ],
            specialized_tools=[
                "code_analyzer", "debugger", "refactoring_tool", "code_reviewer",
                "test_generator", "api_generator", "documentation_generator",
                "deployment_helper", "dependency_manager"
            ],
            knowledge_sources=[
                "official_documentation", "stack_overflow", "github_repos",
                "programming_blogs", "api_references", "best_practice_guides"
            ],
            output_formats=["code", "markdown", "json", "diagrams", "api_docs"],
            supports_streaming=True,
            supports_multimodal=False,
        )
        
        # Define terminology
        terminology = {
            "debugging": "The process of identifying and removing errors from computer hardware or software",
            "refactoring": "The process of restructuring existing computer code without changing its external behavior",
            "api": "Application Programming Interface - a set of functions and procedures allowing the creation of applications",
            "framework": "A platform that provides a foundation for developing software applications",
            "library": "A collection of pre-written code that developers can use to optimize tasks",
            "deployment": "The process of making software available for use",
            "ci_cd": "Continuous Integration/Continuous Deployment - automation of software development processes",
            "version_control": "A system that records changes to files over time",
            "design_pattern": "A general reusable solution to a commonly occurring problem in software design",
            "algorithm": "A step-by-step procedure for solving a problem or accomplishing a task",
        }
        
        # Define safety policies
        safety_policies = [
            "Never generate malicious code or exploits",
            "Avoid suggesting code that could be used for harmful purposes",
            "Always recommend security best practices",
            "Encourage proper error handling and validation",
            "Warn about deprecated or insecure practices",
            "Recommend testing and validation before deployment",
        ]
        
        # Create profile
        profile = ExpertProfile(
            expert_id="programming_ai",
            name="Programming AI",
            category=ExpertCategory.PROGRAMMING,
            description="Specialized AI for software development and programming. Supports multiple languages and frameworks with capabilities for debugging, refactoring, architecture, code review, testing, documentation, and deployment.",
            system_prompt="""You are Programming AI, a specialized assistant for software development and programming.

Your role is to:
- Help with coding and debugging
- Provide code reviews and suggestions
- Assist with architecture and design decisions
- Generate documentation and API specifications
- Help with testing strategies
- Assist with deployment and DevOps
- Explain programming concepts clearly
- Suggest best practices and patterns

Programming approach:
- Write clean, readable, and maintainable code
- Follow language-specific conventions and style guides
- Include proper error handling and validation
- Add comments for complex logic
- Consider performance and scalability
- Prioritize security and best practices
- Use appropriate design patterns
- Write testable code

When debugging:
- Analyze the error message carefully
- Identify the root cause
- Provide step-by-step debugging guidance
- Suggest fixes with explanations
- Recommend preventive measures
- Consider edge cases

When reviewing code:
- Check for bugs and logic errors
- Assess code quality and readability
- Suggest improvements and optimizations
- Verify adherence to best practices
- Check for security vulnerabilities
- Recommend testing strategies

When architecting:
- Consider scalability and maintainability
- Choose appropriate design patterns
- Plan for future extensibility
- Consider performance implications
- Evaluate technology choices
- Document architectural decisions

When generating code:
- Follow language-specific conventions
- Include necessary imports and dependencies
- Add error handling
- Provide usage examples
- Document complex logic
- Consider edge cases""",
            capabilities=capabilities,
            terminology=terminology,
            safety_policies=safety_policies,
            confidence_threshold=0.75,
            preferred_model="gpt-4",
            memory_preferences={
                "remember_language_preferences": True,
                "track_common_patterns": True,
                "store_project_context": True,
                "maintain_code_snippets": True,
            },
        )
        
        super().__init__(profile)
        
        # Language-specific modules
        self.language_modules = {
            "python": self._python_module,
            "javascript": self._javascript_module,
            "java": self._java_module,
            "cpp": self._cpp_module,
            "csharp": self._csharp_module,
            "go": self._go_module,
            "rust": self._rust_module,
            "typescript": self._typescript_module,
        }
        
        # Framework-specific modules
        self.framework_modules = {
            "react": self._react_module,
            "vue": self._vue_module,
            "angular": self._angular_module,
            "fastapi": self._fastapi_module,
            "django": self._django_module,
            "flask": self._flask_module,
            "nodejs": self._nodejs_module,
            "spring": self._spring_module,
        }
    
    def _generate_response(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate response using language/framework-specific modules"""
        context = context or {}
        
        # Detect language from context or prompt
        language = context.get("language", self._detect_language(prompt))
        
        # Detect framework from context or prompt
        framework = context.get("framework", self._detect_framework(prompt))
        
        # Use framework-specific module if available
        if framework and framework in self.framework_modules:
            return self.framework_modules[framework](prompt, context)
        
        # Use language-specific module if available
        if language and language in self.language_modules:
            return self.language_modules[language](prompt, context)
        
        # Default programming response
        return self._general_programming_response(prompt, context)
    
    def _detect_language(self, prompt: str) -> Optional[str]:
        """Detect the programming language from the prompt"""
        prompt_lower = prompt.lower()
        
        language_keywords = {
            "python": ["python", "django", "flask", "fastapi", "pandas", "numpy", ".py"],
            "javascript": ["javascript", "js", "node", "react", "vue", "angular", ".js", ".jsx"],
            "java": ["java", "spring", "maven", "gradle", ".java"],
            "cpp": ["c++", "cpp", "cplusplus", ".cpp", ".hpp"],
            "csharp": ["c#", "csharp", ".net", "asp.net", ".cs"],
            "go": ["go", "golang", ".go"],
            "rust": ["rust", "cargo", ".rs"],
            "typescript": ["typescript", "ts", ".ts", ".tsx"],
        }
        
        for language, keywords in language_keywords.items():
            if any(keyword in prompt_lower for keyword in keywords):
                return language
        
        return None
    
    def _detect_framework(self, prompt: str) -> Optional[str]:
        """Detect the framework from the prompt"""
        prompt_lower = prompt.lower()
        
        framework_keywords = {
            "react": ["react", "jsx", "hooks", "redux"],
            "vue": ["vue", "vuex", "vuetify"],
            "angular": ["angular", "typescript", "rxjs"],
            "fastapi": ["fastapi", "pydantic", "uvicorn"],
            "django": ["django", "orm", "migrations"],
            "flask": ["flask", "jinja", "blueprint"],
            "nodejs": ["node", "express", "npm"],
            "spring": ["spring", "spring boot", "java"],
        }
        
        for framework, keywords in framework_keywords.items():
            if any(keyword in prompt_lower for keyword in keywords):
                return framework
        
        return None
    
    def _python_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Python-specific response handling"""
        response = f"[Python Module]\n\n"
        
        if "debug" in prompt.lower() or "error" in prompt.lower():
            response += "I'll help you debug your Python code:\n\n"
            response += "1. Share the error message you're receiving\n"
            response += "2. Provide the relevant code snippet\n"
            response += "3. Explain what you're trying to achieve\n\n"
            response += "Common Python errors I can help with:\n"
            response += "- SyntaxError\n"
            response += "- IndentationError\n"
            response += "- NameError\n"
            response += "- TypeError\n"
            response += "- ImportError\n"
            response += "- AttributeError\n\n"
        elif "code" in prompt.lower() or "write" in prompt.lower():
            response += "I can help you write Python code. Please specify:\n"
            response += "- What functionality you need\n"
            response += "- Any specific libraries or frameworks\n"
            response += "- Input/output requirements\n"
            response += "- Performance considerations\n\n"
        else:
            response += "I can help you with:\n"
            response += "- Python coding and debugging\n"
            response += "- Frameworks (Django, Flask, FastAPI)\n"
            response += "- Data science (Pandas, NumPy)\n"
            response += "- Web development\n"
            response += "- Scripting and automation\n"
            response += "- Best practices and patterns\n\n"
        
        return response
    
    def _javascript_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """JavaScript-specific response handling"""
        response = f"[JavaScript Module]\n\n"
        
        response += "I can help you with:\n"
        response += "- JavaScript/ES6+ coding\n"
        response += "- Frontend frameworks (React, Vue, Angular)\n"
        response += "- Backend development (Node.js, Express)\n"
        response += "- Asynchronous programming\n"
        response += "- DOM manipulation\n"
        response += "- API integration\n"
        response += "- Testing and debugging\n\n"
        response += "What JavaScript-related task can I help you with?"
        
        return response
    
    def _java_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Java-specific response handling"""
        response = f"[Java Module]\n\n"
        
        response += "I can help you with:\n"
        response += "- Java coding and debugging\n"
        response += "- Spring Framework\n"
        response += "- Object-oriented programming\n"
        response += "- Multithreading\n"
        response += "- Database connectivity (JDBC, JPA)\n"
        response += "- Build tools (Maven, Gradle)\n"
        response += "- Enterprise applications\n\n"
        response += "What Java-related task can I help you with?"
        
        return response
    
    def _cpp_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """C++-specific response handling"""
        response = f"[C++ Module]\n\n"
        
        response += "I can help you with:\n"
        response += "- C++ coding and debugging\n"
        response += "- Memory management\n"
        response += "- STL (Standard Template Library)\n"
        response += "- Object-oriented programming\n"
        response += "- Template programming\n"
        response += "- Performance optimization\n"
        response += "- System programming\n\n"
        response += "What C++-related task can I help you with?"
        
        return response
    
    def _csharp_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """C#-specific response handling"""
        response = f"[C# Module]\n\n"
        
        response += "I can help you with:\n"
        response += "- C# coding and debugging\n"
        response += "- .NET Framework and .NET Core\n"
        response += "- ASP.NET web development\n"
        response += "- Entity Framework\n"
        response += "- Windows applications\n"
        response += "- LINQ and async programming\n"
        response += "- Visual Studio integration\n\n"
        response += "What C#-related task can I help you with?"
        
        return response
    
    def _go_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Go-specific response handling"""
        response = f"[Go Module]\n\n"
        
        response += "I can help you with:\n"
        response += "- Go coding and debugging\n"
        response += "- Concurrency and goroutines\n"
        response += "- Channels\n"
        response += "- Web development with Go\n"
        response += "- Microservices\n"
        response += "- Testing in Go\n"
        response += "- Performance optimization\n\n"
        response += "What Go-related task can I help you with?"
        
        return response
    
    def _rust_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Rust-specific response handling"""
        response = f"[Rust Module]\n\n"
        
        response += "I can help you with:\n"
        response += "- Rust coding and debugging\n"
        response += "- Ownership and borrowing\n"
        response += "- Memory safety\n"
        response += "- Cargo package manager\n"
        response += "- Systems programming\n"
        response += "- WebAssembly\n"
        response += "- Concurrency\n\n"
        response += "What Rust-related task can I help you with?"
        
        return response
    
    def _typescript_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """TypeScript-specific response handling"""
        response = f"[TypeScript Module]\n\n"
        
        response += "I can help you with:\n"
        response += "- TypeScript coding and debugging\n"
        response += "- Type definitions\n"
        response += "- Interfaces and types\n"
        response += "- Generics\n"
        response += "- Framework integration (React, Angular)\n"
        response += "- Build configuration\n"
        response += "- Type safety best practices\n\n"
        response += "What TypeScript-related task can I help you with?"
        
        return response
    
    def _react_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """React-specific response handling"""
        response = f"[React Module]\n\n"
        
        response += "I can help you with:\n"
        response += "- React component development\n"
        response += "- Hooks (useState, useEffect, etc.)\n"
        response += "- State management (Redux, Context)\n"
        response += "- Routing (React Router)\n"
        response += "- Performance optimization\n"
        response += "- Testing (Jest, React Testing Library)\n"
        response += "- Best practices and patterns\n\n"
        response += "What React-related task can I help you with?"
        
        return response
    
    def _vue_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Vue-specific response handling"""
        response = f"[Vue Module]\n\n"
        
        response += "I can help you with:\n"
        response += "- Vue component development\n"
        response += "- Composition API\n"
        response += "- Vuex/Pinia state management\n"
        response += "- Vue Router\n"
        response += "- Directives and plugins\n"
        response += "- Testing with Vue\n"
        response += "- Nuxt.js framework\n\n"
        response += "What Vue-related task can I help you with?"
        
        return response
    
    def _angular_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Angular-specific response handling"""
        response = f"[Angular Module]\n\n"
        
        response += "I can help you with:\n"
        response += "- Angular component development\n"
        response += "- Services and dependency injection\n"
        response += "- RxJS and observables\n"
        response += "- Angular Router\n"
        response += "- Forms (Template-driven, Reactive)\n"
        response += "- Angular CLI\n"
        response += "- Testing with Angular\n\n"
        response += "What Angular-related task can I help you with?"
        
        return response
    
    def _fastapi_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """FastAPI-specific response handling"""
        response = f"[FastAPI Module]\n\n"
        
        response += "I can help you with:\n"
        response += "- FastAPI route creation\n"
        response += "- Pydantic models and validation\n"
        response += "- Async/await patterns\n"
        response += "- Database integration (SQLAlchemy, Tortoise ORM)\n"
        response += "- Authentication and authorization\n"
        response += "- WebSocket support\n"
        response += "- API documentation (OpenAPI/Swagger)\n\n"
        response += "What FastAPI-related task can I help you with?"
        
        return response
    
    def _django_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Django-specific response handling"""
        response = f"[Django Module]\n\n"
        
        response += "I can help you with:\n"
        response += "- Django models and ORM\n"
        response += "- Views and URL routing\n"
        response += "- Templates and context\n"
        response += "- Django REST Framework\n"
        response += "- Authentication and permissions\n"
        response += "- Migrations\n"
        response += "- Django admin\n\n"
        response += "What Django-related task can I help you with?"
        
        return response
    
    def _flask_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Flask-specific response handling"""
        response = f"[Flask Module]\n\n"
        
        response += "I can help you with:\n"
        response += "- Flask route creation\n"
        response += "- Templates and Jinja2\n"
        response += "- Flask extensions\n"
        response += "- Database integration (SQLAlchemy)\n"
        response += "- REST API development\n"
        response += "- Authentication\n"
        response += "- Testing Flask apps\n\n"
        response += "What Flask-related task can I help you with?"
        
        return response
    
    def _nodejs_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Node.js-specific response handling"""
        response = f"[Node.js Module]\n\n"
        
        response += "I can help you with:\n"
        response += "- Express.js web development\n"
        response += "- REST API creation\n"
        response += "- Middleware\n"
        response += "- Database integration (MongoDB, PostgreSQL)\n"
        response += "- Authentication (JWT, sessions)\n"
        response += "- WebSocket (Socket.io)\n"
        response += "- Package management (npm, yarn)\n\n"
        response += "What Node.js-related task can I help you with?"
        
        return response
    
    def _spring_module(self, prompt: str, context: Dict[str, Any]) -> str:
        """Spring-specific response handling"""
        response = f"[Spring Module]\n\n"
        
        response += "I can help you with:\n"
        response += "- Spring Boot configuration\n"
        response += "- Dependency injection\n"
        response += "- Spring MVC\n"
        response += "- Spring Data JPA\n"
        response += "- Spring Security\n"
        response += "- REST APIs with Spring\n"
        response += "- Testing Spring applications\n\n"
        response += "What Spring-related task can I help you with?"
        
        return response
    
    def _general_programming_response(self, prompt: str, context: Dict[str, Any]) -> str:
        """General programming response when no specific language/framework is detected"""
        response = f"[Programming AI]\n\n"
        
        response += "I'm here to help with software development and programming.\n\n"
        response += "**Supported Languages:**\n"
        response += "- Python, Java, JavaScript, TypeScript\n"
        response += "- C, C++, C#, Go, Rust\n"
        response += "- Kotlin, Swift, PHP, Ruby\n\n"
        response += **Supported Frameworks:**\n"
        response += "- React, Vue, Angular (Frontend)\n"
        response += "- FastAPI, Django, Flask (Python)\n"
        response += "- Node.js, Express (JavaScript)\n"
        response += "- Spring (Java)\n"
        response += "- .NET, ASP.NET (C#)\n\n"
        response += "**Capabilities:**\n"
        response += "- Debugging and error resolution\n"
        response += "- Code review and optimization\n"
        response += "- Architecture and design patterns\n"
        response += "- Testing strategies\n"
        response += "- Documentation generation\n"
        response += "- Deployment assistance\n"
        response += "- API development\n\n"
        response += "Please specify the programming language, framework, or task you need help with!"
        
        return response
    
    def generate_code(
        self,
        language: str,
        description: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate code based on description"""
        return {
            "language": language,
            "description": description,
            "code": f"# Generated {language} code for: {description}",
            "explanation": "Explanation of the generated code",
            "usage_example": "Example of how to use the code",
        }
    
    def review_code(self, code: str, language: str) -> Dict[str, Any]:
        """Review code and provide suggestions"""
        return {
            "language": language,
            "issues_found": [],
            "suggestions": [],
            "best_practices": [],
            "security_concerns": [],
            "performance_tips": [],
        }
    
    def generate_tests(self, code: str, language: str) -> Dict[str, Any]:
        """Generate unit tests for code"""
        return {
            "language": language,
            "test_framework": "pytest" if language == "python" else "jest",
            "test_cases": [],
            "setup_instructions": "Instructions for running tests",
        }
