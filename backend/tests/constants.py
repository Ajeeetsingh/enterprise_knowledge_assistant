"""Shared test constants — avoid recomputing expensive bcrypt hashes in fixtures."""

TEST_PASSWORD = "Str0ng!Passw0rd"

# Precomputed bcrypt hash for TEST_PASSWORD (rounds=12). Used by fixtures only;
# password service tests still call hash_password() directly.
TEST_PASSWORD_HASH = (
    "$2b$12$NQ8N7SAXpOOD2oIAVi0MsejiW69WQMhP/ICY5G39wfmmjCxaZhZTu"
)
