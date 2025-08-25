"""
Gemini AI Integration for Email Analysis
Uses Google's Gemini AI to intelligently parse job application emails.
"""

import os
import re
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from .db import SessionLocal
from .models import JobApplication
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Gemini model configuration
MODEL_NAME = "gemini-1.5-flash"  # Free tier model
MAX_TOKENS_PER_REQUEST = 1000  # Conservative limit for free tier

class GeminiEmailAnalyzer:
    """
    Analyzes job application emails using Gemini AI API.
    Implements time-based filtering and token usage control.
    """
    
    def __init__(self):
        """Initialize the Gemini analyzer."""
        self.model = None
        self.is_available = False
        
        if GEMINI_API_KEY:
            try:
                self.model = genai.GenerativeModel(MODEL_NAME)
                self.is_available = True
                print("✅ Gemini API initialized successfully")
            except Exception as e:
                print(f"❌ Failed to initialize Gemini API: {e}")
                self.is_available = False
        else:
            print("⚠️  GEMINI_API_KEY not found in environment variables")
            self.is_available = False
    
    def is_email_recent(self, email_date: str, days_threshold: int = 7) -> bool:
        """
        Check if email is within the specified time threshold.
        
        Args:
            email_date: Email date string
            days_threshold: Number of days to look back (default: 7)
            
        Returns:
            bool: True if email is recent enough to analyze
        """
        try:
            # Parse email date
            parsed_date = self._parse_email_date(email_date)
            if not parsed_date:
                print(f"⚠️  Could not parse email date: {email_date}")
                return True  # If we can't parse the date, assume it's recent enough
            
            # Calculate threshold date (make it timezone-aware)
            threshold_date = datetime.now().replace(tzinfo=None) - timedelta(days=days_threshold)
            
            # Make parsed date timezone-naive for comparison
            if parsed_date.tzinfo:
                parsed_date = parsed_date.replace(tzinfo=None)
            
            # Check if email is recent
            is_recent = parsed_date >= threshold_date
            
            if not is_recent:
                print(f"📧 Email from {parsed_date.strftime('%Y-%m-%d')} is older than {days_threshold} days, skipping AI analysis")
            else:
                print(f"📧 Email from {parsed_date.strftime('%Y-%m-%d')} is within {days_threshold} days, proceeding with analysis")
            
            return is_recent
            
        except Exception as e:
            print(f"Error checking email date: {e}")
            return True  # If there's an error, assume it's recent enough to analyze
    
    def _parse_email_date(self, email_date: str) -> Optional[datetime]:
        """Parse email date string to datetime object."""
        try:
            # Common email date formats
            formats = [
                '%a, %d %b %Y %H:%M:%S %z',  # "Wed, 20 Aug 2025 11:20:00 +0000"
                '%d %b %Y %H:%M:%S %z',      # "20 Aug 2025 11:20:00 +0000"
                '%Y-%m-%d %H:%M:%S %z',      # "2025-08-20 11:20:00 +0000"
                '%a, %d %b %Y %H:%M:%S',    # "Wed, 20 Aug 2025 11:20:00"
                '%d %b %Y %H:%M:%S',         # "20 Aug 2025 11:20:00"
                '%Y-%m-%d',                  # "2025-08-20"
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(email_date, fmt)
                except ValueError:
                    continue
            
            return None
            
        except Exception as e:
            print(f"Error parsing date '{email_date}': {e}")
            return None
    
    def estimate_token_count(self, text: str) -> int:
        """
        Estimate token count for text (rough approximation).
        Gemini uses a similar tokenization to GPT models.
        """
        # Rough approximation: 1 token ≈ 4 characters for English text
        return len(text) // 4
    
    def _is_follow_up_email(self, subject: str, body: str) -> bool:
        """
        Detect if this is a follow-up email, but don't block it entirely.
        Returns True if it's a follow-up, but we'll still parse it for job data.
        """
        text = f"{subject} {body}".lower()
        
        # Strong indicators of follow-up emails
        follow_up_indicators = [
            'follow up', 'follow-up', 'reminder', 'update', 'next steps',
            'interview schedule', 'assessment reminder', 'deadline reminder',
            'application status', 'next phase', 'moving forward', 'scheduled',
            'confirmation', 'confirming', 'reconfirm', 'reschedule',
            'deadline approaching', 'time sensitive', 'urgent reminder'
        ]
        
        # Check for follow-up patterns
        for indicator in follow_up_indicators:
            if indicator in text:
                return True
        
        # Check for email threading indicators
        threading_patterns = [
            r're:\s*',  # Re: subject
            r'fw:\s*',  # Fwd: subject
            r'fwd:\s*',  # Forward subject
            r'\[thread\]',  # Thread indicators
            r'conversation',  # Conversation references
        ]
        
        for pattern in threading_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Check for very short subjects that often indicate follow-ups
        if len(subject.strip()) < 25 and any(word in text for word in ['reminder', 'update', 'next', 'schedule']):
            return True
        
        return False

    def analyze_job_email(self, subject: str, body: str, from_email: str, email_date: str = None) -> Dict[str, Any]:
        """
        Analyze job application email using Gemini AI.
        Now with improved follow-up detection and title parsing.
        """
        try:
            # First, check if this is a follow-up email using pattern matching
            # But don't block it - we'll still parse it for job data
            is_follow_up = self._is_follow_up_email(subject, body)
            
            # Check if email is too old based on threshold
            if email_date and not self.is_email_recent(email_date, days_threshold=days_threshold):
                return {
                    'is_job_email': False,
                    'company': None,
                    'title': None,
                    'status': None,
                    'confidence': 'high',
                    'reasoning': f'Email is older than {days_threshold} days (received: {email_date})',
                    'analysis_method': 'time_filtered'
                }
            
            # Create the analysis prompt
            prompt = self._create_analysis_prompt(subject, body, from_email)
            
            # Estimate token count and truncate if necessary
            estimated_tokens = self.estimate_token_count(prompt)
            if estimated_tokens > 30000:  # Gemini 1.5 Flash limit
                # Truncate body text to fit within token limit
                max_body_length = 1500  # Conservative estimate
                body = body[:max_body_length] + "..."
                prompt = self._create_analysis_prompt(subject, body, from_email)
                print(f"⚠️  Truncated email body to fit token limit (estimated: {estimated_tokens})")
            
            # Generate content using Gemini
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                # Parse the AI response
                parsed_result = self._parse_gemini_response(response.text)
                if parsed_result:
                    # Add analysis method and follow-up flag
                    parsed_result['analysis_method'] = 'gemini_ai'
                    parsed_result['is_follow_up'] = is_follow_up
                    
                    # If it's a follow-up email, we still want to parse it for job data
                    # but mark it appropriately so duplicate detection can handle it
                    if is_follow_up:
                        parsed_result['reasoning'] = f"Follow-up email: {parsed_result.get('reasoning', '')}"
                    
                    return parsed_result
            
            # Fallback to regex parsing if Gemini fails
            print("⚠️  Gemini analysis failed, falling back to regex parsing")
            fallback_result = self._fallback_analysis(subject, body, from_email)
            if fallback_result:
                fallback_result['is_follow_up'] = is_follow_up
            return fallback_result
            
        except Exception as e:
            print(f"Error in Gemini analysis: {e}")
            # Fallback to regex parsing
            fallback_result = self._fallback_analysis(subject, body, from_email)
            if fallback_result:
                fallback_result['is_follow_up'] = self._is_follow_up_email(subject, body)
            return fallback_result
    
    def _create_analysis_prompt(self, subject: str, body: str, from_email: str) -> str:
        """
        Create a detailed prompt for Gemini AI to analyze job application emails.
        """
        prompt = f"""
You are an expert at analyzing job application emails. Your task is to determine if an email is a job application and extract key information.

**Email to analyze:**
Subject: {subject}
From: {from_email}
Body: {body[:2000]}...

**IMPORTANT RULES:**

1. **Email Classification:**
   - Mark as job application if it contains ANY job-related information
   - This includes: application confirmations, interview invitations, follow-up emails, reminders, status updates
   - Follow-up emails are still job-related and should be parsed for company/title data
   - **BE PERMISSIVE**: If you see words like "apply", "application", "intern", "career", "job", "position", "role", "hiring", "recruiting" - mark it as a job email
   - When in doubt, mark as job email (let the system handle duplicates)

2. **Company Name Extraction:**
   - Extract ONLY the actual company name, not email domains or generic text
   - Avoid extracting: "The IBM Talent Acquisition", "your contact information is accurate", "we were paying her", "may arise", "your own time i", "your request", "our"
   - Look for patterns like: "Thank you for applying to [COMPANY]", "Application received from [COMPANY]", "Your application to [COMPANY]"
   - If company name is unclear, use the email domain as fallback
   - **IMPORTANT**: For TikTok emails, extract "TikTok" as the company name

3. **Job Title Extraction:**
   - Extract the ACTUAL job title, not email body text mixed in
   - Avoid titles like: "Software Engineer Intern (The IBM Talent Acquisition)", "Software Engineer Intern (depending on the)", "Software Engineer Intern (thank you for applying to the)"
   - Look for specific roles in parentheses like: "Software Engineer Intern (Media Engine)", "Software Engineer Intern (Live Services)"
   - Include the role or position if given for example "(Media Engine), (Live Services)"
   - If no specific role found, use generic titles like "Software Engineer Intern" or "Software Engineer"
   - **IMPORTANT**: For TikTok emails with "Media Engine" or "Live Service", extract the full title

4. **Follow-up Email Handling:**
   - Follow-up emails (reminders, updates, next steps) are still job-related
   - Parse them for company and title information
   - The system will handle duplicates automatically

**Output Format (JSON only):**
{{
    "is_job_email": true/false,
    "company": "Company Name or null",
    "title": "Job Title or null", 
    "status": "Applied/Interview/Assessment/Offer/Rejected or null",
    "confidence": "high/medium/low",
    "reasoning": "Brief explanation of your analysis"
}}

**Examples of what to extract:**
- "Thank you for applying to TikTok" → company: "TikTok", title: "Software Engineer Intern"
- "Software Engineer Intern (Media Engine)" → title: "Software Engineer Intern (Media Engine)"
- "Application received from Roblox" → company: "Roblox", title: "Software Engineer Intern"

**Examples of what to avoid:**
- "Software Engineer Intern (The IBM Talent Acquisition)" → title: "Software Engineer Intern" (remove the parenthetical text)
- Follow-up emails → is_job_email: false
- Generic text like "your contact information is accurate" → company: null

Analyze this email and provide your response in the exact JSON format above.
"""
        return prompt
    
    def _parse_gemini_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse Gemini's response into structured data."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                print(f"❌ No JSON found in Gemini response: {response_text[:100]}...")
                return None
            
            json_str = json_match.group(0)
            
            # Parse JSON
            import json
            data = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['is_job_email', 'company', 'title', 'status', 'confidence']
            if not all(field in data for field in required_fields):
                print(f"❌ Missing required fields in Gemini response: {data}")
                return None
            
            # Clean and validate data
            cleaned_data = {
                'is_job_email': bool(data.get('is_job_email', False)),
                'company': self._clean_company_name(data.get('company')),
                'title': self._clean_job_title(data.get('title')),
                'status': data.get('status'),
                'confidence': data.get('confidence', 'low'),
                'reasoning': data.get('reasoning', ''),
                'analysis_method': 'gemini_ai'
            }
            
            return cleaned_data
            
        except Exception as e:
            print(f"❌ Error parsing Gemini response: {e}")
            return None
    
    def _clean_company_name(self, company: str) -> Optional[str]:
        """Clean and validate company name."""
        if not company or company.lower() in ['null', 'none', 'unknown']:
            return None
        
        # Remove common unwanted prefixes/suffixes
        cleaned = company.strip()
        cleaned = re.sub(r'^(the\s+|a\s+|an\s+)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'(\s+team|\s+department|\s+group|\s+recruiting|\s+talent|\s+hiring|\s+hr)$', '', cleaned, flags=re.IGNORECASE)
        
        # Must be meaningful
        if len(cleaned) < 2 or len(cleaned) > 100:
            return None
        
        return cleaned
    
    def _clean_job_title(self, title: str) -> Optional[str]:
        """Clean and validate job title."""
        if not title or title.lower() in ['null', 'none', 'unknown']:
            return None
        
        # Clean up title
        cleaned = title.strip()
        if len(cleaned) < 2 or len(cleaned) > 100:
            return None
        
        return cleaned
    
    def _fallback_analysis(self, subject: str, body: str, from_email: str = '') -> Dict[str, Any]:
        """Fallback analysis using regex patterns when Gemini is unavailable."""
        from .email_parser import (
            is_job_application_email, 
            extract_company_name, 
            extract_job_title
        )
        
        is_job_email = is_job_application_email(subject, body)
        company = extract_company_name(subject, body, from_email)
        title = extract_job_title(subject, body)
        
        return {
            'is_job_email': is_job_email,
            'company': company,
            'title': title,
            'status': 'applied' if is_job_email else None,
            'confidence': 'low',
            'reasoning': 'Fallback regex analysis used',
            'analysis_method': 'regex_fallback'
        }
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current API usage statistics."""
        return {
            'api_available': self.is_available,
            'model_name': MODEL_NAME,
            'max_tokens_per_request': MAX_TOKENS_PER_REQUEST,
            'api_key_configured': bool(GEMINI_API_KEY)
        }


# Global analyzer instance
gemini_analyzer = GeminiEmailAnalyzer()


def analyze_email_with_gemini(subject: str, body: str, from_email: str = '', 
                            email_date: str = '', days_threshold: int = 7) -> Dict[str, Any]:
    """
    Convenience function to analyze an email with Gemini AI.
    
    Args:
        subject: Email subject
        body: Email body
        from_email: Sender email
        email_date: Email date string
        days_threshold: Days to look back (default: 7)
        
    Returns:
        Analysis results
    """
    # Check if email is recent enough
    if email_date and not gemini_analyzer.is_email_recent(email_date, days_threshold):
        return {
            'is_job_email': False,
            'company': None,
            'title': None,
            'status': None,
            'confidence': 'low',
            'reasoning': f'Email older than {days_threshold} days, skipped AI analysis',
            'analysis_method': 'time_filtered',
            'skipped_reason': 'too_old'
        }
    
    # Analyze with Gemini
    return gemini_analyzer.analyze_job_email(subject, body, from_email)


def is_gemini_available() -> bool:
    """Check if Gemini API is available."""
    return gemini_analyzer.is_available
