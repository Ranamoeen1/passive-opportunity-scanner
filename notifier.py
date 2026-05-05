import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from typing import List
from models import Opportunity

def send_email_summary(opportunities: List[Opportunity], receiver_email: str = None) -> bool:
    """Sends a summary email of high-relevance opportunities to the user."""
    sender_email = os.getenv("GMAIL_ADDRESS")
    sender_password = os.getenv("GMAIL_APP_PASSWORD")
    
    if not receiver_email:
        receiver_email = sender_email # Default to sender
    
    if not sender_email or not sender_password:
        raise ValueError("Host Gmail configuration missing in .env. Sender address and App Password required.")
        
    if not opportunities:
        raise ValueError("No opportunities to email.")
        
    # Build HTML summary
    html_content = """
    <html>
      <head></head>
      <body>
        <h2>🎯 Passive Opportunity Scanner - Daily Summary</h2>
        <p>I found the following high-value opportunities matching your profile during this scan:</p>
        <hr>
    """
    
    for opp in opportunities:
        urgency = "🔥 <b>URGENT</b>" if opp.is_urgent else ""
        html_content += f"""
        <div style="margin-bottom: 20px;">
            <h3><a href="{opp.url}">{opp.title}</a> {urgency}</h3>
            <p><b>Score:</b> {opp.relevance_score}/100 | <b>Source:</b> {opp.source}</p>
            <p><i>{opp.reasoning}</i></p>
            <p><b>Check your Streamlit Dashboard to see the auto-generated drafts!</b></p>
        </div>
        """
        
    html_content += """
        <hr>
        <p><small>Generated automatically by your AI Career Scout.</small></p>
      </body>
    </html>
    """
    
    message = MIMEMultipart("alternative")
    message["Subject"] = f"🎯 {len(opportunities)} New Opportunities Found!"
    message["From"] = sender_email
    message["To"] = receiver_email
    
    html_part = MIMEText(html_content, "html")
    message.attach(html_part)
    
    try:
        # Create secure connection with server and send email
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, message.as_string())
        server.quit()
        return True
    except smtplib.SMTPAuthenticationError:
        raise PermissionError(f"Authentication Failed for {sender_email}. Please ensure you are using a 16-digit Google App Password, not your standard password.")
    except Exception as e:
        raise RuntimeError(f"Failed to send email summary: {e}")
