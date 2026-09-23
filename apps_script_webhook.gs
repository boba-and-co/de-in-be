function doGet() {
  return HtmlService.createHtmlOutput('Quiz webhook is active.');
}

function doPost(e) {
  const lock = LockService.getScriptLock();
  try {
    lock.waitLock(15000);

    const contents = (e && e.postData && e.postData.contents) ? e.postData.contents : '{}';
    const payload = JSON.parse(contents);

    const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
    let sheet = spreadsheet.getSheetByName('Results') || spreadsheet.getActiveSheet();

    if (!sheet) {
      sheet = spreadsheet.insertSheet('Results');
    }

    if (sheet.getLastRow() === 0) {
      sheet.appendRow(['Timestamp', 'Student', 'Activity', 'Score', 'Max Score', 'Mistakes']);
      sheet.getRange(1, 1, 1, 6).setFontWeight('bold');
    }

    const timestamp = payload.timestamp || new Date().toISOString();
    const student = payload.student || 'Anonymous';
    const activity = payload.activity || 'H5P Activity';
    const score = payload.score ?? 0;
    const maxScore = payload.maxScore ?? 0;
    const mistakes = payload.sentence || '';

    sheet.appendRow([timestamp, student, activity, score, maxScore, mistakes]);

    const lastRow = sheet.getLastRow();
    const mistakesCell = sheet.getRange(lastRow, 6);
    const value = mistakesCell.getValue();

    if (typeof value === 'string' && value && value.length > 0 && Array.isArray(payload.errors) && payload.errors.length > 0) {
      const cellText = value;
      const color = SpreadsheetApp.newTextStyle().setForegroundColor('#d93025').build();

      const ranges = payload.errors
        .map(item => ({
          start: Math.max(0, parseInt(item.start, 10) || 0),
          end: Math.min(cellText.length, parseInt(item.end, 10) || 0)
        }))
        .filter(item => item.end > item.start)
        .sort((a, b) => a.start - b.start);

      if (ranges.length > 0) {
        const richText = SpreadsheetApp.newRichTextValue().setText(cellText);

        ranges.forEach(range => {
          richText.setTextStyle(range.start, range.end, color);
        });

        mistakesCell.setRichTextValue(richText.build());
      }
    }

    return ContentService.createTextOutput('OK').setMimeType(ContentService.MimeType.TEXT);
  } catch (error) {
    console.error('Webhook error:', error);
    return ContentService.createTextOutput('ERROR: ' + error.message).setMimeType(ContentService.MimeType.TEXT);
  } finally {
    try {
      lock.releaseLock();
    } catch (_) {}
  }
}

