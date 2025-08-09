# VK Photos Project - Refactoring Plan

## Overview
This document outlines a comprehensive refactoring plan to bring the VK Photos project into compliance with established project rules and best practices. The plan is broken down into simple, sequential tasks that can be executed by an AI assistant.

## Project Rules Compliance Issues
- ❌ Login/password authentication (FORBIDDEN)
- ❌ File deletion operations (FORBIDDEN)
- ❌ Interactive CLI instead of Click (FORBIDDEN)
- ❌ Missing type annotations
- ❌ Missing docstrings
- ❌ Monolithic code structure
- ❌ No download consistency management
- ❌ No rate limiting
- ❌ No test suite
- ❌ Poor error handling

## Refactoring Tasks

### Phase 1: Security & Safety (CRITICAL)

#### Task 1.1: Remove Login/Password Authentication
**Priority**: CRITICAL
**Files to modify**: `vk_photos/main.py`, `vk_photos/config.yaml`
**Actions**:
1. Remove `auth()` method from `Utils` class in `main.py`
2. Remove `login` and `password` fields from `config.yaml`
3. Update all references to use only `auth_by_token()` method
4. Add validation to ensure only token authentication is used

**Acceptance Criteria**:
- No login/password authentication code exists
- Only token-based authentication is available
- Config file contains only token field

---

#### Task 1.2: Remove File Deletion Operations
**Priority**: CRITICAL
**Files to modify**: `vk_photos/main.py`, `vk_photos/filter.py`
**Actions**:
1. Remove `remove_dir()` method from `Utils` class
2. Replace duplicate file deletion in `filter.py` with safe operations
3. Implement safe file operations that only create and append
4. Add logging for skipped files instead of deletion

**Acceptance Criteria**:
- No file deletion operations exist
- Files are only created or appended to
- Existing files are skipped with logging

---

#### Task 1.3: Implement Download Consistency Management
**Priority**: CRITICAL
**Files to create**: `vk_photos/utils/consistency.py`
**Actions**:
1. Create `ConsistencyManager` class with file locking
2. Implement persistent storage of downloaded file list
3. Add methods to check and mark files as downloaded
4. Integrate with all downloader classes

**Acceptance Criteria**:
- `ConsistencyManager` class exists with proper methods
- Downloaded files are tracked persistently
- Multiple program instances work safely together
- File locking prevents race conditions

---

### Phase 2: CLI Interface (CRITICAL)

#### Task 2.1: Implement Click-Based CLI
**Priority**: CRITICAL
**Files to modify**: `vk_photos/main.py`
**Actions**:
1. Install Click dependency if not present
2. Replace interactive `input()` calls with Click commands
3. Create main Click command with subcommands for each download type
4. Add proper argument validation and help text

**Acceptance Criteria**:
- No `input()` calls exist in the code
- Click-based CLI with proper subcommands
- Environment variable support for all parameters
- Help text and argument validation

---

#### Task 2.2: Add Environment Variable Support
**Priority**: HIGH
**Files to create**: `vk_photos/config/settings.py`
**Actions**:
1. Create `SecureConfig` class for configuration management
2. Add environment variable support for all parameters
3. Implement secure token handling
4. Add configuration validation

**Acceptance Criteria**:
- Environment variables work for all parameters
- Token is never passed via CLI arguments
- Configuration is loaded securely
- Validation prevents insecure configurations

---

### Phase 3: Code Structure (HIGH)

#### Task 3.1: Create Modular Directory Structure
**Priority**: HIGH
**Actions**:
1. Create `vk_photos/downloaders/` directory
2. Create `vk_photos/utils/` directory
3. Create `vk_photos/config/` directory
4. Create `tests/` directory
5. Add `__init__.py` files to all directories

**Acceptance Criteria**:
- All directories exist with proper structure
- `__init__.py` files are present
- Directory structure follows project rules

---

#### Task 3.2: Extract User Downloader
**Priority**: HIGH
**Files to create**: `vk_photos/downloaders/user.py`
**Files to modify**: `vk_photos/main.py`
**Actions**:
1. Extract `UserPhotoDownloader` and `UsersPhotoDownloader` classes
2. Move to `vk_photos/downloaders/user.py`
3. Add proper imports and exports
4. Update main.py to import from new location

**Acceptance Criteria**:
- User downloader classes are in separate file
- Proper imports and exports work
- Main.py imports from new location
- No functionality is lost

---

#### Task 3.3: Extract Group Downloader
**Priority**: HIGH
**Files to create**: `vk_photos/downloaders/group.py`
**Files to modify**: `vk_photos/main.py`
**Actions**:
1. Extract `GroupPhotoDownloader`, `GroupsPhotoDownloader`, and `GroupAlbumsDownloader` classes
2. Move to `vk_photos/downloaders/group.py`
3. Add proper imports and exports
4. Update main.py to import from new location

**Acceptance Criteria**:
- Group downloader classes are in separate file
- Proper imports and exports work
- Main.py imports from new location
- No functionality is lost

---

#### Task 3.4: Extract Chat Downloader
**Priority**: HIGH
**Files to create**: `vk_photos/downloaders/chat.py`
**Files to modify**: `vk_photos/main.py`
**Actions**:
1. Extract `ChatMembersPhotoDownloader`, `ChatPhotoDownloader`, and `ChatUserPhotoDownloader` classes
2. Move to `vk_photos/downloaders/chat.py`
3. Add proper imports and exports
4. Update main.py to import from new location

**Acceptance Criteria**:
- Chat downloader classes are in separate file
- Proper imports and exports work
- Main.py imports from new location
- No functionality is lost

---

#### Task 3.5: Extract Utility Functions
**Priority**: HIGH
**Files to create**: `vk_photos/utils/auth.py`, `vk_photos/utils/validation.py`, `vk_photos/utils/file_ops.py`
**Files to modify**: `vk_photos/main.py`, `vk_photos/functions.py`
**Actions**:
1. Extract authentication methods to `auth.py`
2. Extract validation methods to `validation.py`
3. Extract file operations to `file_ops.py`
4. Update imports in all files

**Acceptance Criteria**:
- Utility functions are properly organized
- No circular imports exist
- All imports work correctly
- Functionality is preserved

---

### Phase 4: Type Annotations & Documentation (HIGH)

#### Task 4.1: Add Type Annotations to All Functions
**Priority**: HIGH
**Files to modify**: All Python files
**Actions**:
1. Add return type annotations to all functions
2. Add parameter type annotations
3. Add proper imports for typing
4. Ensure mypy compliance

**Acceptance Criteria**:
- All functions have type annotations
- No mypy errors
- Proper typing imports
- Type hints are accurate

---

#### Task 4.2: Add Comprehensive Docstrings
**Priority**: HIGH
**Files to modify**: All Python files
**Actions**:
1. Add class docstrings following PEP 257
2. Add function docstrings with parameters and return values
3. Add module docstrings
4. Ensure docstrings are descriptive and helpful

**Acceptance Criteria**:
- All classes have docstrings
- All functions have docstrings
- Docstrings follow PEP 257
- Documentation is comprehensive

---

### Phase 5: Error Handling & Logging (MEDIUM)

#### Task 5.1: Implement Exception Hierarchy
**Priority**: MEDIUM
**Files to create**: `vk_photos/utils/exceptions.py`
**Actions**:
1. Create base `VKScroblerError` exception
2. Create specific exception classes
3. Replace generic exception handling
4. Add proper error messages

**Acceptance Criteria**:
- Custom exception hierarchy exists
- Specific exceptions for different error types
- Proper error messages
- No generic exception handling

---

#### Task 5.2: Improve Logging
**Priority**: MEDIUM
**Files to modify**: All Python files
**Actions**:
1. Replace print statements with logging
2. Standardize logging format
3. Add appropriate log levels
4. Ensure consistent logging throughout

**Acceptance Criteria**:
- No print statements exist
- Consistent logging format
- Appropriate log levels used
- Logging is informative

---

### Phase 6: Performance & Safety (MEDIUM)

#### Task 6.1: Implement Rate Limiting
**Priority**: MEDIUM
**Files to create**: `vk_photos/utils/rate_limiter.py`
**Actions**:
1. Create `RateLimitedVKAPI` class
2. Implement rate limiting for VK API calls
3. Add configurable requests per second
4. Integrate with all API calls

**Acceptance Criteria**:
- Rate limiting is implemented
- Configurable rate limits
- No API rate limit violations
- Performance is maintained

---

#### Task 6.2: Implement Skip Already Downloaded Files
**Priority**: MEDIUM
**Files to modify**: All downloader classes
**Actions**:
1. Add file existence checks before downloading
2. Integrate with ConsistencyManager
3. Add logging for skipped files
4. Ensure no duplicate downloads

**Acceptance Criteria**:
- Files are checked before downloading
- Already downloaded files are skipped
- Proper logging for skipped files
- No duplicate downloads occur

---

### Phase 7: Testing (MEDIUM)

#### Task 7.1: Create Test Directory Structure
**Priority**: MEDIUM
**Actions**:
1. Create `tests/` directory
2. Add `__init__.py` files
3. Create test files for each module
4. Set up pytest configuration

**Acceptance Criteria**:
- Test directory structure exists
- Pytest configuration is correct
- Test files are created
- Tests can be run

---

#### Task 7.2: Write Unit Tests
**Priority**: MEDIUM
**Files to create**: `tests/test_downloaders.py`, `tests/test_utils.py`, `tests/test_config.py`
**Actions**:
1. Write tests for downloader classes
2. Write tests for utility functions
3. Write tests for configuration
4. Add proper test fixtures

**Acceptance Criteria**:
- Tests exist for all major functionality
- Tests use pytest and proper typing
- Tests have docstrings
- Tests pass successfully

---

### Phase 8: Configuration & Dependencies (LOW)

#### Task 8.1: Update Python Version Constraints
**Priority**: LOW
**Files to modify**: `pyproject.toml`
**Actions**:
1. Update Python version constraint to 3.10+
2. Update dependency versions
3. Ensure compatibility
4. Test with newer Python versions

**Acceptance Criteria**:
- Python 3.10+ is supported
- Dependencies are up to date
- No compatibility issues
- Project works with newer Python

---

#### Task 8.2: Add Ruff Configuration
**Priority**: LOW
**Files to create**: `pyproject.toml` (update)
**Actions**:
1. Add Ruff configuration to pyproject.toml
2. Configure code style rules
3. Add pre-commit hooks
4. Ensure code style consistency

**Acceptance Criteria**:
- Ruff is configured
- Code style is consistent
- Pre-commit hooks work
- No style violations

---

## Task Execution Order

### Immediate (Security & Safety)
1. Task 1.1: Remove Login/Password Authentication
2. Task 1.2: Remove File Deletion Operations
3. Task 1.3: Implement Download Consistency Management

### High Priority (Core Functionality)
4. Task 2.1: Implement Click-Based CLI
5. Task 2.2: Add Environment Variable Support
6. Task 3.1: Create Modular Directory Structure
7. Task 3.2: Extract User Downloader
8. Task 3.3: Extract Group Downloader
9. Task 3.4: Extract Chat Downloader
10. Task 3.5: Extract Utility Functions

### Medium Priority (Quality & Testing)
11. Task 4.1: Add Type Annotations to All Functions
12. Task 4.2: Add Comprehensive Docstrings
13. Task 5.1: Implement Exception Hierarchy
14. Task 5.2: Improve Logging
15. Task 6.1: Implement Rate Limiting
16. Task 6.2: Implement Skip Already Downloaded Files
17. Task 7.1: Create Test Directory Structure
18. Task 7.2: Write Unit Tests

### Low Priority (Polish)
19. Task 8.1: Update Python Version Constraints
20. Task 8.2: Add Ruff Configuration

## Success Criteria

The refactoring is complete when:
- ✅ All security violations are fixed
- ✅ All project rules are followed
- ✅ Code is modular and maintainable
- ✅ Type annotations are complete
- ✅ Documentation is comprehensive
- ✅ Tests exist and pass
- ✅ Performance is maintained or improved
- ✅ User experience is enhanced

## Notes for AI Assistant

1. **Always follow project rules strictly** - especially authentication and data safety rules
2. **Test each task thoroughly** before moving to the next
3. **Maintain backward compatibility** where possible
4. **Use proper error handling** throughout
5. **Add comprehensive logging** for debugging
6. **Follow Python best practices** and PEP standards
7. **Ensure all imports work correctly** after refactoring
8. **Validate configuration** at startup
9. **Add proper validation** for all inputs
10. **Maintain async/await patterns** where appropriate

Each task should be completed independently and tested before moving to the next task. This ensures that the refactoring is done safely and incrementally.
