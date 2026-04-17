import json
import pytest
from unittest.mock import patch, MagicMock, call
from aspectcoder.config import ModelConfig, Config, ModelsConfig
from aspectcoder.llm.client import LLMResponse
from aspectcoder.pipeline.orchestrator import Orchestrator, HumanNeededError, OrchestratorResult
from aspectcoder.models.plan import Plan, Subtask
from aspectcoder.models.code import GeneratedCode, GenerationResult
from aspectcoder.models.verdict import ReviewVerdict, ReviewerType, Issue, IssueSeverity
from aspectcoder.models.aggregator import AggregatorDecision, AggregatorAction, AttemptSummary
from typing import Callable


def _make_config() -> Config:
    base = ModelConfig(model="claude-haiku-4-5", temperature=0.0, max_tokens=2048)
    return Config(
        models=ModelsConfig(
            planner=ModelConfig(model="claude-opus-4-7"),
            generator={"default": base, "c": base},
            verifier=base,
            reviewers={"functional": base, "security": base, "performance": base},
            aggregator={"normal": base, "failure_report": base},
        )
    )


def _sample_plan(task_id: str = "task-1") -> Plan:
    return Plan(
        task_id=task_id,
        task_description="Add binary_search to utils.c",
        approach="Iterative binary search",
        subtasks=[
            Subtask(id="subtask-1", description="Implement", target_file="src/utils.c", language="c")
        ],
        target_files=["src/utils.c"],
        primary_language="c",
        confidence=0.9,
    )


def _sample_generation() -> GenerationResult:
    return GenerationResult(
        subtasks=[
            GeneratedCode(
                subtask_id="subtask-1",
                language="c",
                file_path="src/utils.c",
                code="int binary_search(...) { return 0; }",
                explanation="Done",
                confidence=0.85,
            )
        ]
    )


def _pass_verdict(reviewer: ReviewerType) -> ReviewVerdict:
    return ReviewVerdict(reviewer=reviewer, pass_=True, confidence=0.9)


def _fail_verdict(reviewer: ReviewerType, approach_wrong: bool = False) -> ReviewVerdict:
    return ReviewVerdict(
        reviewer=reviewer,
        pass_=False,
        confidence=0.7,
        issues=[Issue(severity=IssueSeverity.MAJOR, description="Bug", location="", suggestion="Fix")],
        approach_wrong=approach_wrong,
    )


@pytest.fixture
def config():
    return _make_config()


@pytest.fixture
def orchestrator(config):
    return Orchestrator(config=config)


# ── Happy path ───────────────────────────────────────────────────────────────

def test_orchestrator_happy_path(orchestrator):
    plan = _sample_plan()
    gen = _sample_generation()
    verdicts = [_pass_verdict(r) for r in [ReviewerType.FUNCTIONAL, ReviewerType.SECURITY, ReviewerType.PERFORMANCE]]
    decision = AggregatorDecision(action=AggregatorAction.DONE, summary="All passed.")

    with patch.object(orchestrator.planner, "run", return_value=plan), \
         patch.object(orchestrator.verifier, "run", return_value=MagicMock(pass_=True, needs_human=False)), \
         patch.object(orchestrator.functional_reviewer, "run", return_value=verdicts[0]), \
         patch.object(orchestrator.security_reviewer, "run", return_value=verdicts[1]), \
         patch.object(orchestrator.performance_reviewer, "run", return_value=verdicts[2]), \
         patch.object(orchestrator.aggregator, "run", return_value=decision):
        # generator is created per-run based on language; patch at module level
        with patch("aspectcoder.pipeline.orchestrator.GeneratorAgent") as MockGen:
            mock_gen_instance = MagicMock()
            mock_gen_instance.run.return_value = gen
            mock_gen_instance.last_needs_human = False
            MockGen.return_value = mock_gen_instance

            result = orchestrator.run("Add binary_search to utils.c")

    assert isinstance(result, OrchestratorResult)
    assert result.plan == plan
    assert result.generated_code == gen
    assert result.decision.action == AggregatorAction.DONE


# ── Planning phase retry ──────────────────────────────────────────────────────

def test_orchestrator_retries_planning_on_verifier_fail(orchestrator):
    plan = _sample_plan()
    fail_verdict = MagicMock(pass_=False, needs_human=False, issues=["Bad plan"])
    pass_verdict_plan = MagicMock(pass_=True, needs_human=False)
    gen = _sample_generation()
    decision = AggregatorDecision(action=AggregatorAction.DONE, summary="Done.")
    all_verdicts = [_pass_verdict(r) for r in [ReviewerType.FUNCTIONAL, ReviewerType.SECURITY, ReviewerType.PERFORMANCE]]

    with patch.object(orchestrator.planner, "run", return_value=plan) as mock_planner, \
         patch.object(orchestrator.verifier, "run", side_effect=[fail_verdict, pass_verdict_plan]), \
         patch.object(orchestrator.functional_reviewer, "run", return_value=all_verdicts[0]), \
         patch.object(orchestrator.security_reviewer, "run", return_value=all_verdicts[1]), \
         patch.object(orchestrator.performance_reviewer, "run", return_value=all_verdicts[2]), \
         patch.object(orchestrator.aggregator, "run", return_value=decision):
        with patch("aspectcoder.pipeline.orchestrator.GeneratorAgent") as MockGen:
            mock_gen_instance = MagicMock()
            mock_gen_instance.run.return_value = gen
            mock_gen_instance.last_needs_human = False
            MockGen.return_value = mock_gen_instance

            result = orchestrator.run("Add binary_search")

    assert mock_planner.call_count == 2  # retried once after verifier fail
    assert result.decision.action == AggregatorAction.DONE


# ── Human escalation ──────────────────────────────────────────────────────────

def test_orchestrator_raises_human_needed_when_planner_sets_needs_human(orchestrator):
    plan = _sample_plan()
    orchestrator.planner.last_needs_human = True

    with patch.object(orchestrator.planner, "run", return_value=plan) as mock_planner:
        mock_planner.side_effect = lambda *a, **kw: setattr(orchestrator.planner, "last_needs_human", True) or plan
        with pytest.raises(HumanNeededError, match="planner"):
            orchestrator.run("ambiguous task")


def test_orchestrator_raises_human_needed_when_verifier_exhausted(orchestrator):
    plan = _sample_plan()
    fail_verdict = MagicMock(pass_=False, needs_human=False, issues=["Bad"])

    with patch.object(orchestrator.planner, "run", return_value=plan), \
         patch.object(orchestrator.verifier, "run", return_value=fail_verdict):
        with pytest.raises(HumanNeededError, match="verifier"):
            orchestrator.run("hard task")


# ── Functional early exit ─────────────────────────────────────────────────────

def test_orchestrator_skips_security_and_perf_when_functional_fails(orchestrator):
    plan = _sample_plan()
    gen = _sample_generation()
    func_fail = _fail_verdict(ReviewerType.FUNCTIONAL)
    regen_decision = AggregatorDecision(action=AggregatorAction.REGEN, summary="Functional failed.")
    pass_func = _pass_verdict(ReviewerType.FUNCTIONAL)
    pass_sec = _pass_verdict(ReviewerType.SECURITY)
    pass_perf = _pass_verdict(ReviewerType.PERFORMANCE)
    done_decision = AggregatorDecision(action=AggregatorAction.DONE, summary="Done.")

    mock_functional = MagicMock(side_effect=[func_fail, pass_func])
    mock_security = MagicMock(side_effect=[pass_sec])
    mock_performance = MagicMock(side_effect=[pass_perf])
    mock_aggregator = MagicMock(side_effect=[regen_decision, done_decision])

    with patch.object(orchestrator.planner, "run", return_value=plan), \
         patch.object(orchestrator.verifier, "run", return_value=MagicMock(pass_=True, needs_human=False)), \
         patch.object(orchestrator.functional_reviewer, "run", mock_functional), \
         patch.object(orchestrator.security_reviewer, "run", mock_security), \
         patch.object(orchestrator.performance_reviewer, "run", mock_performance), \
         patch.object(orchestrator.aggregator, "run", mock_aggregator):
        with patch("aspectcoder.pipeline.orchestrator.GeneratorAgent") as MockGen:
            mock_gen_instance = MagicMock()
            mock_gen_instance.run.return_value = gen
            mock_gen_instance.last_needs_human = False
            MockGen.return_value = mock_gen_instance

            result = orchestrator.run("Add binary_search")

            # Security and perf were skipped on the first (functional-failed) attempt
            assert mock_security.call_count == 1
            assert mock_performance.call_count == 1
            assert result.decision.action == AggregatorAction.DONE


# ── Low generator confidence → human ─────────────────────────────────────────

def _minor_fail_verdict(reviewer: ReviewerType) -> ReviewVerdict:
    """Failing verdict with only minor issues and approach_wrong=False."""
    return ReviewVerdict(
        reviewer=reviewer,
        pass_=False,
        confidence=0.8,
        issues=[Issue(severity=IssueSeverity.MINOR, description="Small perf nit", location="", suggestion="Use try/except")],
        approach_wrong=False,
    )


def _critical_fail_verdict(reviewer: ReviewerType) -> ReviewVerdict:
    return ReviewVerdict(
        reviewer=reviewer,
        pass_=False,
        confidence=0.6,
        issues=[Issue(severity=IssueSeverity.CRITICAL, description="SQL injection", location="", suggestion="Sanitize")],
        approach_wrong=False,
    )


def test_orchestrator_accepts_best_effort_when_regen_budget_exhausted_with_minor_issues(orchestrator):
    """When regen budget runs out and remaining issues are non-critical, return the last attempt."""
    plan = _sample_plan()
    gen = _sample_generation()
    # Functional and security pass; performance always fails with minor issues only
    func_pass = _pass_verdict(ReviewerType.FUNCTIONAL)
    sec_pass = _pass_verdict(ReviewerType.SECURITY)
    perf_fail = _minor_fail_verdict(ReviewerType.PERFORMANCE)
    regen_decision = AggregatorDecision(action=AggregatorAction.REGEN, summary="Minor perf issues.")

    with patch.object(orchestrator.planner, "run", return_value=plan), \
         patch.object(orchestrator.verifier, "run", return_value=MagicMock(pass_=True, needs_human=False)), \
         patch.object(orchestrator.functional_reviewer, "run", return_value=func_pass), \
         patch.object(orchestrator.security_reviewer, "run", return_value=sec_pass), \
         patch.object(orchestrator.performance_reviewer, "run", return_value=perf_fail), \
         patch.object(orchestrator.aggregator, "run", return_value=regen_decision):
        with patch("aspectcoder.pipeline.orchestrator.GeneratorAgent") as MockGen:
            mock_gen_instance = MagicMock()
            mock_gen_instance.run.return_value = gen
            mock_gen_instance.last_needs_human = False
            MockGen.return_value = mock_gen_instance

            result = orchestrator.run("Add binary_search")

    assert isinstance(result, OrchestratorResult)
    assert result.generated_code == gen


def test_orchestrator_raises_human_needed_when_regen_budget_exhausted_with_critical_issues(orchestrator):
    """Critical issues should still escalate to human even after budget exhaustion."""
    plan = _sample_plan()
    gen = _sample_generation()
    func_pass = _pass_verdict(ReviewerType.FUNCTIONAL)
    sec_fail = _critical_fail_verdict(ReviewerType.SECURITY)
    perf_pass = _pass_verdict(ReviewerType.PERFORMANCE)
    regen_decision = AggregatorDecision(action=AggregatorAction.REGEN, summary="Critical security issue.")

    with patch.object(orchestrator.planner, "run", return_value=plan), \
         patch.object(orchestrator.verifier, "run", return_value=MagicMock(pass_=True, needs_human=False)), \
         patch.object(orchestrator.functional_reviewer, "run", return_value=func_pass), \
         patch.object(orchestrator.security_reviewer, "run", return_value=sec_fail), \
         patch.object(orchestrator.performance_reviewer, "run", return_value=perf_pass), \
         patch.object(orchestrator.aggregator, "run", return_value=regen_decision):
        with patch("aspectcoder.pipeline.orchestrator.GeneratorAgent") as MockGen:
            mock_gen_instance = MagicMock()
            mock_gen_instance.run.return_value = gen
            mock_gen_instance.last_needs_human = False
            MockGen.return_value = mock_gen_instance

            with pytest.raises(HumanNeededError, match="regen budget exhausted"):
                orchestrator.run("Add binary_search")


def test_orchestrator_raises_human_needed_when_generator_confidence_low(orchestrator):
    plan = _sample_plan()
    low_conf_gen = GenerationResult(
        subtasks=[
            GeneratedCode(
                subtask_id="subtask-1",
                language="c",
                file_path="src/utils.c",
                code="",
                explanation="",
                confidence=0.3,
            )
        ]
    )

    with patch.object(orchestrator.planner, "run", return_value=plan), \
         patch.object(orchestrator.verifier, "run", return_value=MagicMock(pass_=True, needs_human=False)):
        with patch("aspectcoder.pipeline.orchestrator.GeneratorAgent") as MockGen:
            mock_gen_instance = MagicMock()
            mock_gen_instance.run.return_value = low_conf_gen
            mock_gen_instance.last_needs_human = False
            MockGen.return_value = mock_gen_instance

            with pytest.raises(HumanNeededError, match="confidence"):
                orchestrator.run("hard task")


# ── Progress reporting ────────────────────────────────────────────────────────

def test_orchestrator_emits_progress_events_on_happy_path(config):
    plan = _sample_plan()
    gen = _sample_generation()
    verdicts = [_pass_verdict(r) for r in [ReviewerType.FUNCTIONAL, ReviewerType.SECURITY, ReviewerType.PERFORMANCE]]
    decision = AggregatorDecision(action=AggregatorAction.DONE, summary="All passed.")

    events: list[str] = []
    orchestrator = Orchestrator(config=config, progress=events.append)

    with patch.object(orchestrator.planner, "run", return_value=plan), \
         patch.object(orchestrator.verifier, "run", return_value=MagicMock(pass_=True, needs_human=False, issues=[])), \
         patch.object(orchestrator.functional_reviewer, "run", return_value=verdicts[0]), \
         patch.object(orchestrator.security_reviewer, "run", return_value=verdicts[1]), \
         patch.object(orchestrator.performance_reviewer, "run", return_value=verdicts[2]), \
         patch.object(orchestrator.aggregator, "run", return_value=decision):
        with patch("aspectcoder.pipeline.orchestrator.GeneratorAgent") as MockGen:
            mock_gen_instance = MagicMock()
            mock_gen_instance.run.return_value = gen
            mock_gen_instance.last_needs_human = False
            MockGen.return_value = mock_gen_instance

            orchestrator.run("Add binary_search")

    joined = "\n".join(events)
    assert "Planning" in joined
    assert "Generating" in joined
    assert "functional" in joined.lower()
    assert "security" in joined.lower()
    assert "performance" in joined.lower()


# ── Reviewer selection ────────────────────────────────────────────────────────

def test_review_phase_functional_only(config):
    orch = Orchestrator(config=config, enabled_reviewers={"functional"})
    plan = _sample_plan()
    gen = _sample_generation()

    with patch.object(orch.functional_reviewer, "run", return_value=_pass_verdict(ReviewerType.FUNCTIONAL)) as m_func, \
         patch.object(orch.security_reviewer, "run") as m_sec, \
         patch.object(orch.performance_reviewer, "run") as m_perf:
        verdicts = orch._review_phase(plan, gen)

    assert len(verdicts) == 1
    assert verdicts[0].reviewer == ReviewerType.FUNCTIONAL
    m_sec.assert_not_called()
    m_perf.assert_not_called()


def test_review_phase_security_and_performance_only(config):
    orch = Orchestrator(config=config, enabled_reviewers={"security", "performance"})
    plan = _sample_plan()
    gen = _sample_generation()

    with patch.object(orch.functional_reviewer, "run") as m_func, \
         patch.object(orch.security_reviewer, "run", return_value=_pass_verdict(ReviewerType.SECURITY)), \
         patch.object(orch.performance_reviewer, "run", return_value=_pass_verdict(ReviewerType.PERFORMANCE)):
        verdicts = orch._review_phase(plan, gen)

    m_func.assert_not_called()
    assert {v.reviewer for v in verdicts} == {ReviewerType.SECURITY, ReviewerType.PERFORMANCE}


def test_review_phase_no_reviewers_enabled(config):
    orch = Orchestrator(config=config, enabled_reviewers=set())
    plan = _sample_plan()
    gen = _sample_generation()

    with patch.object(orch.functional_reviewer, "run") as m_func, \
         patch.object(orch.security_reviewer, "run") as m_sec, \
         patch.object(orch.performance_reviewer, "run") as m_perf:
        verdicts = orch._review_phase(plan, gen)

    assert verdicts == []
    m_func.assert_not_called()
    m_sec.assert_not_called()
    m_perf.assert_not_called()


def test_review_phase_functional_disabled_both_parallel_run(config):
    """When functional is disabled, security and performance always both run."""
    orch = Orchestrator(config=config, enabled_reviewers={"security", "performance"})
    plan = _sample_plan()
    gen = _sample_generation()

    with patch.object(orch.functional_reviewer, "run") as m_func, \
         patch.object(orch.security_reviewer, "run", return_value=_fail_verdict(ReviewerType.SECURITY)), \
         patch.object(orch.performance_reviewer, "run", return_value=_pass_verdict(ReviewerType.PERFORMANCE)):
        verdicts = orch._review_phase(plan, gen)

    m_func.assert_not_called()
    assert {v.reviewer for v in verdicts} == {ReviewerType.SECURITY, ReviewerType.PERFORMANCE}


def test_review_phase_functional_fail_early_exits_when_enabled(config):
    """Functional early-exit still applies when functional is in the enabled set."""
    orch = Orchestrator(config=config, enabled_reviewers=None)
    plan = _sample_plan()
    gen = _sample_generation()

    with patch.object(orch.functional_reviewer, "run", return_value=_fail_verdict(ReviewerType.FUNCTIONAL)), \
         patch.object(orch.security_reviewer, "run") as m_sec, \
         patch.object(orch.performance_reviewer, "run") as m_perf:
        verdicts = orch._review_phase(plan, gen)

    assert len(verdicts) == 1
    assert not verdicts[0].pass_
    m_sec.assert_not_called()
    m_perf.assert_not_called()
