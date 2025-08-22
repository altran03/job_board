"""
Email Parser for Job Application Tracking
Fetches Gmail emails and parses them for job application data.
"""
import re
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from email.mime.text import MIMEText
import base64

from googleapiclient.errors import HttpError

from .gmail_auth import get_gmail_service
from .models import JobApplication
from .db import SessionLocal


# Direct patterns to extract company and job info from subject lines
APPLICATION_PATTERNS = [
    # "Thank you for applying to [COMPANY]"
    r'[Tt]hank you for applying to\s+([A-Z][a-zA-Z\s&]+?)(?:\s*!|\s*\.|\s*$)',
    # "Application received from [COMPANY]"
    r'[Aa]pplication received from\s+([A-Z][a-zA-Z\s&]+?)(?:\s*!|\s*\.|\s*$)',
    # "Your application to [COMPANY]"
    r'[Yy]our application to\s+([A-Z][a-zA-Z\s&]+?)(?:\s*!|\s*\.|\s*$)',
    # "Application for [COMPANY]"
    r'[Aa]pplication for\s+([A-Z][a-zA-Z\s&]+?)(?:\s*!|\s*\.|\s*$)',
]

# Keywords that indicate job application emails
RECRUITER_KEYWORDS = [
    # Application confirmations
    'thank you for applying',
    'thank you for your application',
    'we have received your application',
    'application received',
    'application submitted',
    'application confirmation',
    'your application has been received',
    'we received your application',
    
    # Interview related
    'interview invitation',
    'interview scheduling',
    'interview request',
    'technical interview',
    'next round',
    'final round',
    
    # Assessment related
    'online assessment',
    'coding challenge',
    'assessment invitation',
    'technical assessment',
    
    # Status updates
    'application status',
    'next steps',
    'application review',
    'hiring team will review',
    'talent acquisition team',
    
    # Offer related
    'offer letter',
    'job offer',
    'offer details',
    
    # General application keywords
    'your application to',
    'application for',
    'applied to',
    'careers@',
    'recruiting@',
    'talent@',
    'hiring@'
]

# Job title patterns - expanded to catch more variations
TITLE_PATTERNS = [
    # Software Engineering
    r'Software Engineer',
    r'SWE',
    r'Software Developer',
    r'Developer',
    r'Programmer',
    r'Full Stack',
    r'Frontend',
    r'Backend',
    r'DevOps',
    r'Data Engineer',
    r'Machine Learning',
    r'ML Engineer',
    r'AI Engineer',
    r'Systems Engineer',
    r'Intern',
    
    # Product roles
    r'Product Manager',
    r'PM',
    r'Product Owner',
    
    # Internships and entry level
    r'Intern',
    r'Internship',
    r'Graduate',
    r'Entry Level',
    r'New Grad',
    r'Recent Graduate',
    
    # Specific roles from the emails
    r'Software Engineer Intern',
    r'Media Engine'
]


def is_job_application_email(subject: str, body: str) -> bool:
    """
    Check if email is likely a job application related email.
    """
    subject_lower = subject.lower()
    body_lower = body.lower()
    
    # Check for direct application patterns first
    for pattern in APPLICATION_PATTERNS:
        if re.search(pattern, subject, re.IGNORECASE):
            return True
    
    # Check for recruiter keywords in subject or body
    for keyword in RECRUITER_KEYWORDS:
        if keyword.lower() in subject_lower or keyword.lower() in body_lower:
            return True
    
    # Check for career-related email domains
    career_domains = ['careers.', 'recruiting.', 'talent.', 'hiring.']
    for domain in career_domains:
        if domain in subject_lower or domain in body_lower:
            return True
    
    return False


def extract_company_name(subject: str, body: str) -> Optional[str]:
    """
    Extract company name from email subject and body.
    """
    text = f"{subject} {body}"
    
    # Try direct application patterns first (most reliable)
    for pattern in APPLICATION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            company = match.group(1).strip()
            # Clean up common words
            company = re.sub(r'\b(recruiting|team|department|hr|human\s+resources|talent|acquisition)\b', '', company, flags=re.IGNORECASE)
            company = company.strip()
            if len(company) > 2:  # Avoid very short matches
                return company
    
    # Try to extract from email domain as fallback
    email_match = re.search(r'@([a-zA-Z]+)\.', text)
    if email_match:
        domain = email_match.group(1)
        # Convert common domains to company names
        domain_to_company = {
            'ixl': 'IXL Learning',
            'tiktok': 'TikTok',
            'google': 'Google',
            'meta': 'Meta',
            'microsoft': 'Microsoft',
            'apple': 'Apple',
            'amazon': 'Amazon',
            'netflix': 'Netflix',
            'uber': 'Uber',
            'lyft': 'Lyft',
            'airbnb': 'Airbnb',
            'stripe': 'Stripe',
            'square': 'Square',
            'salesforce': 'Salesforce',
            'adobe': 'Adobe',
            'oracle': 'Oracle',
            'intel': 'Intel',
            'nvidia': 'NVIDIA',
            'amd': 'AMD',
            'cisco': 'Cisco'
        }
        return domain_to_company.get(domain.lower(), domain.title())
    
    return None


def extract_job_title(subject: str, body: str) -> Optional[str]:
    """
    Extract job title from email subject and body.
    """
    text = f"{subject} {body}"
    
    for pattern in TITLE_PATTERNS:
        if pattern.lower() in text.lower():
            return pattern
    
    return None


def parse_email_date(email_date: str) -> Optional[date]:
    """
    Parse email date string to date object.
    """
    try:
        # Try common email date formats
        for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%d %b %Y %H:%M:%S %z', '%Y-%m-%d']:
            try:
                dt = datetime.strptime(email_date, fmt)
                return dt.date()
            except ValueError:
                continue
    except Exception:
        pass
    
    return None


def fetch_and_parse_emails(max_results: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch unread emails from Gmail and parse them for job applications.
    Returns list of parsed job application data.
    """
    service = get_gmail_service()
    if not service:
        print("Failed to get Gmail service")
        return []
    
    try:
        # Search for unread emails
        query = 'is:unread'
        results = service.users().messages().list(
            userId='me', 
            q=query, 
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        parsed_applications = []
        
        for message in messages:
            try:
                msg = service.users().messages().get(
                    userId='me', 
                    id=message['id'],
                    format='full'
                ).execute()
                
                # Extract email data
                headers = msg['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                from_header = next((h['value'] for h in headers if h['name'] == 'From'), '')
                date_header = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                
                # Get email body
                body = ''
                if 'parts' in msg['payload']:
                    for part in msg['payload']['parts']:
                        if part['mimeType'] == 'text/plain':
                            body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                            break
                elif 'body' in msg['payload'] and 'data' in msg['payload']['body']:
                    body = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode('utf-8')
                
                # Check if it's a job application email
                if is_job_application_email(subject, body):
                    company = extract_company_name(subject, body)
                    title = extract_job_title(subject, body)
                    email_date = parse_email_date(date_header)
                    
                    if company or title:  # At least one should be extracted
                        parsed_applications.append({
                            'email_id': message['id'],
                            'subject': subject,
                            'from': from_header,
                            'date': email_date or date.today(),
                            'company': company or 'Unknown Company',
                            'title': title or 'Software Engineer',
                            'body_preview': body[:200] + '...' if len(body) > 200 else body
                        })
                        
            except Exception as e:
                print(f"Error parsing email {message['id']}: {e}")
                continue
        
        return parsed_applications
        
    except HttpError as error:
        print(f"Error fetching emails: {error}")
        return []


def save_parsed_applications(applications: List[Dict[str, Any]]) -> int:
    """
    Save parsed job applications to database.
    Returns number of applications saved.
    """
    if not applications:
        return 0
    
    db = SessionLocal()
    saved_count = 0
    
    try:
        for app_data in applications:
            # Check if application already exists (by title, company, and date)
            existing = db.query(JobApplication).filter(
                JobApplication.title == app_data['title'],
                JobApplication.company == app_data['company'],
                JobApplication.date_applied == app_data['date']
            ).first()
            
            if not existing:
                job_app = JobApplication(
                    title=app_data['title'],
                    company=app_data['company'],
                    date_applied=app_data['date']
                )
                db.add(job_app)
                saved_count += 1
        
        db.commit()
        print(f"Saved {saved_count} new job applications")
        
    except Exception as e:
        print(f"Error saving applications: {e}")
        db.rollback()
    finally:
        db.close()
    
    return saved_count


def process_gmail_applications() -> Dict[str, Any]:
    """
    Main function to process Gmail for job applications.
    Returns summary of processing results.
    """
    print("Fetching and parsing Gmail for job applications...")
    
    # Fetch and parse emails
    applications = fetch_and_parse_emails(max_results=50)
    print(f"Found {len(applications)} potential job application emails")
    
    # Save to database
    saved_count = save_parsed_applications(applications)
    
    return {
        'emails_processed': len(applications),
        'applications_saved': saved_count,
        'applications': applications
    }


if __name__ == "__main__":
    # Test email processing
    results = process_gmail_applications()
    print(f"Processing complete: {results}")
