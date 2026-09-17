# Follow-up campaigns to an already-contacted list

Rules learned re-mailing a list that had already received one campaign three
weeks earlier (113 recipients, 0 replies). Getting these wrong is visible to the
recipient and undoes the relationship.

## The contact export is NOT the audience

Asked to "re-include the 113 contacts", the obvious move is to re-run the
contact extractor without its exclusion flag. That produced **18** contacts, not
113 — because the LinkedIn export only ever held 13 addresses.

The audience of a past campaign lives in **`tracking.json['sent']`**. That is the
authoritative record of who actually received mail. The CSV/JSON contact files
are only useful for *enriching* those addresses (first name, company, category).

Correct rebuild:

```python
sent = json.load(open('tracking.json'))['sent']        # source of truth
# then look each address up across every contact file to fill in name/company
```

Cross-check before trusting either side: count how many of `sent[]` each contact
file actually covers. Addresses present in `sent[]` but in **no** contact file
are the manually-added ones — usually organizations, not individuals.

## Read the previously sent template before writing the follow-up

Extract the prior email's body and **measure the register**:

```bash
grep -ocE "\b(tu|te|ton|ta|tes)\b" template_previous.html
grep -ocE "\b(vous|votre|vos)\b" template_previous.html
```

In the real case the earlier mail scored 4 informal / 0 formal — it addressed
everyone with *tu* ("je voulais te la partager", "si t'as 30 secondes"). A
follow-up written in formal B2B register, with a security-audit value
proposition, would have read as an automated mailing to people who had been
spoken to as friends three weeks before.

Do this check even when the brief explicitly states a tone. The user's own
request said to categorize all 113 as "entreprise"; 106 of them were friends.

## The friends list is the ONLY authority for a "friend" category

Deriving category from the email domain (gmail = individual, custom = business)
misclassifies. `14310@aidec.pro`, `lencrage@gmail.com`,
`vaticaenproduction@gmail.com` are organizations on consumer domains or vice
versa.

Rule that worked: an address is a friend **only** if it appears in the friends
CSV(s). Anything else in `sent[]` defaults to organization. Default-to-friend is
the dangerous direction — it sends informal copy to a business.

Result on the real list: 106 friends + 7 organizations = 113, matching the
source files exactly. Domain heuristics alone had given 110/3.

## Only derive a first name for individuals

Extracting a first name from the email local part is fine for a friend
(`adelinecoffard@` → "Adeline"). Applied to an organization it produces
`Bonjour Vaticaenproduction,` / `Bonjour Cdar,` — worse than no name.

- individuals: fall back to the local part, capitalized
- organizations: use an explicitly recorded name or nothing
- generic mailboxes (`contact@`, `info@`, `rh@`): never a first name
- always support an empty value cleanly: `Bonjour{name_slot},` → `Bonjour,`

Report the coverage ("first name known for 105 / 113") so the user can spot bad
data before it ships.

## For a friends list, the ask is a referral, not a sale

A friend will not buy an audit. They may know someone who needs a site. The
earlier campaign already had that sentence buried in the last line; moving it to
the centre of the message is the single highest-value edit. Keep a soft
secondary CTA ("15 minutes, no commitment") rather than a hard one.

## Check the source data is real before building anything

A folder of sample CVs turned out to be fixtures generated in an earlier
session, all on `@example.com`. RFC 2606 reserves `example.com/.org/.net`,
`test`, and `invalid` — they **cannot receive mail**. Filter and report them
loudly rather than letting them into a send list:

```python
UNDELIVERABLE = ("example.com","example.org","example.net","test","invalid","localhost")
```

More generally: before promising a campaign on a data source, verify the source
holds real, deliverable, current contacts. Say so plainly when it does not — an
honest "there is no viable audience here" beats a technically-correct pipeline
aimed at nothing.

## Segment counts must reconcile

After building the final list, assert the segment totals against the source:

```python
Counter(line.split(';')[3] for line in open('final_list.txt')
        if line.strip() and not line.startswith('#'))
```

If the total or split does not match what the source files imply, the
categorization logic is wrong — do not send.
