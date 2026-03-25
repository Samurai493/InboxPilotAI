"""Gmail service for reading emails and creating drafts."""
from typing import List, Dict, Any, Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.config import settings


class GmailService:
    """Service for Gmail API operations."""
    
    def __init__(self, credentials: Optional[Credentials] = None):
        """Initialize Gmail service with credentials."""
        self.credentials = credentials
        self.service = None
        if credentials:
            self.service = build('gmail', 'v1', credentials=credentials)
    
    def list_messages(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        List messages from inbox.
        
        Args:
            max_results: Maximum number of messages to return
            
        Returns:
            List of message metadata
        """
        if not self.service:
            raise ValueError("Gmail service not initialized. Credentials required.")
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            return messages
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")
    
    def get_message(self, message_id: str) -> Dict[str, Any]:
        """
        Get a specific message.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Message content and metadata
        """
        if not self.service:
            raise ValueError("Gmail service not initialized. Credentials required.")
        
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract message data
            payload = message.get('payload', {})
            headers = payload.get('headers', [])
            
            # Extract headers
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            from_header = next((h['value'] for h in headers if h['name'] == 'From'), '')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Extract body
            body = self._extract_body(payload)
            
            return {
                'id': message_id,
                'subject': subject,
                'from': from_header,
                'date': date,
                'body': body,
                'snippet': message.get('snippet', '')
            }
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")
    
    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract message body from payload."""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    import base64
                    body += base64.urlsafe_b64decode(data).decode('utf-8')
        elif payload.get('mimeType') == 'text/plain':
            data = payload['body'].get('data', '')
            import base64
            body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        return body
    
    def create_draft(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """
        Create a draft email.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body
            
        Returns:
            Draft metadata
        """
        if not self.service:
            raise ValueError("Gmail service not initialized. Credentials required.")
        
        try:
            import base64
            from email.mime.text import MIMEText
            
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            draft = self.service.users().drafts().create(
                userId='me',
                body={
                    'message': {
                        'raw': raw_message
                    }
                }
            ).execute()
            
            return draft
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")
