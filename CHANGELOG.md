# Changelog

## [1.1.0] - 2024-06-05

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