# IIMXamday

Live site: https://jervis446.github.io/IIMXamday/

Daily flow: Google Apps Script (apps-script/Code.gs, runs under an iimidr account) reads the Term V schedule sheet at 6 AM IST and commits data/schedule.json when it changes. The GitHub Action (.github/workflows/build.yml) parses it, rebuilds index.html and the calendar feeds, commits them, and deploys to Pages.

Manual rebuild: Actions > Rebuild from schedule > Run workflow.
Course rosters, WhatsApp links and Term IV results are static files in _build/.
Bug reports are separate from the app: apps-script/BugTracker.gs creates a Google Form and a tracker sheet in your Drive.

## Jobs board and batch directory

- data/jobs.json holds postings. apps-script/Jobs.gs creates the posting form and syncs new entries hourly.
- _build/parse_whatsapp_export.py turns an exported group chat into postings, for backfilling.
- Sign-in: roll number plus the mobile registered with the office. _build/make_access.py wraps one
  master key per known number into access.json, and encrypts the directory and results under it.
  Rebuild with: python3 make_access.py directory_plain.json phones_private.json
  Never commit directory_plain.json, results_plain.json or phones_private.json.
- Put the posting form's prefilled link in _build/config.json as jobForm.
