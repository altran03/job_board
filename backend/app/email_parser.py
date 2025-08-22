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
    'thank you for applying to',
    
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
    'assessments invitation',
    
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
    r'Media Engine',
    r'Live Service'
]

# Company name mapping from email domains and common variations
COMPANY_MAPPING = {
    'ixl': 'IXL Learning',
    'tiktok': 'TikTok',
    'roblox': 'Roblox',
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

def is_valid_company_name(company_name: str) -> bool:
    """
    Check if a company name is valid using general patterns, not specific names.
    """
    if not company_name or len(company_name.strip()) < 3:
        return False
    
    company_name = company_name.strip()
    
    # Must contain at least one letter
    if not re.search(r'[a-zA-Z]', company_name):
        return False
    
    # Must not be too long (likely not a company name)
    if len(company_name) > 100:
        return False
    
    # Must not be all numbers or special characters
    if re.match(r'^[\d\s\W]+$', company_name):
        return False
    
    # Must not be email addresses
    if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', company_name):
        return False
    
    # Must not be URLs
    if re.match(r'^https?://|^www\.', company_name):
        return False
    
    # Must not be generic pronouns/words that indicate it's not a company name
    generic_words = [
        'we', 'you', 'your', 'our', 'their', 'they', 'them',
        'this', 'that', 'these', 'those', 'here', 'there',
        'should', 'would', 'could', 'will', 'can', 'may', 'might', 'must', 'need', 'want',
        'like', 'love', 'hate', 'please', 'thank', 'thanks', 'sorry',
        'hello', 'hi', 'hey', 'goodbye', 'bye', 'click', 'link', 'website',
        'message', 'notification', 'update', 'confirm', 'verify'
    ]
    
    # Check if the entire company name is just generic words
    company_lower = company_name.lower()
    if company_lower in generic_words:
        return False
    
    # Check if it's mostly generic words (more than 70% of words are generic)
    words = company_lower.split()
    if len(words) > 0:
        generic_count = sum(1 for word in words if word in generic_words)
        if generic_count / len(words) > 0.7:
            return False
    
    # Must not be sentence fragments that indicate it's not a company name
    sentence_fragments = [
        r'^we\s+were\s+',  # "we were paying her"
        r'^your\s+contact\s+information\s+is\s+',  # "your contact information is accurate"
        r'^you\s+should\s+have\s+received\s+a\s+message\s+from\s+our\s*$',  # "you should have received a message from our"
        r'^may\s+arise\s*$',  # "may arise"
        r'^your\s+own\s+time\s+i\s*$',  # "your own time i"
        r'^your\s+request\s*$',  # "your request"
        r'^our\s*$',  # "our"
    ]
    
    for pattern in sentence_fragments:
        if re.search(pattern, company_lower):
            return False
    
    # Must not be too short (less than 3 characters)
    if len(company_name) < 3:
        return False
    
    # Must start with a letter (most company names do)
    if not re.match(r'^[a-zA-Z]', company_name):
        return False
    
    return True


def clean_company_name(company_name: str) -> Optional[str]:
    """
    Clean and validate a company name, returning None if invalid.
    Uses general patterns rather than specific company names.
    """
    if not company_name:
        return None
    
    # Clean up the company name
    cleaned = company_name.strip()
    
    # Remove common prefixes that don't affect company identity
    cleaned = re.sub(r'^(the\s+|a\s+|an\s+)', '', cleaned, flags=re.IGNORECASE)
    
    # Remove common suffixes that don't affect company identity
    cleaned = re.sub(r'(\s+team|\s+department|\s+group|\s+division|\s+unit|\s+section|\s+recruiting|\s+talent|\s+hiring|\s+hr|\s+human\s+resources)$', '', cleaned, flags=re.IGNORECASE)
    
    # Check if it's valid
    if is_valid_company_name(cleaned):
        return cleaned
    
    return None


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
    
    # Check for specific company patterns in the emails you showed
    specific_patterns = [
        r'we have received your application',
        r'we received your application',
        r'your application for the',
        r'role within',
        r'early career talent',
        r'rob assessments invitation',
        r'thrilled to invite you to the next step',
        r'next step of the recruiting process'
    ]
    
    for pattern in specific_patterns:
        if re.search(pattern, body_lower):
            return True
    
    return False


def extract_company_name(subject: str, body: str, from_email: str = '') -> Optional[str]:
    """
    Extract company name from email subject, body, and sender email.
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
                cleaned_company = clean_company_name(company)
                if cleaned_company:
                    return cleaned_company
    
    # Try to extract from email domain
    email_match = re.search(r'@([a-zA-Z]+)\.', from_email)
    if email_match:
        domain = email_match.group(1).lower()
        if domain in COMPANY_MAPPING:
            return COMPANY_MAPPING[domain]
    
    # Try to extract from email domain in body text as fallback
    email_match = re.search(r'@([a-zA-Z]+)\.', text)
    if email_match:
        domain = email_match.group(1).lower()
        if domain in COMPANY_MAPPING:
            return COMPANY_MAPPING[domain]
    
    # Try to extract company names from common patterns in the text
    company_patterns = [
        r'from\s+([A-Z][a-zA-Z\s&]+?)(?:\s*!|\s*\.|\s*$)',
        r'at\s+([A-Z][a-zA-Z\s&]+?)(?:\s*!|\s*\.|\s*$)',
        r'within\s+([A-Z][a-zA-Z\s&]+?)(?:\s*!|\s*\.|\s*$)',
        r'([A-Z][a-zA-Z\s&]+?)\s+team',
        r'([A-Z][a-zA-Z\s&]+?)\s+recruiting',
        r'([A-Z][a-zA-Z\s&]+?)\s+talent',
    ]
    
    for pattern in company_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            company = match.group(1).strip()
            # Clean up common words
            company = re.sub(r'\b(recruiting|team|department|hr|human\s+resources|talent|acquisition|early\s+career)\b', '', company, flags=re.IGNORECASE)
            company = company.strip()
            if len(company) > 2:  # Avoid very short matches
                cleaned_company = clean_company_name(company)
                if cleaned_company:
                    return cleaned_company
    
    return None


def extract_job_title(subject: str, body: str) -> Optional[str]:
    """
    Extract job title from email subject and body.
    Prioritizes specific roles over generic titles.
    """
    text = f"{subject} {body}"
    
    # First, try to find specific role patterns in the text
    specific_role_patterns = [
        # Look for specific role descriptions
        r'Software Engineer\s+(?:Intern\s+)?\(([^)]+)\)',  # "Software Engineer Intern (Media Engine)"
        r'Software Engineer\s+(?:Intern\s+)?-?\s*([^-]+)',  # "Software Engineer Intern - Media Engine"
        r'role\s+within\s+([^.!?]+)',  # "role within Media Engine"
        r'position\s+as\s+([^.!?]+)',  # "position as Media Engine"
        r'([A-Z][a-zA-Z\s&]+)\s+role',  # "Media Engine role"
        r'([A-Z][a-zA-Z\s&]+)\s+position',  # "Media Engine position"
        r'([A-Z][a-zA-Z\s&]+)\s+team',  # "Media Engine team"
        r'([A-Z][a-zA-Z\s&]+)\s+department',  # "Media Engine department"
    ]
    
    for pattern in specific_role_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            specific_role = match.group(1).strip()
            if len(specific_role) > 2 and is_valid_role(specific_role):
                # Clean and truncate the role to reasonable length
                cleaned_role = clean_role_text(specific_role)
                if cleaned_role:
                    return f"Software Engineer Intern ({cleaned_role})"
    
    # Look for specific role mentions in the text
    role_keywords = [
        'Media Engine', 'Live Service', 'Backend', 'Frontend', 'Full Stack',
        'Machine Learning', 'Data Science', 'DevOps', 'Cloud', 'Security',
        'Mobile', 'Web', 'API', 'Infrastructure', 'Platform', 'Systems'
    ]
    
    for role in role_keywords:
        if role.lower() in text.lower():
            return f"Software Engineer Intern ({role})"
    
    # Fall back to generic titles if no specific role found
    for pattern in TITLE_PATTERNS:
        if pattern.lower() in text.lower():
            return pattern
    
    return None


def clean_role_text(role_text: str) -> Optional[str]:
    """
    Clean role text to make it suitable for a job title.
    """
    if not role_text:
        return None
    
    # Remove common unwanted phrases
    unwanted_phrases = [
        r're\s+currently\s+reviewing\s+all\s+applications.*',
        r'will\s+be\s+in\s+touch\s+if.*',
        r'experience\s+and\s+skillset\s+align.*',
        r'requirements\s+of\s+the.*',
        r'role\.\s+We\'re\s+excited.*',
        r'learn\s+more\s+about\s+your\s+skills.*',
        r'As\s+we\s+review\s+your\s+application.*',
        r'what\s+to\s+expect\s+next.*',
        r'If\s+your\s+profile\s+meets.*',
        r'basic\s+qualifications.*',
        r'you\'ll\s+receive.*',
        r'Roblox\s+Hiring\s+Assessments.*',
        r'You\s+can\s+find\s+more\s+information.*',
        r'This\s+email\s+confirms.*',
        r'we\s+received\s+your\s+application.*',
        r'for\s+the\s+.*',
        r'one\s*$',
        r'Web\s*$'
    ]
    
    cleaned = role_text
    for pattern in unwanted_phrases:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    # Clean up extra whitespace and punctuation
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    cleaned = re.sub(r'^\s*[.!?,\s]+\s*', '', cleaned)  # Remove leading punctuation
    cleaned = re.sub(r'\s*[.!?,\s]+\s*$', '', cleaned)  # Remove trailing punctuation
    
    # Truncate if still too long (max 50 characters for role part)
    if len(cleaned) > 50:
        cleaned = cleaned[:47] + "..."
    
    # Must be meaningful
    if len(cleaned) < 3 or cleaned.lower() in ['one', 'web', 'the', 'and', 'or']:
        return None
    
    return cleaned


def is_valid_role(role: str) -> bool:
    """
    Check if a role description is valid.
    """
    if not role or len(role.strip()) < 3:
        return False
    
    # Must not be generic words
    generic_words = ['role', 'position', 'team', 'department', 'company', 'organization']
    if role.lower() in generic_words:
        return False
    
    # Must contain letters
    if not re.search(r'[a-zA-Z]', role):
        return False
    
    # Must not be too long (will be truncated anyway)
    if len(role) > 100:
        return False
    
    return True


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
        # Search for recent emails (not just unread) to catch more job applications
        # Try multiple search queries to catch different types of emails
        search_queries = [
            'is:unread',  # Unread emails
            'from:careers OR from:recruiting OR from:talent OR from:hiring',  # Career emails
            'subject:"thank you for applying" OR subject:"application received" OR subject:"assessment"',  # Specific subjects
            'after:2025/08/20'  # Recent emails (last few days)
        ]
        
        all_messages = []
        for query in search_queries:
            try:
                print(f"Searching with query: {query}")
                results = service.users().messages().list(
                    userId='me', 
                    q=query, 
                    maxResults=max_results
                ).execute()
                
                messages = results.get('messages', [])
                print(f"Query '{query}' found {len(messages)} messages")
                
                # Add unique messages
                for msg in messages:
                    if msg not in all_messages:
                        all_messages.append(msg)
                        
            except Exception as e:
                print(f"Error with query '{query}': {e}")
                continue
        
        print(f"Total unique messages found: {len(all_messages)}")
        
        parsed_applications = []
        
        for message in all_messages:
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
                
                print(f"Processing email: Subject='{subject[:50]}...' From='{from_header}'")
                
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
                is_job_email = is_job_application_email(subject, body)
                print(f"  Is job email: {is_job_email}")
                
                if is_job_email:
                    company = extract_company_name(subject, body, from_header)
                    title = extract_job_title(subject, body)
                    email_date = parse_email_date(date_header)
                    
                    print(f"  Extracted - Company: {company}, Title: {title}, Date: {email_date}")
                    
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
                        print(f"  ✅ Added to parsed applications")
                    else:
                        print(f"  ❌ Failed to extract company or title")
                else:
                    print(f"  ❌ Not identified as job application email")
                        
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
            # Skip if company name is invalid
            if not app_data['company'] or app_data['company'] == 'Unknown Company':
                print(f"Skipped invalid company: {app_data['company']}")
                continue
            
            # Ensure title and company don't exceed database limits
            title = app_data['title']
            company = app_data['company']
            
            # Truncate if too long (database field is VARCHAR(255))
            if len(title) > 250:
                title = title[:247] + "..."
                print(f"Truncated long title: {title}")
            
            if len(company) > 250:
                company = company[:247] + "..."
                print(f"Truncated long company: {company}")
            
            # Check for existing applications with the same company and date
            # This prevents duplicate entries for the same company from multiple emails
            existing = db.query(JobApplication).filter(
                JobApplication.company == company,
                JobApplication.date_applied == app_data['date']
            ).first()
            
            if existing:
                print(f"Skipped duplicate: {company} - {title} (already exists)")
                continue
            
            # Additional check: look for similar company names on the same date
            similar_companies = db.query(JobApplication).filter(
                JobApplication.date_applied == app_data['date']
            ).all()
            
            is_duplicate = False
            for existing_job in similar_companies:
                # Check if company names are similar (simple similarity check)
                if are_companies_similar(existing_job.company, company):
                    print(f"Skipped similar company: {company} (similar to {existing_job.company})")
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                job_app = JobApplication(
                    title=title,
                    company=company,
                    date_applied=app_data['date']
                )
                db.add(job_app)
                saved_count += 1
                print(f"Added: {company} - {title}")
            else:
                print(f"Skipped duplicate: {company} - {title}")
        
        db.commit()
        print(f"Saved {saved_count} new job applications")
        
    except Exception as e:
        print(f"Error saving applications: {e}")
        db.rollback()
    finally:
        db.close()
    
    return saved_count


def are_companies_similar(company1: str, company2: str) -> bool:
    """
    Check if two company names are similar enough to be considered duplicates.
    Uses general patterns rather than specific company name variations.
    """
    if not company1 or not company2:
        return False
    
    # Normalize company names
    c1 = company1.lower().strip()
    c2 = company2.lower().strip()
    
    # Exact match
    if c1 == c2:
        return True
    
    # One is contained in the other (e.g., "Meta" vs "The Meta")
    if c1 in c2 or c2 in c1:
        return True
    
    # Check for common company suffixes that don't affect identity
    suffixes = [' inc', ' corp', ' llc', ' ltd', ' company', ' co', ' corporation', ' limited']
    
    c1_clean = c1
    c2_clean = c2
    
    for suffix in suffixes:
        c1_clean = c1_clean.replace(suffix, '')
        c2_clean = c2_clean.replace(suffix, '')
    
    if c1_clean == c2_clean:
        return True
    
    # Check for common prefixes that don't affect identity
    prefixes = ['the ', 'a ', 'an ']
    
    c1_clean = c1
    c2_clean = c2
    
    for prefix in prefixes:
        c1_clean = c1_clean.replace(prefix, '')
        c2_clean = c2_clean.replace(prefix, '')
    
    if c1_clean == c2_clean:
        return True
    
    # Check for city variations (e.g., "City of San Francisco" vs "City and County of San Francisco")
    # This is a common pattern for government entities
    if 'city' in c1 and 'city' in c2:
        # Extract the city name after "city of" or "city and county of"
        city1 = re.sub(r'city\s+(?:and\s+county\s+)?of\s+', '', c1)
        city2 = re.sub(r'city\s+(?:and\s+county\s+)?of\s+', '', c2)
        if city1 == city2:
            return True
    
    # Check for abbreviations vs full names
    # e.g., "SF" vs "San Francisco", "NYC" vs "New York City"
    common_abbreviations = {
        'sf': 'san francisco',
        'nyc': 'new york city',
        'la': 'los angeles',
        'dc': 'washington dc',
        'seattle': 'sea',
        'boston': 'bos',
        'chicago': 'chi',
        'miami': 'mia',
        'atlanta': 'atl',
        'denver': 'den',
        'phoenix': 'phx',
        'dallas': 'dal',
        'houston': 'hou',
        'austin': 'aus',
        'portland': 'pdx',
        'san diego': 'sd',
        'philadelphia': 'philly',
        'detroit': 'det',
        'minneapolis': 'minn',
        'cleveland': 'cle'
    }
    
    # Check if one is an abbreviation of the other
    for abbr, full in common_abbreviations.items():
        if (c1 == abbr and c2 == full) or (c1 == full and c2 == abbr):
            return True
    
    # Check for common word variations
    # e.g., "and" vs "&", "of" vs "for"
    c1_variations = c1.replace(' and ', ' & ').replace(' of ', ' for ')
    c2_variations = c2.replace(' and ', ' & ').replace(' of ', ' for ')
    
    if c1_variations == c2_variations:
        return True
    
    # Check for plural vs singular
    if c1.endswith('s') and c1[:-1] == c2:
        return True
    if c2.endswith('s') and c2[:-1] == c1:
        return True
    
    return False


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
