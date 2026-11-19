"""
Default email subjects and messages. Users can change them before sending.
"""

INVOICE_SUBJECT = "Invoice {number} from {company}"
INVOICE_MESSAGE = (
    "Dear {customer},\n\n"
    "Here is invoice {number} for {amount}, due on {due_date}.\n"
    "{link_line}\n"
    "Thank you for your business!\n\n"
    "{company}"
)

DOCUMENT_SUBJECT = "{title} {number} from {company}"
DOCUMENT_MESSAGE = (
    "Dear {customer},\n\n"
    "Please find attached {title_lower} {number} for {amount}.\n\n"
    "Thank you,\n{company}"
)

STATEMENT_SUBJECT = "Statement from {company}"
STATEMENT_MESSAGE = (
    "Dear {customer},\n\n"
    "Please find attached your statement. The amount due is {amount}.\n\n"
    "Thank you,\n{company}"
)

REMINDER_SUBJECT = "Reminder: invoice {number} from {company} is overdue"
REMINDER_MESSAGE = (
    "Dear {customer},\n\n"
    "This is a friendly reminder that invoice {number} was due on {due_date}. "
    "The balance due is {amount}.\n"
    "{link_line}\n"
    "If you have already paid, please ignore this message.\n\n"
    "{company}"
)
