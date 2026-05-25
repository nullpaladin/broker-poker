from typing import List
import html
from urllib.parse import quote

# Maximum number of emails per batch should be 100
email_batches: List[List[str]] = []
current_batch: List[str] = []
SUBJECT = "SUBJECT OF THIS CONVERSATION"
BODY = "BODY OF THIS CONVERSATION"

with open("src/dsar/emails/verified_email_list.txt", "r+") as file:
    for line in file.readlines():
        line = line.replace("\n", "")
        if len(current_batch) > 99:
            email_batches.append(current_batch)
            current_batch = []
    
        current_batch.append(line)
    
    if len(current_batch) > 0:
        email_batches.append(current_batch)
    
    print(f"Number of email batches: {len(email_batches)}")
    for num, batch in enumerate(email_batches):
        print(f"Contents of batch {num + 1}: {batch}")

for batch in email_batches:
    recipients: str = ""
    for email in batch:
        recipients += f"{email}, "
    recipients = recipients.removesuffix(", ")

    subject_formatted: str = quote(SUBJECT)
    body_formatted: str = quote(BODY)

    print(f"mailto:?bcc={recipients}&subject={subject_formatted}&body={body_formatted}")
    print(f'<a href="mailto:?bcc={recipients}&subject={subject_formatted}&body={body_formatted}">Link text</a>')