/**
 * IIMXamday jobs board.
 * Run createJobsForm() once: it creates the posting form and its sheet,
 * then prints the form link to put in _build/config.json as jobForm.
 * Run installJobsTrigger() to sync postings into the repo every hour.
 * Uses REPO, BRANCH and GITHUB_TOKEN from Code.gs.
 */
const JOBS_PATH = 'data/jobs.json';
const JOBS_SHEET_PROP = 'JOBS_SHEET_ID';

function createJobsForm() {
  const form = FormApp.create('IIMXamday: post a job or referral')
    .setDescription('Shared with the MMS 25-27 batch inside IIMXamday. Keep it to roles you can refer for or postings worth passing on.')
    .setCollectEmail(false).setAllowResponseEdits(true).setProgressBar(false)
    .setConfirmationMessage('Posted. It appears in the app at the next sync, usually within an hour.');

  const name = form.addTextItem().setTitle('Your name').setRequired(true);
  form.addTextItem().setTitle('Role title').setRequired(true);
  form.addTextItem().setTitle('Company').setRequired(true);
  form.addTextItem().setTitle('Location').setHelpText('City, or Remote');
  form.addMultipleChoiceItem().setTitle('Type')
    .setChoiceValues(['Full time', 'Contract', 'Internship']).showOtherOption(true);
  form.addTextItem().setTitle('Experience needed').setHelpText('For example 3 to 6 years');
  form.addMultipleChoiceItem().setTitle('Domain')
    .setChoiceValues(['Product', 'Data and AI', 'Engineering', 'Consulting', 'Finance', 'Marketing', 'Sales', 'HR', 'Operations', 'Supply chain', 'Other'])
    .showOtherOption(true).setRequired(true);
  form.addTextItem().setTitle('Link to the posting');
  form.addParagraphTextItem().setTitle('Anything else').setHelpText('Team, must-haves, whether you can refer directly');
  form.addTextItem().setTitle('Your WhatsApp number')
    .setHelpText('Optional. If you add it, an Ask on WhatsApp button appears on your post and anyone with the app link can see the number.');

  const ss = SpreadsheetApp.create('IIMXamday job postings');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());
  SpreadsheetApp.flush(); Utilities.sleep(3000);
  PropertiesService.getScriptProperties().setProperty(JOBS_SHEET_PROP, ss.getId());

  const prefill = form.createResponse().withItemResponse(name.createResponse('NAMEHERE')).toPrefilledUrl();
  console.log('FORM (share this): ' + form.getPublishedUrl());
  console.log('PREFILL (put in _build/config.json as jobForm): ' + prefill);
  console.log('SHEET: ' + ss.getUrl());
}

function syncJobs() {
  const id = PropertiesService.getScriptProperties().getProperty(JOBS_SHEET_PROP);
  if (!id) throw new Error('Run createJobsForm first');
  const sheet = SpreadsheetApp.openById(id).getSheets()[0];
  const rows = sheet.getDataRange().getValues();
  const head = rows.shift().map(h => String(h).trim().toLowerCase());
  const col = n => head.findIndex(h => h.indexOf(n) === 0);
  const idx = {
    ts: 0, name: col('your name'), title: col('role title'), company: col('company'),
    loc: col('location'), type: col('type'), exp: col('experience'), domain: col('domain'),
    link: col('link'), notes: col('anything'), phone: col('your whatsapp')
  };
  const out = [];
  rows.forEach((r, i) => {
    const title = String(r[idx.title] || '').trim();
    if (!title) return;
    const ts = r[0] instanceof Date ? r[0] : new Date();
    out.push({
      id: 'f' + (i + 1),
      posted: Utilities.formatDate(ts, 'Asia/Kolkata', "yyyy-MM-dd'T'HH:mm:ssXXX"),
      title: title,
      company: String(r[idx.company] || '').trim(),
      loc: String(r[idx.loc] || '').trim(),
      type: String(r[idx.type] || '').trim(),
      exp: String(r[idx.exp] || '').trim(),
      domain: String(r[idx.domain] || '').trim(),
      link: String(r[idx.link] || '').trim(),
      notes: String(r[idx.notes] || '').trim(),
      by: String(r[idx.name] || '').trim(),
      ph: String(r[idx.phone] || '').replace(/\D/g, '').slice(-10),
      src: 'App'
    });
  });

  // Keep anything added by hand or imported from the group export
  let manual = [];
  try {
    const cur = JSON.parse(readGithub_(JOBS_PATH) || '[]');
    manual = cur.filter(j => j.src !== 'App');
  } catch (e) {}
  const all = manual.concat(out).sort((a, b) => (b.posted || '').localeCompare(a.posted || ''));
  putGithub_(JOBS_PATH, JSON.stringify(all), 'Jobs sync ' +
    Utilities.formatDate(new Date(), 'Asia/Kolkata', 'dd MMM yyyy HH:mm') + ' IST');
}

function readGithub_(path) {
  const token = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
  const res = UrlFetchApp.fetch('https://api.github.com/repos/' + REPO + '/contents/' + path + '?ref=' + BRANCH,
    { headers: { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json' }, muteHttpExceptions: true });
  if (res.getResponseCode() !== 200) return null;
  const j = JSON.parse(res.getContentText());
  return Utilities.newBlob(Utilities.base64Decode(j.content.replace(/\n/g, ''))).getDataAsString('UTF-8');
}

function putGithub_(path, content, message) {
  const token = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
  const api = 'https://api.github.com/repos/' + REPO + '/contents/' + path;
  const headers = { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json' };
  const cur = UrlFetchApp.fetch(api + '?ref=' + BRANCH, { headers: headers, muteHttpExceptions: true });
  let sha = null, old = null;
  if (cur.getResponseCode() === 200) {
    const j = JSON.parse(cur.getContentText());
    sha = j.sha;
    old = Utilities.newBlob(Utilities.base64Decode(j.content.replace(/\n/g, ''))).getDataAsString('UTF-8');
  }
  if (old === content) { console.log('No change'); return; }
  const body = { message: message, content: Utilities.base64Encode(content, Utilities.Charset.UTF_8), branch: BRANCH };
  if (sha) body.sha = sha;
  const put = UrlFetchApp.fetch(api, { method: 'put', headers: headers, contentType: 'application/json',
    payload: JSON.stringify(body), muteHttpExceptions: true });
  if (put.getResponseCode() >= 300) throw new Error('GitHub write failed: ' + put.getContentText());
  console.log('Committed ' + path);
}

/** Hourly sync of new postings. */
function installJobsTrigger() {
  ScriptApp.getProjectTriggers().filter(t => t.getHandlerFunction() === 'syncJobs').forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('syncJobs').timeBased().everyHours(1).create();
}
