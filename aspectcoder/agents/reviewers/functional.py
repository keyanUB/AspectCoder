from aspectcoder.agents.reviewers.base import BaseReviewerAgent


class FunctionalReviewerAgent(BaseReviewerAgent):
    reviewer_name = "functional correctness"
    reviewer_focus = (
        "correctness: does the implementation match the specification? "
        "Are edge cases handled (empty input, null, overflow)? "
        "Are function signatures and return types correct? "
        "Is test coverage adequate if tests are part of the plan?"
    )
