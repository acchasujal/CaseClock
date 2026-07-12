# SmartBrowz

## Capability

Validate Catalyst SmartBrowz for HTML to PDF generation.

This spike must not build Case Clock report generation. It should only test representative rendering behavior.

## Status

PENDING

No SmartBrowz execution logs, generated PDF artifact, timing measurement, or screenshot evidence are present in this repository.

## Evidence

Run a minimal HTML to PDF test covering:

- Headings
- Tables
- Images
- Unicode text
- Long pages
- Page breaks

Suggested fixture content:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>SmartBrowz Catalyst Spike</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 32px; }
      h1 { break-after: avoid; }
      table { width: 100%; border-collapse: collapse; }
      th, td { border: 1px solid #999; padding: 8px; }
      .page-break { break-before: page; }
    </style>
  </head>
  <body>
    <h1>SmartBrowz Catalyst Spike</h1>
    <p>Unicode sample: Bengaluru, Kannada, ನವದೆಹಲಿ, ₹, §.</p>
    <table>
      <thead><tr><th>Case</th><th>Status</th><th>Notes</th></tr></thead>
      <tbody>
        <tr><td>CC-001</td><td>Open</td><td>Table formatting check</td></tr>
      </tbody>
    </table>
    <div class="page-break"></div>
    <h2>Second Page</h2>
    <p>Page break validation.</p>
  </body>
</html>
```

Expected checks:

| Check | Result | Evidence |
|---|---|---|
| PDF generation succeeds | PENDING | Add SmartBrowz response/log |
| Headings render correctly | PENDING | Add PDF screenshot |
| Tables preserve borders and spacing | PENDING | Add PDF screenshot |
| Images render | PENDING | Add PDF screenshot |
| Unicode renders | PENDING | Add text screenshot |
| Long pages paginate | PENDING | Add page count |
| CSS page breaks work | PENDING | Add page screenshot |
| Generation time measured | PENDING | Add elapsed time |

## Limitations

- SmartBrowz suitability cannot be confirmed without a generated PDF artifact.
- Page-break behavior, font availability, image loading rules, authentication for private assets, and timeout limits remain unknown.
- If SmartBrowz cannot render Kannada reliably, document the fallback font strategy instead of changing report contracts.

## Recommendation

Keep SmartBrowz as the planned PDF path only after this spike produces a rendered PDF with acceptable table, Unicode, image, and pagination quality.
