<!-- Source: email/email-campaign/SKILL.md · section 'Quick Send (one-shot)' -->

## Quick Send (one-shot)

```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

sender = 'you@gmail.com'
recipient = 'target@example.com'
app_password = 'xxxx xxxx xxxx xxxx'  # 16-char Gmail App Password

msg = MIMEMultipart('alternative')
msg['From'] = formataddr(('Display Name', sender))
msg['To'] = recipient
msg['Subject'] = 'Subject here'

msg.attach(MIMEText('Plain text fallback', 'plain', 'utf-8'))
msg.attach(MIMEText('<html>...</html>', 'html', 'utf-8'))

with smtplib.SMTP('smtp.gmail.com', 587, timeout=15) as server:
    server.starttls()
    server.login(sender, app_password)
    server.sendmail(sender, [recipient], msg.as_string())
```
