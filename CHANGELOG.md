# Changelog

## [1.1.7] - 2024-06-09

### Fixed
- Fixed critical Unicode encoding errors that were causing server crashes
- Enhanced text sanitization to handle problematic Unicode characters like narrow no-break spaces
- Improved MCP session patching to handle different versions of the MCP protocol
- Added more robust error handling for non-standard text in email bodies and headers
- Fixed compatibility issues with Windows console encoding limitations

### Added
- Better debugging information for MCP module structure
- Improved text sanitization for email content 
- Multiple fallback mechanisms for handling special characters
- Better error handling for IO operations

## [1.1.6] - 2024-06-08

### Fixed
- Completely rewrote the search-emails implementation to be more responsive
- Added timeouts to prevent client-side timeouts during long-running operations
- Implemented more efficient email header fetching for faster search results
- Improved error handling in the search-emails tool to avoid crashes
- Enhanced robustness of the cancellation notification handling
- Moved MCP protocol patching to server initialization phase for better stability

### Added
- More diagnostic information about the runtime environment
- Limit of 20 emails in search results to ensure quick responses
- Better error messages with specific guidance for user input errors

## [1.1.5] - 2024-06-07

### Fixed
- Fixed server crashes when the client sends cancellation notifications 
- Implemented a more robust method to handle the MCP protocol's cancellation messages
- Added monkey-patching of the MCP session handling to ensure compatibility
- Improved debugging output to show more server initialization details

## [1.1.4] - 2024-06-06

### Fixed
- Fixed an issue where the email client would hang when sending emails due to IMAP timeout when saving to Sent folder
- Improved handling of Infomaniak sent folder structure with multiple folder format attempts
- Added 10-second timeout for IMAP operations to prevent indefinite hanging
- Enhanced logging for sent folder operations to better diagnose issues

### Changed
- Restructured the sent folder saving logic to be more robust
- Added early return after email send to prevent blocking even if sent folder operations fail
- Expanded list of Infomaniak-specific folder path formats to try
- Improved error handling and error messages for better diagnostics

### Added
- Comprehensive logging for each folder selection attempt
- Timeout mechanism for IMAP operations
- Better folder path detection for Infomaniak servers

## [1.0.0] - 2024-06-01

### Added
- Initial fork from ZilongXue's project
- Added support for browsing email folders
- Fixed IMAP state errors
- Improved error handling and logging
- Enhanced mailbox selection logic 