from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable

from aspectcoder.config import Config
from aspectcoder.agents.planner import PlannerAgent
from aspectcoder.agents.plan_verifier import PlanVerifierAgent
from aspectcoder.agents.generator import GeneratorAgent
from aspectcoder.agents.reviewers.functional import FunctionalReviewerAgent
from aspectcoder.agents.reviewers.security import SecurityReviewerAgent, SecurityLevel
from aspectcoder.agents.reviewers.performance import PerformanceReviewerAgent
from aspectcoder.agents.aggregator import AggregatorAgent
from aspectcoder.agents.inputs import PlannerInput, GeneratorInput, ReviewInput, AggregatorInput
from aspectcoder.models.plan import Plan
from aspectcoder.models.code import GenerationResult
from aspectcoder.models.verdict import ReviewVerdict, IssueSeverity
from aspectcoder.models.aggregator import AggregatorDecision, AggregatorAction, AttemptSummary

MAX_VERIFIER_RETRIES = 3   # plan revisions before human escalation
MAX_REGEN_RETRIES = 3      # generation attempts before exhaustion

VALID_REVIEWERS: frozenset[str] = frozenset({"functional", "security", "performance"})


class HumanNeededError(Exception):
    pass


@dataclass
class OrchestratorResult:
    plan: Plan
    generated_code: GenerationResult
    decision: AggregatorDecision
    all_attempts: list[AttemptSummary] = field(default_factory=list)


class Orchestrator:
    def __init__(
        self,
        config: Config,
        progress: Callable[[str], None] | None = None,
        enabled_reviewers: set[str] | None = None,
        security_level: SecurityLevel = SecurityLevel.STANDARD,
    ):
        self.config = config
        self._progress = progress or (lambda _: None)
        self._enabled = enabled_reviewers  # None = all three
        self.planner = PlannerAgent(config=config.models.planner)
        self.verifier = PlanVerifierAgent(config=config.models.verifier)
        self.functional_reviewer = FunctionalReviewerAgent(config=config.models.reviewers["functional"])
        self.security_reviewer = SecurityReviewerAgent(config=config.models.reviewers["security"], level=security_level)
        self.performance_reviewer = PerformanceReviewerAgent(config=config.models.reviewers["performance"])
        self.aggregator = AggregatorAgent(config=config)

    def _emit(self, msg: str) -> None:
        self._progress(msg)

    def run(self, task_description: str, codebase_context: str = "") -> OrchestratorResult:
        plan = self._planning_phase(task_description, codebase_context)
        return self._generation_review_loop(plan, codebase_context)

    # ── Planning phase ────────────────────────────────────────────────────────

    def _planning_phase(self, task_description: str, codebase_context: str) -> Plan:
        previous_issues: list[str] = []

        for attempt in range(MAX_VERIFIER_RETRIES):
            self._emit(f"Planning{'  (revision)' if attempt > 0 else ''}...")
            plan = self.planner.run(
                PlannerInput(
                    task_description=task_description,
                    codebase_context=codebase_context,
                    previous_issues=previous_issues,
                )
            )
            if self.planner.last_needs_human:
                raise HumanNeededError("planner: task is too ambiguous to plan without human input")

            self._emit(f"Verifying plan ({len(plan.subtasks)} subtask(s), language: {plan.primary_language})...")
            verdict = self.verifier.run(plan)
            if self.verifier.last_needs_human or verdict.needs_human:
                raise HumanNeededError("verifier: task description requires human clarification")

            if verdict.pass_:
                self._emit(f"Plan approved.")
                return plan

            self._emit(f"Plan rejected — {len(verdict.issues)} issue(s). Replanning...")
            previous_issues = verdict.issues

        raise HumanNeededError(
            f"verifier: plan rejected {MAX_VERIFIER_RETRIES} times — human input required"
        )

    # ── Generation + Review loop ──────────────────────────────────────────────

    def _generation_review_loop(self, plan: Plan, codebase_context: str) -> OrchestratorResult:
        retry_feedback: list[ReviewVerdict] = []
        all_attempts: list[AttemptSummary] = []
        last_result: OrchestratorResult | None = None
        last_verdicts: list[ReviewVerdict] = []

        for regen_count in range(MAX_REGEN_RETRIES):
            attempt_label = f"attempt {regen_count + 1}/{MAX_REGEN_RETRIES}"
            self._emit(f"Generating code ({attempt_label})...")
            gen_agent = GeneratorAgent(config=self.config.generator_model_for(plan.primary_language))
            generated = gen_agent.run(
                GeneratorInput(plan=plan, codebase_context=codebase_context, retry_feedback=retry_feedback)
            )

            if gen_agent.last_needs_human:
                raise HumanNeededError("generator: implementation requires human clarification")

            if any(gc.confidence < 0.4 for gc in generated.subtasks):
                raise HumanNeededError(
                    "generator: confidence too low — plan may be unimplementable without human input"
                )

            n_files = len(generated.subtasks)
            self._emit(f"Generated {n_files} file(s). Running reviews...")
            verdicts = self._review_phase(plan, generated)
            all_attempts.append(AttemptSummary(attempt_number=regen_count + 1, verdicts=verdicts))

            for v in verdicts:
                icon = "✓" if v.pass_ else "✗"
                n_issues = len(v.issues)
                suffix = f" ({n_issues} issue(s))" if not v.pass_ else ""
                self._emit(f"  {icon} {v.reviewer.value}{suffix}")

            decision = self.aggregator.run(
                AggregatorInput(
                    verdicts=verdicts,
                    regen_count=regen_count,
                    task_id=plan.task_id,
                    all_attempts=all_attempts,
                )
            )

            last_result = OrchestratorResult(plan=plan, generated_code=generated, decision=decision, all_attempts=all_attempts)
            last_verdicts = verdicts

            if decision.action == AggregatorAction.DONE:
                return last_result

            if decision.action == AggregatorAction.HUMAN:
                raise HumanNeededError("aggregator: reviewer confidence too low — human input required")

            if decision.action == AggregatorAction.REPLAN:
                self._emit(f"Replanning based on reviewer feedback...")
                plan = self._replan(plan, decision, codebase_context, all_attempts)
                retry_feedback = []
                all_attempts = []
                regen_count = 0
                continue

            # REGEN: carry feedback forward
            self._emit(f"Regenerating with reviewer feedback...")
            retry_feedback = verdicts

        # Budget exhausted — accept best-effort if no critical issues and no approach_wrong
        has_critical = any(
            issue.severity == IssueSeverity.CRITICAL
            for v in last_verdicts if not v.pass_
            for issue in v.issues
        )
        has_approach_wrong = any(v.approach_wrong for v in last_verdicts)
        if last_result and not has_critical and not has_approach_wrong:
            self._emit("Accepting best-effort result (no critical issues).")
            return last_result

        raise HumanNeededError("regen budget exhausted — human input required")

    def _review_phase(self, plan, generated: GenerationResult) -> list[ReviewVerdict]:
        enabled = self._enabled  # None = all three
        review_input = ReviewInput(plan=plan, generated_code=generated.subtasks)
        verdicts: list[ReviewVerdict] = []

        func_enabled = enabled is None or "functional" in enabled
        if func_enabled:
            func_verdict = self.functional_reviewer.run(review_input)
            verdicts.append(func_verdict)
            if not func_verdict.pass_:
                return verdicts  # early exit: skip security + performance

        parallel: dict[str, object] = {}
        if enabled is None or "security" in enabled:
            parallel["security"] = self.security_reviewer
        if enabled is None or "performance" in enabled:
            parallel["performance"] = self.performance_reviewer

        if parallel:
            with ThreadPoolExecutor(max_workers=len(parallel)) as executor:
                futures = {
                    executor.submit(agent.run, review_input): name
                    for name, agent in parallel.items()
                }
                for future in as_completed(futures):
                    verdicts.append(future.result())

        return verdicts

    def _replan(
        self,
        plan: Plan,
        decision: AggregatorDecision,
        codebase_context: str,
        all_attempts: list[AttemptSummary],
    ) -> Plan:
        previous_issues: list[str] = []
        if decision.failure_report:
            previous_issues = decision.failure_report.replan_hints

        new_plan = self.planner.run(
            PlannerInput(
                task_description=plan.task_description,
                codebase_context=codebase_context,
                previous_issues=previous_issues,
            )
        )
        if self.planner.last_needs_human:
            raise HumanNeededError("planner (replan): task requires human input")

        verdict = self.verifier.run(new_plan)
        if not verdict.pass_ or verdict.needs_human:
            raise HumanNeededError("verifier (replan): revised plan rejected — human input required")

        return new_plan
