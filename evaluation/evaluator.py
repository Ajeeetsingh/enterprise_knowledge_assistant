"""Domain evaluation orchestration: ask questions, collect artifacts."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api_client import KnowraApiClient
from config import Settings, domain_dir
from logger import EvaluationLogger
from utils import (
    ensure_domain_layout,
    extract_final_answer,
    extract_retrieved_documents,
    extract_retrieved_sources,
    join_list,
    read_questions,
    write_csv,
    write_json,
)

CSV_FIELDS = [
    "Question Number",
    "Question",
    "Response Time (seconds)",
    "HTTP Status",
    "Success/Failure",
    "Retrieved Documents",
    "Retrieved Sources",
    "Final Answer",
]


@dataclass
class QuestionResult:
    question_number: int
    question: str
    response_time_seconds: float
    http_status: int | None
    success: bool
    error: str | None
    conversation_id: str | None
    retrieved_documents: list[str] = field(default_factory=list)
    retrieved_sources: list[str] = field(default_factory=list)
    final_answer: str = ""
    api_response: dict[str, Any] | None = None
    raw_body: str | None = None

    def to_csv_row(self) -> dict[str, Any]:
        return {
            "Question Number": self.question_number,
            "Question": self.question,
            "Response Time (seconds)": f"{self.response_time_seconds:.3f}",
            "HTTP Status": self.http_status if self.http_status is not None else "",
            "Success/Failure": "Success" if self.success else "Failure",
            "Retrieved Documents": join_list(self.retrieved_documents),
            "Retrieved Sources": join_list(self.retrieved_sources),
            "Final Answer": self.final_answer,
        }

    def to_json_item(self) -> dict[str, Any]:
        return {
            "question_number": self.question_number,
            "question": self.question,
            "response_time_seconds": round(self.response_time_seconds, 3),
            "http_status": self.http_status,
            "success": self.success,
            "error": self.error,
            "api_response": self.api_response,
            "raw_body": self.raw_body,
            "metadata": {
                "conversation_id": self.conversation_id,
                "retrieved_documents": self.retrieved_documents,
                "retrieved_sources": self.retrieved_sources,
                "final_answer": self.final_answer,
            },
        }


@dataclass
class RunSummary:
    total_questions: int
    successful_requests: int
    failed_requests: int
    average_response_time: float | None
    fastest_response: float | None
    slowest_response: float | None
    total_execution_time: float

    def to_text(self) -> str:
        def fmt(value: float | None) -> str:
            return f"{value:.3f}s" if value is not None else "n/a"

        lines = [
            "Knowra Evaluation Summary",
            "=========================",
            f"Total Questions:        {self.total_questions}",
            f"Successful Requests:    {self.successful_requests}",
            f"Failed Requests:        {self.failed_requests}",
            f"Average Response Time:  {fmt(self.average_response_time)}",
            f"Fastest Response:       {fmt(self.fastest_response)}",
            f"Slowest Response:       {fmt(self.slowest_response)}",
            f"Total Execution Time:   {self.total_execution_time:.3f}s",
            "",
        ]
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DomainEvaluator:
    """Run all questions for one domain folder and overwrite output artifacts."""

    def __init__(self, domain_name: str, settings: Settings) -> None:
        self.domain_name = domain_name
        self.settings = settings
        self.domain_path: Path = domain_dir(domain_name)
        ensure_domain_layout(self.domain_path)

        self.questions_path = self.domain_path / "questions.txt"
        self.responses_csv_path = self.domain_path / "responses.csv"
        self.responses_json_path = self.domain_path / "responses.json"
        self.summary_path = self.domain_path / "summary.txt"
        self.logs_path = self.domain_path / "logs.txt"

        self.logger = EvaluationLogger(self.logs_path)
        self.client = KnowraApiClient(settings, self.logger)

    def run(self) -> RunSummary:
        started = time.perf_counter()
        questions = read_questions(self.questions_path)
        total = len(questions)

        self.logger.info(f"Domain: {self.domain_name}")
        self.logger.info(f"Questions file: {self.questions_path}")
        self.logger.info(f"API base URL: {self.settings.api_base_url}")
        self.logger.info(f"Loaded {total} question(s).")

        if total == 0:
            self.logger.warning("No questions found after filtering blanks/comments.")

        self.client.ensure_authenticated()

        shared_conversation_id: str | None = None
        if not self.settings.create_conversation_per_question and total > 0:
            shared_conversation_id = self.client.create_conversation(
                title=f"{self.settings.conversation_title_prefix} — {self.domain_name}"
            )
            self.logger.info(
                f"Reusing conversation for all questions: {shared_conversation_id}"
            )

        results: list[QuestionResult] = []
        for index, question in enumerate(questions, start=1):
            print(f"[{index}/{total}] Processing...")
            self.logger.info(f"[{index}/{total}] Starting question.")
            self.logger.debug(f"[{index}/{total}] Question text: {question}")

            result = self._evaluate_one(
                question_number=index,
                question=question,
                shared_conversation_id=shared_conversation_id,
            )
            results.append(result)

            status_label = "OK" if result.success else "FAIL"
            print(
                f"[{index}/{total}] {status_label} "
                f"({result.response_time_seconds:.2f}s)"
            )
            self.logger.info(
                f"[{index}/{total}] Finished: success={result.success} "
                f"http_status={result.http_status} "
                f"time={result.response_time_seconds:.3f}s"
            )
            if not result.success:
                self.logger.error(
                    f"[{index}/{total}] Failed request: {result.error}"
                )

            # Stay under the backend chat-ask rate limit (30/min by default).
            if (
                index < total
                and self.settings.request_delay_seconds > 0
            ):
                time.sleep(self.settings.request_delay_seconds)

        total_execution_time = time.perf_counter() - started
        summary = self._build_summary(results, total_execution_time)
        self._write_artifacts(results, summary)

        print()
        print(summary.to_text())
        print(f"Wrote: {self.responses_csv_path}")
        print(f"Wrote: {self.responses_json_path}")
        print(f"Wrote: {self.summary_path}")
        print(f"Wrote: {self.logs_path}")
        self.logger.info("Evaluation run completed.")
        return summary

    def _evaluate_one(
        self,
        *,
        question_number: int,
        question: str,
        shared_conversation_id: str | None,
    ) -> QuestionResult:
        conversation_id: str | None = shared_conversation_id
        started = time.perf_counter()

        try:
            if conversation_id is None:
                conversation_id = self.client.create_conversation(
                    title=(
                        f"{self.settings.conversation_title_prefix} — "
                        f"{self.domain_name} #{question_number}"
                    )
                )
                self.logger.debug(
                    f"[{question_number}] Created conversation {conversation_id}"
                )

            api_result = self.client.ask_question(conversation_id, question)
            elapsed = time.perf_counter() - started

            documents = extract_retrieved_documents(api_result.payload)
            sources = extract_retrieved_sources(api_result.payload)
            answer = extract_final_answer(api_result.payload)

            return QuestionResult(
                question_number=question_number,
                question=question,
                response_time_seconds=elapsed,
                http_status=api_result.http_status,
                success=api_result.ok,
                error=api_result.error,
                conversation_id=conversation_id,
                retrieved_documents=documents,
                retrieved_sources=sources,
                final_answer=answer,
                api_response=api_result.payload,
                raw_body=api_result.raw_body,
            )
        except Exception as exc:  # noqa: BLE001 — never abort the full run
            elapsed = time.perf_counter() - started
            self.logger.exception(
                f"[{question_number}] Unhandled exception while evaluating",
                exc,
            )
            return QuestionResult(
                question_number=question_number,
                question=question,
                response_time_seconds=elapsed,
                http_status=None,
                success=False,
                error=f"{type(exc).__name__}: {exc}",
                conversation_id=conversation_id,
            )

    def _build_summary(
        self,
        results: list[QuestionResult],
        total_execution_time: float,
    ) -> RunSummary:
        times = [item.response_time_seconds for item in results]
        successful = sum(1 for item in results if item.success)
        failed = len(results) - successful
        average = (sum(times) / len(times)) if times else None
        fastest = min(times) if times else None
        slowest = max(times) if times else None
        return RunSummary(
            total_questions=len(results),
            successful_requests=successful,
            failed_requests=failed,
            average_response_time=average,
            fastest_response=fastest,
            slowest_response=slowest,
            total_execution_time=total_execution_time,
        )

    def _write_artifacts(
        self,
        results: list[QuestionResult],
        summary: RunSummary,
    ) -> None:
        # Overwrite all four artifacts every run.
        write_csv(
            self.responses_csv_path,
            [item.to_csv_row() for item in results],
            CSV_FIELDS,
        )

        payload = {
            "domain": self.domain_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "api_base_url": self.settings.api_base_url,
            "questions_file": str(self.questions_path),
            "summary": summary.to_dict(),
            "results": [item.to_json_item() for item in results],
        }
        write_json(self.responses_json_path, payload)
        self.summary_path.write_text(summary.to_text(), encoding="utf-8")
        self.logger.info("Output artifacts overwritten.")
