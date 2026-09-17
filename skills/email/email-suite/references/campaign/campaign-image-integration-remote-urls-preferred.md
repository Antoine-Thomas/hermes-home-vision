<!-- Source: email/email-campaign/SKILL.md · section 'Image Integration — Remote URLs Preferred' -->

## Image Integration — Remote URLs Preferred

**Always prefer remote `<img>` tags over CID (Content-ID) attachments.** Reasons:
- Lighter email payload (no base64 bloat)
- Better deliverability (less flagging by spam filters)
- Easier to update images without re-sending
- Consistent rendering across email clients

```html
<!-- Preferred: remote URL -->
<img src="https://example.com/image.webp" alt="Description" style="max-width:100%;height:auto;" />

<!-- Avoid: CID attachment -->
<img src="cid:image-id" ... />
```

Only use CID attachments when the image MUST display offline or when the image is dynamically generated per-recipient.
