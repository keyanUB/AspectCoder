from aspectcoder.agents.reviewers.base import BaseReviewerAgent


class PerformanceReviewerAgent(BaseReviewerAgent):
    reviewer_name = "performance"
    reviewer_focus = (
        "algorithmic efficiency and resource usage: "
        "time complexity — is the algorithm appropriate for the expected data scale? "
        "memory usage — unnecessary allocations, leaks, large stack frames in C/C++; "
        "hot path analysis — expensive operations in tight loops; "
        "language-specific patterns — Python list comprehensions vs loops, JS async overhead."
    )
