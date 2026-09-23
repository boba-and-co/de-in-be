(function () {
  const WEBHOOK_URL = 'https://script.google.com/macros/s/AKfycbwCyFNl3J7AFyLbMwLhzKyoXNodUuFoPRbuH4iGXVrHtkFLQCBepANj-i0k89p65LE4Ag/exec';
  const STUDENT_KEY = 'h5p_student';
  let isSubmitting = false;
  let lastSubmitHash = '';

  function getStudentName(forcePromptIfAnonymous) {
    const stored = (sessionStorage.getItem(STUDENT_KEY) || '').trim();
    if (stored && stored !== 'Anonymous' && !forcePromptIfAnonymous) {
      return stored;
    }
    if (stored && stored !== 'Anonymous') {
      return stored;
    }

    const entered = window.prompt('Please enter your name:', stored && stored !== 'Anonymous' ? stored : '') || '';
    const name = entered.trim() || stored || 'Anonymous';
    sessionStorage.setItem(STUDENT_KEY, name);
    return name;
  }

  function getActivityName(statement) {
    const definition = statement && statement.object && statement.object.definition ? statement.object.definition : {};
    const name = definition.name || {};
    if (typeof name === 'string' && name.trim()) return name.trim();
    if (typeof name === 'object' && name !== null) {
      if (name['en-US']) return name['en-US'];
      if (name['en']) return name['en'];
      if (name['de']) return name['de'];
      if (name['de-DE']) return name['de-DE'];
      const values = Object.values(name);
      if (values.length > 0 && typeof values[0] === 'string' && values[0].trim()) {
        return values[0].trim();
      }
    }
    if (document.title && document.title.trim()) {
      return document.title.trim();
    }
    return 'H5P Activity';
  }

  function getScoreValue(event, statement) {
    if (typeof event.getScore === 'function') {
      const s = event.getScore();
      if (typeof s === 'number') return s;
    }
    if (statement && statement.result && statement.result.score) {
      const score = statement.result.score;
      if (typeof score.raw === 'number') return score.raw;
      if (typeof score.scaled === 'number') return Math.round(score.scaled * 100);
    }
    return 0;
  }

  function getMaxScoreValue(event, statement) {
    if (typeof event.getMaxScore === 'function') {
      const m = event.getMaxScore();
      if (typeof m === 'number') return m;
    }
    if (statement && statement.result && statement.result.score) {
      const score = statement.result.score;
      if (typeof score.max === 'number') return score.max;
      if (typeof score.raw === 'number' && typeof score.min === 'number') return score.max || score.raw;
    }
    return 0;
  }

  function extractSentenceAndErrors(sentenceGroups) {
    let accumulatedText = '';
    const errorRanges = [];

    sentenceGroups.forEach(group => {
      const wrongElements = group.querySelectorAll('.h5p-wrong');
      if (wrongElements.length === 0) return;

      const p = group.querySelector('p') || group;
      let lineText = '';
      const lineErrors = [];

      function appendChunk(chunk, isError) {
        if (!chunk) return;
        let clean = chunk.replace(/[\u00A0\s]+/g, ' ');
        if (lineText.length === 0) {
          clean = clean.trimStart();
        }
        if (!clean) return;
        if (lineText.endsWith(' ') && clean.startsWith(' ')) {
          clean = clean.slice(1);
        }
        if (!clean) return;

        const start = lineText.length;
        const end = start + clean.length;
        lineText += clean;
        if (isError) {
          lineErrors.push({ start, end });
        }
      }

      function walk(node) {
        if (!node) return;
        if (node.nodeType === Node.TEXT_NODE) {
          appendChunk(node.textContent, false);
          return;
        }
        if (node.nodeType === Node.ELEMENT_NODE) {
          const classList = node.classList;
          if (
            classList &&
            (classList.contains('hidden-but-read') ||
              classList.contains('h5p-correct-answer') ||
              classList.contains('joubel-tip-container'))
          ) {
            return;
          }

          if (
            (classList && classList.contains('h5p-input-wrapper')) ||
            node.tagName === 'INPUT'
          ) {
            const input = node.tagName === 'INPUT' ? node : node.querySelector('input');
            const val = input && input.value && input.value.trim() !== '' ? input.value : '___';
            const isWrong =
              Boolean(classList && classList.contains('h5p-wrong')) ||
              Boolean(input && input.classList && input.classList.contains('h5p-wrong'));

            appendChunk(val, isWrong);
            return;
          }

          node.childNodes.forEach(walk);
        }
      }

      walk(p);

      const trimmedLine = lineText.trimEnd();
      const cut = lineText.length - trimmedLine.length;
      lineText = trimmedLine;

      const validLineErrors = lineErrors
        .filter(err => err.start < lineText.length)
        .map(err => ({
          start: err.start,
          end: Math.min(err.end, lineText.length)
        }));

      if (lineText.length > 0) {
        if (accumulatedText.length > 0) {
          accumulatedText += '\n';
        }
        const baseOffset = accumulatedText.length;
        validLineErrors.forEach(err => {
          errorRanges.push({
            start: baseOffset + err.start,
            end: baseOffset + err.end
          });
        });
        accumulatedText += lineText;
      }
    });

    return { accumulatedText, errorRanges };
  }

  function attachDispatcher() {
    if (!(window.H5P && window.H5P.externalDispatcher)) {
      setTimeout(attachDispatcher, 200);
      return;
    }

    H5P.externalDispatcher.on('xAPI', function (event) {
      const statement = event && event.data && event.data.statement;
      if (!statement) return;

      const completed =
        Boolean(statement.result && statement.result.completion) ||
        (statement.verb && statement.verb.id === 'http://adlnet.gov/expapi/verbs/completed') ||
        (statement.verb && statement.verb.id === 'http://adlnet.gov/expapi/verbs/answered');

      if (!completed) return;

      setTimeout(() => {
        const score = getScoreValue(event, statement);
        const maxScore = getMaxScoreValue(event, statement);
        const activity = getActivityName(statement);

        const sentenceGroups = document.querySelectorAll(
          '.h5p-question-content div[role="group"], .h5p-blanks div[role="group"]'
        );

        const { accumulatedText, errorRanges } = extractSentenceAndErrors(sentenceGroups);

        let finalSentence = '';
        if (accumulatedText) {
          finalSentence = accumulatedText;
        } else if (score >= maxScore && maxScore > 0) {
          finalSentence = 'All answers correct!';
        } else {
          finalSentence = score === maxScore
            ? 'All answers correct!'
            : 'Mistakes detected (detailed breakdown unavailable for this exercise format)';
        }

        const student = getStudentName(false);

        const submitHash = `${student}|${activity}|${score}|${maxScore}|${finalSentence}`;
        if (submitHash === lastSubmitHash && isSubmitting) {
          return;
        }
        lastSubmitHash = submitHash;
        isSubmitting = true;

        const payload = {
          timestamp: new Date().toISOString(),
          student: student,
          activity: activity,
          score: score,
          maxScore: maxScore,
          sentence: finalSentence,
          errors: accumulatedText ? errorRanges : []
        };

        console.log('[Quiz Tracker] Sending results to webhook:', payload);
        fetch(WEBHOOK_URL, {
          method: 'POST',
          mode: 'no-cors',
          headers: { 'Content-Type': 'text/plain;charset=utf-8' },
          body: JSON.stringify(payload)
        })
          .then(() => {
            console.log('[Quiz Tracker] Webhook request dispatched successfully.');
          })
          .catch((err) => {
            console.error('[Quiz Tracker] Webhook request failed:', err);
          })
          .finally(() => {
            setTimeout(() => {
              isSubmitting = false;
            }, 1000);
          });
      }, 250);
    });
  }

  const initialName = getStudentName(false);
  if (initialName) {
    sessionStorage.setItem(STUDENT_KEY, initialName);
  }
  attachDispatcher();
})();

