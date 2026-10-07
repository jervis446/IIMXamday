/**
 * IIMXamday bug tracker.
 * Run createBugTracker() once. It creates a Google Form and a linked Google Sheet
 * in your Drive, adds a Status column you can update, and emails you on each new report.
 */
const BUG_SECTIONS = ['Classes', 'Exams', 'Results', 'Groups', 'Calendar subscribe', 'Install app', 'Buy me a coffee', 'Other'];

function createBugTracker() {
  const form = FormApp.create('IIMXamday: report a bug')
    .setDescription('Found something wrong in IIMXamday? Tell me what happened and I will fix it. A screenshot link helps a lot.')
    .setCollectEmail(false)
    .setAllowResponseEdits(false)
    .setProgressBar(false)
    .setConfirmationMessage('Thanks, got it. I will take a look.');

  form.addTextItem().setTitle('Roll number').setHelpText('Optional, but it helps me reproduce the issue');
  form.addMultipleChoiceItem().setTitle('Where did it happen?').setChoiceValues(BUG_SECTIONS).setRequired(true);
  form.addParagraphTextItem().setTitle('What went wrong?').setHelpText('What you did, what you expected, what you saw').setRequired(true);
  form.addMultipleChoiceItem().setTitle('Device and browser')
    .setChoiceValues(['iPhone, Safari', 'iPhone, Chrome', 'iPhone, home screen app', 'Android, Chrome', 'Android, home screen app', 'Laptop or desktop'])
    .showOtherOption(true).setRequired(true);
  form.addTextItem().setTitle('Screenshot link').setHelpText('Optional. Upload to Drive or Google Photos and paste a view link');
  form.addTextItem().setTitle('How can I reach you?').setHelpText('Optional. WhatsApp name or email');

  const ss = SpreadsheetApp.create('IIMXamday bug reports');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());
  SpreadsheetApp.flush();
  Utilities.sleep(3000);

  // Add Status and Fix notes columns next to the form responses
  const sheet = ss.getSheets().find(s => s.getFormUrl()) || ss.getSheets()[0];
  sheet.setName('Reports');
  const lastCol = sheet.getLastColumn();
  sheet.getRange(1, lastCol + 1, 1, 2).setValues([['Status', 'Fix notes']]);
  const rule = SpreadsheetApp.newDataValidation().requireValueInList(['New', 'Looking into it', 'Fixed', 'Not a bug'], true).build();
  sheet.getRange(2, lastCol + 1, 999, 1).setDataValidation(rule);
  sheet.getRange(1, 1, 1, lastCol + 2).setFontWeight('bold').setBackground('#333333').setFontColor('#FFFFFF');
  sheet.setFrozenRows(1);
  sheet.setColumnWidth(4, 360);
  ss.getSheets().filter(s => s.getName() === 'Sheet1' && s.getLastRow() === 0).forEach(s => ss.deleteSheet(s));

  // Email on every new report
  ScriptApp.newTrigger('onBugReport').forSpreadsheet(ss).onFormSubmit().create();

  console.log('FORM (share this): ' + form.getPublishedUrl());
  console.log('SHEET (your tracker): ' + ss.getUrl());
  console.log('EDIT FORM: ' + form.getEditUrl());
}

function onBugReport(e) {
  const v = e.namedValues || {};
  const get = k => (v[k] && v[k][0]) || '';
  const row = e.range.getRow();
  e.range.getSheet().getRange(row, e.range.getLastColumn() + 1).setValue('New');
  MailApp.sendEmail(Session.getEffectiveUser().getEmail(),
    'IIMXamday bug: ' + get('Where did it happen?') + (get('Roll number') ? ' (' + get('Roll number') + ')' : ''),
    get('What went wrong?') + '\n\nDevice: ' + get('Device and browser') +
    (get('Screenshot link') ? '\nScreenshot: ' + get('Screenshot link') : '') +
    (get('How can I reach you?') ? '\nContact: ' + get('How can I reach you?') : '') +
    '\n\nTracker: ' + e.range.getSheet().getParent().getUrl());
}
