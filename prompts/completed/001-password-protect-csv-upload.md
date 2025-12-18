<objective>
Add password protection to the CSV file upload functionality in the SNOWGREP application.

Only users who enter the correct password should be able to access the file uploader and upload CSV files. This protects sensitive ServiceNow incident data from unauthorized uploads.
</objective>

<context>
This is a Streamlit application (app.py) that allows users to upload ServiceNow incident CSV files for querying.

The current file upload implementation is in the `render_sidebar()` function (around line 407):
- Uses `st.file_uploader()` with type restricted to CSV
- Has REPLACE and APPEND buttons that appear after file selection
- Currently has no access control

Tech stack:
- Python 3.x with Streamlit
- Brutalist terminal-style UI theme (dark background, green accents)
</context>

<requirements>
1. Add a password input field above the file uploader in the sidebar
2. The file uploader should only be visible/functional after correct password entry
3. Use Streamlit session state to track authentication status
4. Password should be configurable (suggest storing in environment variable or config)
5. Failed password attempts should show an error message
6. Successful authentication should persist for the session
7. Include a "Lock" button to re-lock the upload functionality if needed
</requirements>

<implementation>
Follow these steps:

1. Add a new session state variable for upload authentication:
   - `upload_authenticated` (boolean, default False)

2. Create a password verification section in `render_sidebar()` BEFORE the file uploader:
   - Show password input when not authenticated
   - Verify against configured password
   - Update session state on successful entry

3. Wrap the file uploader and REPLACE/APPEND buttons in a conditional:
   - Only show when `upload_authenticated` is True
   - Show "locked" message when False

4. Add a "LOCK UPLOAD" button when authenticated to allow re-locking

5. Style the password input and lock/unlock states to match the brutalist theme:
   - Use uppercase labels
   - Green (#00ff00) for success states
   - Red (#ff5f56) for locked/error states

Password storage approach:
- Check for `SNOWGREP_UPLOAD_PASSWORD` environment variable first
- Fall back to a default password "admin123" for development (with a warning)
- Document this in code comments
</implementation>

<output>
Modify: `./app.py`
- Add password protection logic to `render_sidebar()` function
- Add `upload_authenticated` to `init_session_state()`
- Password field and authentication logic before file uploader
- Conditional rendering of upload components

The file uploader section should transform from:
```
### DATA INGEST
[File Uploader]
DROP CSV FILE HERE
```

To:
```
### DATA INGEST
[Password Input] (when locked)
[🔒 UPLOAD LOCKED] (status when locked)
OR
[🔓 UPLOAD UNLOCKED] (status when unlocked)
[File Uploader] (only when unlocked)
DROP CSV FILE HERE
[LOCK UPLOAD] button (only when unlocked)
```
</output>

<verification>
After implementation, verify:
1. App starts with upload locked (file uploader not visible)
2. Wrong password shows error, uploader remains hidden
3. Correct password unlocks uploader
4. REPLACE and APPEND buttons work after unlocking
5. LOCK UPLOAD button re-locks the functionality
6. Refreshing page resets to locked state (session-based)
7. UI styling matches existing brutalist theme
</verification>

<success_criteria>
- File uploader is hidden by default
- Password authentication works correctly
- Session state properly tracks auth status
- Lock/unlock flow is intuitive
- Styling is consistent with existing UI
- No security vulnerabilities (password not exposed in UI)
</success_criteria>
