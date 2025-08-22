# Gemini AI Integration Setup Guide

This guide explains how to set up Google's Gemini AI API for intelligent email parsing in your Smart Job Tracker.

## 🚀 What is Gemini AI?

Gemini is Google's latest AI model that provides:
- **Free Tier**: Generous usage limits with Gemini 1.5 Flash
- **Intelligent Parsing**: Better understanding of job application emails
- **Fallback Support**: Automatically falls back to regex parsing if unavailable
- **Token Control**: Built-in limits to prevent excessive API usage

## 🔑 Getting Your API Key

### Step 1: Visit Google AI Studio
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"

### Step 2: Copy Your Key
- Your API key will look like: `AIzaSyC...`
- Copy it to your clipboard

### Step 3: Configure Environment
Create a `.env` file in your `backend/` directory:

```bash
# backend/.env
GEMINI_API_KEY=your_actual_api_key_here
```

## ⚙️ Configuration Options

### Time-Based Filtering
Control which emails are analyzed to manage token usage:

```python
# Only analyze emails from the past 7 days (default)
process_gmail_applications(days_threshold=7)

# Only analyze emails from the past 3 days (conservative)
process_gmail_applications(days_threshold=3)

# Analyze emails from the past 30 days (more comprehensive)
process_gmail_applications(days_threshold=30)
```

### AI Analysis Control
Enable/disable Gemini AI analysis:

```python
# Use Gemini AI (default)
process_gmail_applications(use_gemini=True)

# Use regex parsing only (fallback)
process_gmail_applications(use_gemini=False)
```

## 📊 API Endpoints

### Basic Processing
```bash
POST /gmail/process
# Uses default settings: 7 days, Gemini enabled, max 50 emails
```

### Advanced Processing
```bash
POST /gmail/process-advanced?days_threshold=3&use_gemini=true&max_results=25
# Customize all parameters
```

### Gemini Status
```bash
GET /gemini/status
# Check API availability and configuration
```

### Test Analysis
```bash
POST /gemini/test?subject="Thank you for applying"&body="We received your application..."
# Test Gemini analysis on sample content
```

## 💰 Cost Control

### Free Tier Limits
- **Gemini 1.5 Flash**: Free with generous limits
- **Token Estimation**: Built-in to prevent excessive usage
- **Time Filtering**: Only analyze recent emails
- **Automatic Fallback**: Regex parsing when AI unavailable

### Token Usage Optimization
```python
# Conservative approach (3 days, max 25 emails)
process_gmail_applications(days_threshold=3, max_results=25)

# Balanced approach (7 days, max 50 emails) - DEFAULT
process_gmail_applications(days_threshold=7, max_results=50)

# Comprehensive approach (30 days, max 100 emails)
process_gmail_applications(days_threshold=30, max_results=100)
```

## 🔧 Installation

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Set Environment Variable
```bash
export GEMINI_API_KEY="your_api_key_here"
# Or add to .env file
```

### 3. Restart Backend
```bash
docker compose restart backend
```

## 🧪 Testing

### Test Gemini Availability
```bash
curl http://localhost:8000/gemini/status
```

### Test Email Analysis
```bash
curl -X POST "http://localhost:8000/gemini/test" \
  -d "subject=Thank you for applying to Google" \
  -d "body=We have received your application for Software Engineer Intern..."
```

## 🚨 Troubleshooting

### Common Issues

#### 1. "Gemini API not available"
- Check if `GEMINI_API_KEY` is set
- Verify API key is valid
- Check internet connection

#### 2. "Failed to initialize Gemini API"
- Verify API key format
- Check if you've exceeded free tier limits
- Try regenerating API key

#### 3. "Email too long, truncating"
- This is normal for long emails
- System automatically truncates to stay within token limits
- Consider reducing `max_results` parameter

### Fallback Behavior
If Gemini is unavailable, the system automatically:
1. Uses regex-based parsing
2. Logs the fallback behavior
3. Continues processing emails
4. Maintains full functionality

## 📈 Monitoring

### Check Processing Results
```bash
curl http://localhost:8000/gmail/process-advanced?days_threshold=7
```

### Monitor Token Usage
- Check response headers for token estimates
- Use time filtering to control usage
- Monitor API quotas in Google AI Studio

## 🔒 Security Notes

- **Never commit** your API key to version control
- **Use environment variables** for configuration
- **Rotate keys** if compromised
- **Monitor usage** to prevent abuse

## 📚 Additional Resources

- [Gemini API Documentation](https://ai.google.dev/docs)
- [Google AI Studio](https://makersuite.google.com/)
- [Free Tier Limits](https://ai.google.dev/pricing)
- [Token Usage Guide](https://ai.google.dev/docs/gemini_api_quickstart)

## 🆘 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify your API key configuration
3. Test with the `/gemini/status` endpoint
4. Check backend logs for detailed error messages

The system is designed to be robust and will continue working even if Gemini is unavailable!
