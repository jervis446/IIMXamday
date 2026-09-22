# IIMXamday

Live site: https://jervis446.github.io/IIMXamday/

Daily flow: Google Apps Script (apps-script/Code.gs, runs under an iimidr account) reads the Term V schedule sheet at 6 AM IST and commits data/schedule.json when it changes. The GitHub Action (.github/workflows/build.yml) parses it, rebuilds index.html and the calendar feeds, commits them, and deploys to Pages.

Manual rebuild: Actions > Rebuild from schedule > Run workflow.
Course rosters, WhatsApp links and Term IV results are static files in _build/.
Bug reports are separate from the app: apps-script/BugTracker.gs creates a Google Form and a tracker sheet in your Drive.
