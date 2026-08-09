"""Canonical enumerations for Knowledge Objects (Phase 13.1)."""

from __future__ import annotations

from enum import StrEnum


class DocumentType(StrEnum):
    RESUME = "Resume"
    POLICY = "Policy"
    HANDBOOK = "Handbook"
    INVOICE = "Invoice"
    RESEARCH_PAPER = "Research Paper"
    FINANCIAL_REPORT = "Financial Report"
    PRESENTATION = "Presentation"
    CONTRACT = "Contract"
    MANUAL = "Manual"
    UNKNOWN = "Unknown"


class Department(StrEnum):
    SUPPORT = "Support"
    HR = "HR"
    FINANCE = "Finance"
    IT = "IT"
    SECURITY = "Security"
    ENGINEERING = "Engineering"
    LEGAL = "Legal"
    ADMIN = "Admin"
    MARKETING = "Marketing"
    SALES = "Sales"
    OPERATIONS = "Operations"
    PERSONAL = "Personal"
    EXTERNAL = "External"
    UNKNOWN = "Unknown"


class EntityType(StrEnum):
    PEOPLE = "people"
    COMPANIES = "companies"
    PROJECTS = "projects"
    DEPARTMENTS = "departments"
    TECHNOLOGIES = "technologies"
    POLICIES = "policies"
    PRODUCTS = "products"
    STANDARDS = "standards"
    DATES = "dates"
    LOCATIONS = "locations"
    EMAIL = "email"
    PHONE = "phone"
    DOCUMENT_IDS = "document_ids"


class KnowledgeProcessingStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
