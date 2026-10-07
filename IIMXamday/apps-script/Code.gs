/**
 * IIMXamday schedule sync.
 * Runs under your iimidr Google account, reads the Term V schedule sheet,
 * and commits it to GitHub as data/schedule.json only when something changed.
 * The GitHub Action then rebuilds and redeploys the site.
 */
const SHEET_ID = '1hCGJ7z8zkU2QhlAIzBOzTJODA7wj5uxmukQTb-TIKU4';
const SHEET_GID = 0;                      // the tab in the URL (#gid=0)
const REPO = 'jervis446/IIMXamday';
const BRANCH = 'main';
const PATH = 'data/schedule.json';
const NOTIFY_ON_CHANGE = true;            // email yourself when the schedule changes

function syncSchedule() {
  const ss = SpreadsheetApp.openById(SHEET_ID);
  const tz = ss.getSpreadsheetTimeZone();
  const sheet = ss.getSheets().find(s => s.getSheetId() === SHEET_GID) || ss.getSheets()[0];
  const values = sheet.getDataRange().getValues();

  const rows = values.map(r => r.map(v => {
    if (v instanceof Date) {
      // Time-only cells come back as dates in 1899
      return v.getFullYear() < 1901
        ? Utilities.formatDate(v, tz, 'HH:mm')
        : Utilities.formatDate(v, tz, 'yyyy-MM-dd');
    }
    return String(v).trim();
  }));
  const content = JSON.stringify({ sheet: 'Term V schedule', rows: rows }, null, 0);

  const token = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
  if (!token) throw new Error('Add GITHUB_TOKEN in Project Settings > Script properties');
  const api = 'https://api.github.com/repos/' + REPO + '/contents/' + PATH;
  const headers = {
    Authorization: 'Bearer ' + token,
    Accept: 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28'
  };

  const cur = UrlFetchApp.fetch(api + '?ref=' + BRANCH, { headers: headers, muteHttpExceptions: true });
  let sha = null, old = null;
  if (cur.getResponseCode() === 200) {
    const j = JSON.parse(cur.getContentText());
    sha = j.sha;
    old = Utilities.newBlob(Utilities.base64Decode(j.content.replace(/\n/g, ''))).getDataAsString('UTF-8');
  } else if (cur.getResponseCode() !== 404) {
    throw new Error('GitHub read failed: ' + cur.getResponseCode() + ' ' + cur.getContentText());
  }

  if (old !== null && normalise(old) === normalise(content)) {
    console.log('Schedule unchanged');
    return;
  }

  const stamp = Utilities.formatDate(new Date(), 'Asia/Kolkata', 'dd MMM yyyy HH:mm');
  const body = {
    message: 'Schedule sync ' + stamp + ' IST',
    content: Utilities.base64Encode(content, Utilities.Charset.UTF_8),
    branch: BRANCH
  };
  if (sha) body.sha = sha;
  const put = UrlFetchApp.fetch(api, {
    method: 'put', headers: headers, contentType: 'application/json',
    payload: JSON.stringify(body), muteHttpExceptions: true
  });
  if (put.getResponseCode() >= 300) {
    throw new Error('GitHub write failed: ' + put.getResponseCode() + ' ' + put.getContentText());
  }
  console.log('Schedule changed, committed to GitHub');

  if (NOTIFY_ON_CHANGE) {
    MailApp.sendEmail(Session.getEffectiveUser().getEmail(),
      'IIMXamday: Term V schedule changed',
      'The schedule sheet changed and was pushed at ' + stamp + ' IST.\n' +
      'The site rebuilds in about 2 minutes: https://github.com/' + REPO + '/actions');
  }
}

function normalise(s) {
  try { return JSON.stringify(JSON.parse(s)); } catch (e) { return s; }
}

/** Run once to schedule the daily sync at 6 AM IST. */
function installDailyTrigger() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'syncSchedule')
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('syncSchedule').timeBased().everyDays(1).atHour(6).inTimezone('Asia/Kolkata').create();
}
