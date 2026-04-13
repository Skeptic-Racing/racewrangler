export function parseApiUtcDate(dateStr: string): Date {
  // Backend emits UTC-naive ISO timestamps. Treat missing timezone as UTC.
  const hasTimezone = /[zZ]|[+-]\d{2}:\d{2}$/.test(dateStr);
  return new Date(hasTimezone ? dateStr : `${dateStr}Z`);
}

export function formatUtcTimeWithMs(dateStr: string): string {
  const date = parseApiUtcDate(dateStr);

  const hh = String(date.getUTCHours()).padStart(2, '0');
  const mm = String(date.getUTCMinutes()).padStart(2, '0');
  const ss = String(date.getUTCSeconds()).padStart(2, '0');
  const mmm = String(date.getUTCMilliseconds()).padStart(3, '0');

  return `${hh}:${mm}:${ss}.${mmm} UTC`;
}
