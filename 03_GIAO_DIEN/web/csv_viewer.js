'use strict';
// CSV viewer: create byte offsets for every CSV record, including embedded newlines
// in quoted fields. Only requested rows are decoded; avoids rendering huge CSVs at once.
(function () {
  async function indexBlob(blob) {
    const offsets = [0];
    let insideQuotes = false;
    let position = 0;
    const reader = blob.stream().getReader();
    try {
      for (;;) {
        const {value, done} = await reader.read();
        if (done) break;
        for (let i = 0; i < value.length; i++) {
          const byte = value[i];
          if (byte === 34) insideQuotes = !insideQuotes;
          else if (byte === 10 && !insideQuotes) offsets.push(position + i + 1);
        }
        position += value.length;
      }
    } finally {
      reader.releaseLock();
    }
    if (insideQuotes) throw new Error('Tệp kết quả có dấu nháy CSV không đóng.');
    if (offsets.at(-1) !== position) offsets.push(position);
    if (offsets.length < 3) throw new Error('CSV kết quả không có dòng dữ liệu.');
    return {offsets, rowCount: offsets.length - 2};
  }
  function parseRecord(value) {
    // Retain embedded newlines but strip the record terminator only.
    const line = value.replace(/\r?\n$/, '');
    const fields = [];
    let current = '';
    let quoted = false;
    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      if (char === '"') {
        if (quoted && line[i + 1] === '"') {current += '"'; i++;}
        else quoted = !quoted;
      } else if (char === ',' && !quoted) {
        fields.push(current);
        current = '';
      } else {
        current += char;
      }
    }
    if (quoted) throw new Error('Dòng CSV bị lỗi dấu nháy.');
    fields.push(current);
    return fields;
  }
  async function readRow(blob, index, rowNumber) {
    const start = index.offsets[rowNumber];
    const end = index.offsets[rowNumber + 1];
    if (start === undefined || end === undefined) throw new RangeError('Dòng CSV không tồn tại.');
    return parseRecord(await blob.slice(start, end).text());
  }
  window.TextSenseCsv = {indexBlob, parseRecord, readRow};
})();
