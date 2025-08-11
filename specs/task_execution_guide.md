# Task Execution Guide for AI Assistant

This guide provides simple, individual task commands that you can send to the AI assistant to execute the refactoring plan.

## How to Use

Copy and paste the task command below into your message to the AI assistant. Each task is designed to be executed independently and in sequence.

---

## Phase 1: Security & Safety (CRITICAL)

### Task 1.1: Remove Login/Password Authentication
**Command to send to AI:**
```
Execute Task 1.1: Remove Login/Password Authentication

Remove the login/password authentication method from the Utils class in vk_archiver/main.py and remove the login and password fields from vk_archiver/config.yaml. Ensure only token-based authentication is available and add validation to prevent login/password usage.
```

---

### Task 1.2: Remove File Deletion Operations
**Command to send to AI:**
```
Execute Task 1.2: Remove File Deletion Operations

Remove the remove_dir() method from the Utils class in vk_archiver/main.py and replace the duplicate file deletion in vk_archiver/filter.py with safe operations that only create and append files. Add logging for skipped files instead of deletion.
```

---

### Task 1.3: Implement Download Consistency Management
**Command to send to AI:**
```
Execute Task 1.3: Implement Download Consistency Management

Create a new file vk_archiver/utils/consistency.py with a ConsistencyManager class that implements file locking and persistent storage of downloaded file list. Add methods to check and mark files as downloaded, and integrate with all downloader classes to prevent duplicate downloads across multiple program instances.
```

---

## Phase 2: CLI Interface (CRITICAL)

### Task 2.1: Implement Click-Based CLI
**Command to send to AI:**
```
Execute Task 2.1: Implement Click-Based CLI

Replace all interactive input() calls in vk_archiver/main.py with Click commands. Create a main Click command with subcommands for each download type (user, group, chat, etc.). Add proper argument validation and help text. Ensure no input() calls remain in the code.
```

---

### Task 2.2: Add Environment Variable Support
**Command to send to AI:**
```
Execute Task 2.2: Add Environment Variable Support

Create a new file vk_archiver/config/settings.py with a SecureConfig class for configuration management. Add environment variable support for all parameters (VK_TOKEN, VK_USER_ID, VK_GROUP_ID, etc.). Implement secure token handling that never passes tokens via CLI arguments. Add configuration validation.
```

---

## Phase 3: Code Structure (HIGH)

### Task 3.1: Create Modular Directory Structure
**Command to send to AI:**
```
Execute Task 3.1: Create Modular Directory Structure

Create the following directory structure:
- vk_archiver/downloaders/
- vk_archiver/utils/
- vk_archiver/config/
- tests/

Add __init__.py files to all directories to make them proper Python packages.
```

---

### Task 3.2: Extract User Downloader
**Command to send to AI:**
```
Execute Task 3.2: Extract User Downloader

Extract the UserPhotoDownloader and UsersPhotoDownloader classes from vk_archiver/main.py and move them to vk_archiver/downloaders/user.py. Add proper imports and exports, and update main.py to import from the new location. Ensure no functionality is lost.
```

---

### Task 3.3: Extract Group Downloader
**Command to send to AI:**
```
Execute Task 3.3: Extract Group Downloader

Extract the GroupPhotoDownloader, GroupsPhotoDownloader, and GroupAlbumsDownloader classes from vk_archiver/main.py and move them to vk_archiver/downloaders/group.py. Add proper imports and exports, and update main.py to import from the new location. Ensure no functionality is lost.
```

---

### Task 3.4: Extract Chat Downloader
**Command to send to AI:**
```
Execute Task 3.4: Extract Chat Downloader

Extract the ChatMembersPhotoDownloader, ChatPhotoDownloader, and ChatUserPhotoDownloader classes from vk_archiver/main.py and move them to vk_archiver/downloaders/chat.py. Add proper imports and exports, and update main.py to import from the new location. Ensure no functionality is lost.
```

---

### Task 3.5: Extract Utility Functions
**Command to send to AI:**
```
Execute Task 3.5: Extract Utility Functions

Extract authentication methods from Utils class to vk_archiver/utils/auth.py, validation methods to vk_archiver/utils/validation.py, and file operations to vk_archiver/utils/file_ops.py. Update all imports in affected files. Ensure no circular imports exist and all functionality is preserved.
```

---

## Phase 4: Type Annotations & Documentation (HIGH)

### Task 4.1: Add Type Annotations to All Functions
**Command to send to AI:**
```
Execute Task 4.1: Add Type Annotations to All Functions

Add comprehensive type annotations to all functions in the entire codebase. Include return type annotations, parameter type annotations, and proper imports for typing. Ensure mypy compliance and that all type hints are accurate.
```

---

### Task 4.2: Add Comprehensive Docstrings
**Command to send to AI:**
```
Execute Task 4.2: Add Comprehensive Docstrings

Add comprehensive docstrings to all classes and functions in the codebase. Follow PEP 257 conventions with proper parameter descriptions, return value descriptions, and examples where appropriate. Ensure all documentation is descriptive and helpful.
```

---

## Phase 5: Error Handling & Logging (MEDIUM)

### Task 5.1: Implement Exception Hierarchy
**Command to send to AI:**
```
Execute Task 5.1: Implement Exception Hierarchy

Create a new file vk_archiver/utils/exceptions.py with a custom exception hierarchy. Include a base VKScroblerError exception and specific exception classes for different error types (AuthenticationError, DownloadError, etc.). Replace generic exception handling throughout the codebase with specific exception handling.
```

---

### Task 5.2: Improve Logging
**Command to send to AI:**
```
Execute Task 5.2: Improve Logging

Replace all print statements with proper logging throughout the codebase. Standardize logging format and add appropriate log levels (DEBUG, INFO, WARNING, ERROR). Ensure consistent logging throughout the application and that logging is informative for debugging.
```

---

## Phase 6: Performance & Safety (MEDIUM)

### Task 6.1: Implement Rate Limiting
**Command to send to AI:**
```
Execute Task 6.1: Implement Rate Limiting

Create a new file vk_archiver/utils/rate_limiter.py with a RateLimitedVKAPI class that implements rate limiting for VK API calls. Add configurable requests per second (default 3) and integrate with all API calls throughout the codebase. Ensure no API rate limit violations occur.
```

---

### Task 6.2: Implement Skip Already Downloaded Files
**Command to send to AI:**
```
Execute Task 6.2: Implement Skip Already Downloaded Files

Add file existence checks before downloading in all downloader classes. Integrate with the ConsistencyManager to track downloaded files. Add proper logging for skipped files and ensure no duplicate downloads occur. This should work across multiple program instances.
```

---

## Phase 7: Testing (MEDIUM)

### Task 7.1: Create Test Directory Structure
**Command to send to AI:**
```
Execute Task 7.1: Create Test Directory Structure

Create the tests/ directory with proper structure. Add __init__.py files and create test files for each module (test_downloaders.py, test_utils.py, test_config.py). Set up pytest configuration in pyproject.toml to ensure tests can be run properly.
```

---

### Task 7.2: Write Unit Tests
**Command to send to AI:**
```
Execute Task 7.2: Write Unit Tests

Write comprehensive unit tests for all major functionality in the codebase. Include tests for downloader classes, utility functions, and configuration management. Use pytest with proper typing annotations and docstrings. Ensure all tests pass successfully.
```

---

## Phase 8: Configuration & Dependencies (LOW)

### Task 8.1: Update Python Version Constraints
**Command to send to AI:**
```
Execute Task 8.1: Update Python Version Constraints

Update the Python version constraint in pyproject.toml from ">=3.10, <3.11" to ">=3.10" to support Python 3.10 and above. Update dependency versions to latest stable versions and ensure compatibility. Test that the project works with newer Python versions.
```

---

### Task 8.2: Add Ruff Configuration
**Command to send to AI:**
```
Execute Task 8.2: Add Ruff Configuration

Add Ruff configuration to pyproject.toml with appropriate code style rules. Configure the linter to enforce consistent code style throughout the project. Ensure no style violations exist and that the code follows Python best practices.
```

---

## Execution Tips

1. **Execute tasks in order** - Each task builds on the previous ones
2. **Test after each task** - Verify the changes work before moving to the next
3. **Check for errors** - Ensure no functionality is broken
4. **Follow project rules** - Always adhere to the established project rules
5. **Maintain compatibility** - Don't break existing functionality

## Success Verification

After completing all tasks, verify:
- ✅ No login/password authentication exists
- ✅ No file deletion operations exist
- ✅ Click-based CLI works properly
- ✅ All imports work correctly
- ✅ Type annotations are complete
- ✅ Tests pass successfully
- ✅ Code follows project rules
- ✅ Performance is maintained
