import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    SMTP_FROM_EMAIL,
    SMTP_TLS
)
from repos.settings_repo import SettingsRepository
from db.db import get_db

class EmailService:
    """Service for sending emails"""
    
    @staticmethod
    async def send_email(
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None
    ) -> bool:
        """
        Send an email using SMTP
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Plain text email body
            html_body: Optional HTML email body
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Get app settings to check dev mode
            db = await get_db()
            settings_repo = SettingsRepository(db)
            settings = await settings_repo.get_settings()
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = SMTP_FROM_EMAIL
            
            # Handle dev mode
            if settings.get('dev_mode') and settings.get('dev_mode_email'):
                dev_email = settings['dev_mode_email']
                msg['To'] = dev_email
                msg['Subject'] = f"[DEV MODE] {subject} - originally meant for {to_email}"
                to_email = dev_email
                print(f"[DEV MODE] Redirecting email to {dev_email} (originally for {to_email})")
            else:
                msg['To'] = to_email
            
            # Attach plain text body
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach HTML body if provided
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))
            
            # Connect to SMTP server
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                if SMTP_TLS:
                    server.starttls()
                
                # Login to SMTP server
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                
                # Send email
                server.send_message(msg)
                print(f"Email sent successfully to {to_email}")
                
            return True
            
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False
    
    @staticmethod
    async def send_password_reset_email(
        to_email: str,
        reset_code: str
    ) -> bool:
        """
        Send a password reset email
        
        Args:
            to_email: Recipient email address
            reset_code: The password reset code
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        subject = "Password Reset Request"
        
        # Plain text version
        body = f"""
        Hello,
        
        You have requested to reset your password. Your password reset code is:
        
        {reset_code}
        
        This code will expire in 15 minutes.
        
        If you did not request this password reset, please ignore this email.
        
        Best regards,
        Your App Team
        """
        
        # HTML version
        html_body = f"""
        <html>
            <body>
                <h2>Password Reset Request</h2>
                <p>Hello,</p>
                <p>You have requested to reset your password. Your password reset code is:</p>
                <h3 style="background-color: #f0f0f0; padding: 10px; text-align: center; font-size: 24px;">
                    {reset_code}
                </h3>
                <p>This code will expire in 15 minutes.</p>
                <p>If you did not request this password reset, please ignore this email.</p>
                <br>
                <p>Best regards,<br>Your App Team</p>
            </body>
        </html>
        """
        
        return await EmailService.send_email(to_email, subject, body, html_body) 