# Google Contacts CSV Export Format

When a user exports contacts from https://contacts.google.com using the
"Google CSV" format, the resulting file has these columns:

## Column Reference

| Column | Description |
|---|---|
| `First Name` | Given name |
| `Middle Name` | Middle name |
| `Last Name` | Family name |
| `Phonetic First Name` | Pronunciation guide |
| `Phonetic Middle Name` | Pronunciation guide |
| `Phonetic Last Name` | Pronunciation guide |
| `Name Prefix` | Mr, Mrs, Dr, etc. |
| `Name Suffix` | Jr, Sr, III, etc. |
| `Nickname` | Nickname |
| `File As` | Display name ordering |
| `Organization Name` | Company / employer |
| `Organization Title` | Job title |
| `Organization Department` | Department |
| `Birthday` | Date of birth |
| `Notes` | Free-text notes |
| `Photo` | Photo URL |
| `Labels` | Google Contact labels (e.g., `* myContacts`) |
| `E-mail 1 - Label` | Label for primary email (e.g., `*`) |
| `E-mail 1 - Value` | Primary email address |
| `E-mail 2 - Label` | Label for secondary email |
| `E-mail 2 - Value` | Secondary email address |
| `E-mail 3 - Label` | Label for tertiary email |
| `E-mail 3 - Value` | Tertiary email address |
| `Phone 1 - Label` | Phone label |
| `Phone 1 - Value` | Phone number |
| `Phone 2 - Label` | Phone label |
| `Phone 2 - Value` | Phone number |
| `Address 1 - *` | Address fields |
| `Website 1 - Label` | Website label |
| `Website 1 - Value` | Website URL |

## Key Facts

- **Many entries are phone-only** (no email). Always check `E-mail 1 - Value`
  first; if empty, the contact has no email. Phone-only contacts should be
  excluded from email-based filtering and reported as "ignored."

- **First Name may contain the email address** when Google auto-imported a
  contact from an email interaction without a name. Always check
  `is_name_field_valid()` against the email to catch these.

- **Labels** (column `Labels`) often contain `* myContacts` for user-created
  contacts. This can be used as a quality signal but is not reliable.

- **Organization Name** and **Organization Title** are rarely populated
  (<5% of contacts in typical personal Google accounts). Don't rely on
  them for filtering decisions.

## Access Pattern in Python

```python
def get_all_emails(row: dict) -> list[str]:
    emails = []
    for key in ["E-mail 1 - Value", "E-mail 2 - Value", "E-mail 3 - Value"]:
        val = row.get(key, "").strip()
        if val and "@" in val:
            emails.append(val)
    return emails

first_name = row.get("First Name", "").strip()
last_name = row.get("Last Name", "").strip()
org = row.get("Organization Name", "").strip()
title = row.get("Organization Title", "").strip()
```
