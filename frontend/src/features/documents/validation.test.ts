import { validateFile } from './validation';

describe('validateFile (UX pre-check only)', () => {
  it('accepts PDF, DOCX and TXT regardless of case', () => {
    expect(validateFile({ name: 'a.pdf', size: 10 }, 20)).toBeNull();
    expect(validateFile({ name: 'B.DOCX', size: 10 }, 20)).toBeNull();
    expect(validateFile({ name: 'c.txt', size: 10 }, 20)).toBeNull();
  });
  it('rejects other types, empty files and files over the limit', () => {
    expect(validateFile({ name: 'a.exe', size: 10 }, 20)).toMatch(/Unsupported/);
    expect(validateFile({ name: 'noextension', size: 10 }, 20)).toMatch(/Unsupported/);
    expect(validateFile({ name: 'a.pdf', size: 0 }, 20)).toMatch(/empty/);
    expect(validateFile({ name: 'a.pdf', size: 21 * 1024 * 1024 }, 20)).toMatch(/limit is 20 MB/);
  });
});
