"""Canonical audit event identifiers used by analytics queries."""


class AnalyticsEvents:
    """Audit event type strings aggregated into analytics dashboards.

    Values must match persisted ``AuditLog.event_type`` values emitted by
    integration modules (auth, chat, document, security).
    """

    CHAT_QUESTION = "chat.question.asked"
    CHAT_RESPONSE = "chat.answer.generated"
    CHAT_FAILURE = "chat.retrieval.failed"
    DOCUMENT_UPLOAD = "document.uploaded"
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILED = "auth.login.failed"
    SECURITY_PERMISSION_DENIED = "security.permission.denied"
    SECURITY_INVALID_TOKEN = "security.invalid.token"
    SECURITY_UNAUTHORIZED_ACCESS = "security.unauthorized.access"
