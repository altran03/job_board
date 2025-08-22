"""
Gemini API Email Analyzer for Job Application Tracking
Uses Google's Gemini AI to intelligently parse job application emails.
"""
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import google.generativeai as genai
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
                return False
            
            # Calculate threshold date
            threshold_date = datetime.now() - timedelta(days=days_threshold)
            
            # Check if email is recent
            is_recent = parsed_date >= threshold_date
            
            if not is_recent:
                print(f"📧 Email from {parsed_date.strftime('%Y-%m-%d')} is older than {days_threshold} days, skipping AI analysis")
            
            return is_recent
            
        except Exception as e:
            print(f"Error checking email date: {e}")
            return False
    
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
    
    def analyze_job_email(self, subject: str, body: str, from_email: str = '') -> Dict[str, Any]:
        """
        Analyze job application email using Gemini AI.
        
        Args:
            subject: Email subject
            body: Email body text
            from_email: Sender email address
            
        Returns:
            Dict containing extracted job application information
        """
        if not self.is_available:
            print("⚠️  Gemini API not available, falling back to regex parsing")
            return self._fallback_analysis(subject, body, from_email)
        
        # Estimate token usage
        total_text = f"{subject}\n\n{body}"
        estimated_tokens = self.estimate_token_count(total_text)
        
        if estimated_tokens > MAX_TOKENS_PER_REQUEST:
            print(f"⚠️  Email too long ({estimated_tokens} estimated tokens), truncating for Gemini analysis")
            # Truncate body to stay within token limits
            max_chars = MAX_TOKENS_PER_REQUEST * 4
            body = body[:max_chars - len(subject)] + "..."
            total_text = f"{subject}\n\n{body}"
        
        try:
            # Create prompt for Gemini
            prompt = self._create_analysis_prompt(subject, body, from_email)
            
            # Call Gemini API
            response = self.model.generate_content(prompt)
            
            if response.text:
                # Parse Gemini response
                parsed_data = self._parse_gemini_response(response.text)
                if parsed_data:
                    print(f"✅ Gemini analysis successful: {parsed_data.get('company', 'Unknown')} - {parsed_data.get('title', 'Unknown')}")
                    return parsed_data
                else:
                    print("⚠️  Failed to parse Gemini response, using fallback")
                    return self._fallback_analysis(subject, body, from_email)
            else:
                print("⚠️  Empty response from Gemini, using fallback")
                return self._fallback_analysis(subject, body, from_email)
                
        except Exception as e:
            print(f"❌ Gemini API error: {e}, using fallback analysis")
            return self._fallback_analysis(subject, body, from_email)
    
    def _create_analysis_prompt(self, subject: str, body: str, from_email: str) -> str:
        """Create the prompt for Gemini analysis."""
        return f"""
You are an expert AI assistant that analyzes job application emails. Your task is to extract key information with high accuracy.

Email Subject: {subject}
From: {from_email}
Body: {body}

Please analyze this email and extract the following information:

1. **Is this a job application related email?** (yes/no)
   - Look for keywords like: application, applied, position, role, job, career, hiring, recruiting
   - Consider both subject and body content

2. **Company name** (if found)
   - Extract the actual company name, not generic terms
   - Look for company names in: sender email domain, email body, subject line
   - Examples: "Google", "Microsoft", "Amazon", "Meta", "Apple"
   - Avoid: "recruiting team", "talent acquisition", "HR department"

3. **Job title/position** (if found)
   - Extract the specific job title or role
   - Look for titles like: "Software Engineer", "Data Scientist", "Product Manager", etc.
   - Include level if mentioned: "Senior", "Junior", "Intern", "Lead"
   - Examples: "Software Engineer Intern", "Senior Data Scientist", "Product Manager"
   - Include the role or position if given for example "(Media Engine), (Live Services)"

4. **Application status** (if found)
   - Current status: "applied", "interview", "offer", "rejection", "assessment", "screening"
   - Look for action words: "received", "reviewing", "invited", "scheduled", "accepted"

5. **Confidence level** (high/medium/low)
   - High: Clear company name and job title
   - Medium: Some information clear, some unclear
   - Low: Limited or unclear information

Return your response in this exact JSON format:
{{
    "is_job_email": true/false,
    "company": "Company Name or null",
    "title": "Job Title or null",
    "status": "Application Status or null",
    "confidence": "high/medium/low",
    "reasoning": "Brief explanation of your analysis and what you found"
}}

**Important Rules:**
- Only return valid JSON
- Use null for fields you cannot determine
- Be specific with company names (avoid generic terms)
- Include full job titles when possible
- If unsure, use lower confidence levels
"""
    
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
