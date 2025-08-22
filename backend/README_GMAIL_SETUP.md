# Gmail Integration Setup Guide

This guide will help you set up Gmail OAuth2 authentication to automatically parse job application emails.

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API:
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"

## Step 2: Create OAuth2 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client IDs"
3. Choose "Desktop application" as the application type
4. Give it a name (e.g., "Job Tracker Gmail")
5. Click "Create"
6. Download the JSON file and save it as `credentials.json` in the `backend/` directory

## Step 3: Test Authentication

1. Make sure you have the credentials file in place:
   ```bash
   # From project root
   ls backend/credentials.json
   ```

2. Test the Gmail connection:
   ```bash
   cd backend
   python -c "from app.gmail_auth import test_gmail_connection; test_gmail_connection()"
   ```

3. This will open a browser window for OAuth authentication. Follow the prompts to authorize the application.

## Step 4: Test Email Parsing

1. Run the email parser directly:
   ```bash
   cd backend
   python -c "from app.email_parser import process_gmail_applications; print(process_gmail_applications())"
   ```

2. Or test via the API endpoint:
   ```bash
   curl -X POST http://localhost:8000/gmail/process
   ```

## Step 5: Add to Frontend (Optional)

Add a button to the React frontend to trigger Gmail processing:

```typescript
const processGmail = async () => {
  try {
    const res = await fetch(`${API_BASE}/gmail/process`, {
      method: 'POST',
    });
    const data = await res.json();
    if (data.success) {
      await loadJobs(); // Refresh the job list
      alert(data.message);
    } else {
      alert('Error: ' + data.message);
    }
  } catch (error) {
    alert('Error processing Gmail');
  }
};
```

## How It Works

1. **Authentication**: Uses OAuth2 to securely access your Gmail
2. **Email Search**: Searches for unread emails
3. **Keyword Detection**: Looks for recruiter keywords like:
   - "Your application to..."
   - "Interview invitation"
   - "Online assessment"
   - "Next steps"
4. **Data Extraction**: Parses company names and job titles using regex patterns
5. **Database Storage**: Saves parsed applications to PostgreSQL

## Security Notes

- The `credentials.json` file contains sensitive OAuth client information
- The `token.json` file contains your personal access tokens
- Both files are in `.gitignore` to prevent accidental commits
- Never share these files publicly

## Troubleshooting

- **"Credentials file not found"**: Make sure `credentials.json` is in the `backend/` directory
- **"Invalid credentials"**: Delete `token.json` and re-authenticate
- **"Gmail API not enabled"**: Enable the Gmail API in Google Cloud Console
- **"Quota exceeded"**: Gmail API has daily quotas; the script processes max 50 emails by default

## Next Steps

- Add more sophisticated email parsing patterns
- Implement email marking as read after processing
- Add scheduling to run automatically
- Integrate with Google Calendar for interview scheduling
