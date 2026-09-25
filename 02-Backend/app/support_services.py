import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from app.repositories.database.client import get_db

logger = logging.getLogger(__name__)


@dataclass
class HelpArticle:
    id: str
    slug: str
    title: str
    content: str
    category: str
    tags: List[str] = field(default_factory=list)
    views: int = 0
    helpful_count: int = 0
    not_helpful_count: int = 0
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


@dataclass
class Tutorial:
    id: str
    title: str
    description: str
    steps: List[Dict[str, Any]]
    difficulty: str = "beginner"
    estimated_time: int = 5
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


@dataclass
class TutorialProgress:
    id: str
    user_id: str
    tutorial_id: str
    current_step: int = 0
    completed: bool = False
    started_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    completed_at: Optional[float] = None


@dataclass
class Feedback:
    id: str
    user_id: str
    type: str
    rating: Optional[int] = None
    comment: Optional[str] = None
    page_url: Optional[str] = None
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


@dataclass
class NpsSurvey:
    id: str
    user_id: str
    score: int
    comment: Optional[str] = None
    survey_type: str = "periodic"
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


@dataclass
class FeatureRequest:
    id: str
    user_id: str
    title: str
    description: str
    votes: int = 0
    status: str = "open"
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


@dataclass
class BugReport:
    id: str
    user_id: str
    title: str
    description: str
    severity: str = "medium"
    status: str = "open"
    steps_to_reproduce: Optional[str] = None
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


@dataclass
class CustomerHealth:
    id: str
    user_id: str
    score: float = 0.0
    factors: Dict[str, Any] = field(default_factory=dict)
    last_calculated: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


@dataclass
class SupportAnalytic:
    id: str
    metric_name: str
    metric_value: float
    period: str
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


@dataclass
class StatusIncident:
    id: str
    title: str
    description: str
    status: str = "investigating"
    affected_services: List[str] = field(default_factory=list)
    started_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    resolved_at: Optional[float] = None
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


@dataclass
class OnboardingProgress:
    id: str
    user_id: str
    current_step: int = 0
    completed_steps: List[str] = field(default_factory=list)
    completed: bool = False
    started_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    completed_at: Optional[float] = None


@dataclass
class LiveChatSession:
    id: str
    user_id: str
    agent_id: Optional[str] = None
    status: str = "open"
    started_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    ended_at: Optional[float] = None


@dataclass
class ChatMessage:
    id: str
    session_id: str
    sender_id: str
    sender_type: str
    message: str
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


class CxService:
    def __init__(self):
        self.articles: Dict[str, HelpArticle] = {}
        self.tutorials: Dict[str, Tutorial] = {}
        self.progress: Dict[str, TutorialProgress] = {}
        self.feedbacks: Dict[str, Feedback] = {}
        self.nps: Dict[str, NpsSurvey] = {}
        self.feature_requests: Dict[str, FeatureRequest] = {}
        self.bug_reports: Dict[str, BugReport] = {}
        self.health_scores: Dict[str, CustomerHealth] = {}
        self.analytics: Dict[str, SupportAnalytic] = {}
        self.incidents: Dict[str, StatusIncident] = {}
        self.onboarding: Dict[str, OnboardingProgress] = {}
        self.chat_sessions: Dict[str, LiveChatSession] = {}
        self.chat_messages: Dict[str, ChatMessage] = {}

    def _now(self) -> float:
        return datetime.now(timezone.utc).timestamp()

    def _iso(self, ts: Optional[float]) -> Optional[str]:
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else None

    # Help Center
    def create_article(self, slug: str, title: str, content: str, category: str, tags: List[str] = None) -> HelpArticle:
        article_id = str(uuid.uuid4())
        article = HelpArticle(id=article_id, slug=slug, title=title, content=content, category=category, tags=tags or [])
        self.articles[article_id] = article
        self._persist_article(article)
        return article

    def _persist_article(self, article: HelpArticle) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO help_articles (id, slug, title, content, category, tags, views, helpful_count, not_helpful_count, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (article.id, article.slug, article.title, article.content, article.category, json.dumps(article.tags),
                 article.views, article.helpful_count, article.not_helpful_count, self._iso(article.created_at), self._iso(article.updated_at)),
            )
            conn.commit()

    def get_article(self, article_id: str) -> Optional[HelpArticle]:
        return self.articles.get(article_id)

    def list_articles(self, category: str = None) -> List[HelpArticle]:
        articles = list(self.articles.values())
        if category:
            articles = [a for a in articles if a.category == category]
        return sorted(articles, key=lambda a: a.updated_at, reverse=True)

    def search_articles(self, query: str) -> List[HelpArticle]:
        q = query.lower()
        return [a for a in self.articles.values() if q in a.title.lower() or q in a.content.lower() or any(q in t.lower() for t in a.tags)]

    def increment_article_views(self, article_id: str) -> None:
        article = self.articles.get(article_id)
        if article:
            article.views += 1
            article.updated_at = self._now()
            with get_db() as conn:
                conn.execute("UPDATE help_articles SET views = views + 1, updated_at = ? WHERE id = ?", (self._iso(article.updated_at), article_id))
                conn.commit()

    def mark_article_helpful(self, article_id: str, helpful: bool) -> None:
        article = self.articles.get(article_id)
        if article:
            if helpful:
                article.helpful_count += 1
            else:
                article.not_helpful_count += 1
            article.updated_at = self._now()
            with get_db() as conn:
                conn.execute("UPDATE help_articles SET helpful_count = ?, not_helpful_count = ?, updated_at = ? WHERE id = ?",
                             (article.helpful_count, article.not_helpful_count, self._iso(article.updated_at), article_id))
                conn.commit()

    # Tutorials
    def create_tutorial(self, title: str, description: str, steps: List[Dict[str, Any]], difficulty: str = "beginner", estimated_time: int = 5) -> Tutorial:
        tutorial_id = str(uuid.uuid4())
        tutorial = Tutorial(id=tutorial_id, title=title, description=description, steps=steps, difficulty=difficulty, estimated_time=estimated_time)
        self.tutorials[tutorial_id] = tutorial
        self._persist_tutorial(tutorial)
        return tutorial

    def _persist_tutorial(self, tutorial: Tutorial) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO tutorials (id, title, description, steps, difficulty, estimated_time, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (tutorial.id, tutorial.title, tutorial.description, json.dumps(tutorial.steps), tutorial.difficulty, tutorial.estimated_time,
                 self._iso(tutorial.created_at), self._iso(tutorial.updated_at)),
            )
            conn.commit()

    def get_tutorial(self, tutorial_id: str) -> Optional[Tutorial]:
        return self.tutorials.get(tutorial_id)

    def list_tutorials(self, difficulty: str = None) -> List[Tutorial]:
        tutorials = list(self.tutorials.values())
        if difficulty:
            tutorials = [t for t in tutorials if t.difficulty == difficulty]
        return sorted(tutorials, key=lambda t: t.created_at, reverse=True)

    def start_tutorial(self, user_id: str, tutorial_id: str) -> TutorialProgress:
        progress_id = str(uuid.uuid4())
        progress = TutorialProgress(id=progress_id, user_id=user_id, tutorial_id=tutorial_id)
        self.progress[progress_id] = progress
        self._persist_progress(progress)
        return progress

    def update_tutorial_progress(self, user_id: str, tutorial_id: str, current_step: int) -> Optional[TutorialProgress]:
        progress = next((p for p in self.progress.values() if p.user_id == user_id and p.tutorial_id == tutorial_id), None)
        if not progress:
            return None
        progress.current_step = current_step
        tutorial = self.tutorials.get(tutorial_id)
        if tutorial and current_step >= len(tutorial.steps):
            progress.completed = True
            progress.completed_at = self._now()
        self._persist_progress(progress)
        return progress

    def _persist_progress(self, progress: TutorialProgress) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO tutorial_progress (id, user_id, tutorial_id, current_step, completed, started_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (progress.id, progress.user_id, progress.tutorial_id, progress.current_step, int(progress.completed),
                 self._iso(progress.started_at), self._iso(progress.completed_at)),
            )
            conn.commit()

    def get_user_tutorial_progress(self, user_id: str) -> List[TutorialProgress]:
        return [p for p in self.progress.values() if p.user_id == user_id]

    # Feedback
    def submit_feedback(self, user_id: str, feedback_type: str, rating: int = None, comment: str = None, page_url: str = None) -> Feedback:
        feedback_id = str(uuid.uuid4())
        feedback = Feedback(id=feedback_id, user_id=user_id, type=feedback_type, rating=rating, comment=comment, page_url=page_url)
        self.feedbacks[feedback_id] = feedback
        self._persist_feedback(feedback)
        return feedback

    def _persist_feedback(self, feedback: Feedback) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO feedback (id, user_id, type, rating, comment, page_url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (feedback.id, feedback.user_id, feedback.type, feedback.rating, feedback.comment, feedback.page_url, self._iso(feedback.created_at)),
            )
            conn.commit()

    def list_feedback(self, feedback_type: str = None) -> List[Feedback]:
        feedbacks = list(self.feedbacks.values())
        if feedback_type:
            feedbacks = [f for f in feedbacks if f.type == feedback_type]
        return sorted(feedbacks, key=lambda f: f.created_at, reverse=True)

    # NPS
    def submit_nps(self, user_id: str, score: int, comment: str = None, survey_type: str = "periodic") -> NpsSurvey:
        survey_id = str(uuid.uuid4())
        survey = NpsSurvey(id=survey_id, user_id=user_id, score=score, comment=comment, survey_type=survey_type)
        self.nps[survey_id] = survey
        self._persist_nps(survey)
        return survey

    def _persist_nps(self, survey: NpsSurvey) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO nps_surveys (id, user_id, score, comment, survey_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (survey.id, survey.user_id, survey.score, survey.comment, survey.survey_type, self._iso(survey.created_at)),
            )
            conn.commit()

    def get_nps_stats(self) -> Dict[str, Any]:
        surveys = list(self.nps.values())
        if not surveys:
            return {"average": 0, "total": 0, "promoters": 0, "passives": 0, "detractors": 0}
        total = len(surveys)
        avg = sum(s.score for s in surveys) / total
        promoters = sum(1 for s in surveys if s.score >= 9)
        passives = sum(1 for s in surveys if 7 <= s.score <= 8)
        detractors = sum(1 for s in surveys if s.score <= 6)
        return {"average": round(avg, 1), "total": total, "promoters": promoters, "passives": passives, "detractors": detractors}

    # Feature Requests
    def create_feature_request(self, user_id: str, title: str, description: str) -> FeatureRequest:
        req_id = str(uuid.uuid4())
        req = FeatureRequest(id=req_id, user_id=user_id, title=title, description=description)
        self.feature_requests[req_id] = req
        self._persist_feature_request(req)
        return req

    def _persist_feature_request(self, req: FeatureRequest) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO feature_requests (id, user_id, title, description, votes, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (req.id, req.user_id, req.title, req.description, req.votes, req.status, self._iso(req.created_at)),
            )
            conn.commit()

    def vote_feature_request(self, req_id: str) -> Optional[FeatureRequest]:
        req = self.feature_requests.get(req_id)
        if req:
            req.votes += 1
            with get_db() as conn:
                conn.execute("UPDATE feature_requests SET votes = ? WHERE id = ?", (req.votes, req_id))
                conn.commit()
        return req

    def list_feature_requests(self, status: str = None) -> List[FeatureRequest]:
        reqs = list(self.feature_requests.values())
        if status:
            reqs = [r for r in reqs if r.status == status]
        return sorted(reqs, key=lambda r: r.votes, reverse=True)

    # Bug Reports
    def create_bug_report(self, user_id: str, title: str, description: str, severity: str = "medium", steps_to_reproduce: str = None) -> BugReport:
        bug_id = str(uuid.uuid4())
        bug = BugReport(id=bug_id, user_id=user_id, title=title, description=description, severity=severity, steps_to_reproduce=steps_to_reproduce)
        self.bug_reports[bug_id] = bug
        self._persist_bug_report(bug)
        return bug

    def _persist_bug_report(self, bug: BugReport) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO bug_reports (id, user_id, title, description, severity, status, steps_to_reproduce, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (bug.id, bug.user_id, bug.title, bug.description, bug.severity, bug.status, bug.steps_to_reproduce, self._iso(bug.created_at)),
            )
            conn.commit()

    def update_bug_status(self, bug_id: str, status: str) -> Optional[BugReport]:
        bug = self.bug_reports.get(bug_id)
        if bug:
            bug.status = status
            with get_db() as conn:
                conn.execute("UPDATE bug_reports SET status = ? WHERE id = ?", (status, bug_id))
                conn.commit()
        return bug

    def list_bug_reports(self, status: str = None) -> List[BugReport]:
        bugs = list(self.bug_reports.values())
        if status:
            bugs = [b for b in bugs if b.status == status]
        return sorted(bugs, key=lambda b: b.created_at, reverse=True)

    # Customer Health
    def calculate_health_score(self, user_id: str) -> CustomerHealth:
        health = self.health_scores.get(user_id)
        if not health:
            health_id = str(uuid.uuid4())
            health = CustomerHealth(id=health_id, user_id=user_id)
            self.health_scores[user_id] = health
        factors = {
            "login_frequency": 0.3,
            "feature_usage": 0.3,
            "support_tickets": 0.2,
            "nps_score": 0.2,
        }
        score = sum(factors.values()) * 100
        health.score = min(100, max(0, score))
        health.factors = factors
        health.last_calculated = self._now()
        self._persist_health(health)
        return health

    def _persist_health(self, health: CustomerHealth) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO customer_health (id, user_id, score, factors, last_calculated, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (health.id, health.user_id, health.score, json.dumps(health.factors), self._iso(health.last_calculated), self._iso(health.created_at)),
            )
            conn.commit()

    def get_customer_health(self, user_id: str) -> Optional[CustomerHealth]:
        return self.health_scores.get(user_id)

    # Support Analytics
    def record_analytic(self, metric_name: str, metric_value: float, period: str) -> SupportAnalytic:
        analytic_id = str(uuid.uuid4())
        analytic = SupportAnalytic(id=analytic_id, metric_name=metric_name, metric_value=metric_value, period=period)
        self.analytics[analytic_id] = analytic
        self._persist_analytic(analytic)
        return analytic

    def _persist_analytic(self, analytic: SupportAnalytic) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO support_analytics (id, metric_name, metric_value, period, created_at) VALUES (?, ?, ?, ?, ?)",
                (analytic.id, analytic.metric_name, analytic.metric_value, analytic.period, self._iso(analytic.created_at)),
            )
            conn.commit()

    def get_analytics(self, metric_name: str = None, period: str = None) -> List[SupportAnalytic]:
        analytics = list(self.analytics.values())
        if metric_name:
            analytics = [a for a in analytics if a.metric_name == metric_name]
        if period:
            analytics = [a for a in analytics if a.period == period]
        return sorted(analytics, key=lambda a: a.created_at, reverse=True)

    # Status Page
    def create_incident(self, title: str, description: str, affected_services: List[str] = None) -> StatusIncident:
        incident_id = str(uuid.uuid4())
        incident = StatusIncident(id=incident_id, title=title, description=description, affected_services=affected_services or [])
        self.incidents[incident_id] = incident
        self._persist_incident(incident)
        return incident

    def _persist_incident(self, incident: StatusIncident) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO status_page_incidents (id, title, description, status, affected_services, started_at, resolved_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (incident.id, incident.title, incident.description, incident.status, json.dumps(incident.affected_services),
                 self._iso(incident.started_at), self._iso(incident.resolved_at), self._iso(incident.created_at)),
            )
            conn.commit()

    def update_incident_status(self, incident_id: str, status: str) -> Optional[StatusIncident]:
        incident = self.incidents.get(incident_id)
        if incident:
            incident.status = status
            if status == "resolved":
                incident.resolved_at = self._now()
            with get_db() as conn:
                conn.execute("UPDATE status_page_incidents SET status = ?, resolved_at = ? WHERE id = ?",
                             (status, self._iso(incident.resolved_at), incident_id))
                conn.commit()
        return incident

    def list_incidents(self, status: str = None) -> List[StatusIncident]:
        incidents = list(self.incidents.values())
        if status:
            incidents = [i for i in incidents if i.status == status]
        return sorted(incidents, key=lambda i: i.started_at, reverse=True)

    def get_status_summary(self) -> Dict[str, Any]:
        incidents = list(self.incidents.values())
        active = [i for i in incidents if i.status != "resolved"]
        return {
            "status": "operational" if not active else "degraded",
            "active_incidents": len(active),
            "total_incidents": len(incidents),
            "services": ["API", "Web App", "Chat", "Database", "AI Models"],
        }

    # Onboarding
    def start_onboarding(self, user_id: str) -> OnboardingProgress:
        progress_id = str(uuid.uuid4())
        progress = OnboardingProgress(id=progress_id, user_id=user_id)
        self.onboarding[user_id] = progress
        self._persist_onboarding(progress)
        return progress

    def _persist_onboarding(self, progress: OnboardingProgress) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO onboarding_progress (id, user_id, current_step, completed_steps, completed, started_at, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (progress.id, progress.user_id, progress.current_step, json.dumps(progress.completed_steps), int(progress.completed),
                 self._iso(progress.started_at), self._iso(progress.completed_at)),
            )
            conn.commit()

    def complete_onboarding_step(self, user_id: str, step: str) -> Optional[OnboardingProgress]:
        progress = self.onboarding.get(user_id)
        if not progress:
            return None
        if step not in progress.completed_steps:
            progress.completed_steps.append(step)
        progress.current_step += 1
        self._persist_onboarding(progress)
        return progress

    def complete_onboarding(self, user_id: str) -> Optional[OnboardingProgress]:
        progress = self.onboarding.get(user_id)
        if progress:
            progress.completed = True
            progress.completed_at = self._now()
            self._persist_onboarding(progress)
        return progress

    def get_onboarding_progress(self, user_id: str) -> Optional[OnboardingProgress]:
        return self.onboarding.get(user_id)

    # Live Chat
    def create_chat_session(self, user_id: str, agent_id: str = None) -> LiveChatSession:
        session_id = str(uuid.uuid4())
        session = LiveChatSession(id=session_id, user_id=user_id, agent_id=agent_id)
        self.chat_sessions[session_id] = session
        self._persist_chat_session(session)
        return session

    def _persist_chat_session(self, session: LiveChatSession) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO live_chat_sessions (id, user_id, agent_id, status, started_at, ended_at) VALUES (?, ?, ?, ?, ?, ?)",
                (session.id, session.user_id, session.agent_id, session.status, self._iso(session.started_at), self._iso(session.ended_at)),
            )
            conn.commit()

    def end_chat_session(self, session_id: str) -> Optional[LiveChatSession]:
        session = self.chat_sessions.get(session_id)
        if session:
            session.status = "closed"
            session.ended_at = self._now()
            with get_db() as conn:
                conn.execute("UPDATE live_chat_sessions SET status = ?, ended_at = ? WHERE id = ?",
                             ("closed", self._iso(session.ended_at), session_id))
                conn.commit()
        return session

    def get_chat_session(self, session_id: str) -> Optional[LiveChatSession]:
        return self.chat_sessions.get(session_id)

    def list_user_sessions(self, user_id: str) -> List[LiveChatSession]:
        return [s for s in self.chat_sessions.values() if s.user_id == user_id]

    def send_chat_message(self, session_id: str, sender_id: str, sender_type: str, message: str) -> ChatMessage:
        msg_id = str(uuid.uuid4())
        msg = ChatMessage(id=msg_id, session_id=session_id, sender_id=sender_id, sender_type=sender_type, message=message)
        self.chat_messages[msg_id] = msg
        self._persist_chat_message(msg)
        return msg

    def _persist_chat_message(self, msg: ChatMessage) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO chat_messages (id, session_id, sender_id, sender_type, message, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (msg.id, msg.session_id, msg.sender_id, msg.sender_type, msg.message, self._iso(msg.created_at)),
            )
            conn.commit()

    def get_chat_messages(self, session_id: str) -> List[ChatMessage]:
        return sorted([m for m in self.chat_messages.values() if m.session_id == session_id], key=lambda m: m.created_at)


cx_service = CxService()
