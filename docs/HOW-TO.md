# Documentation — How-To Guide

---

## Files in this folder

| File | Purpose |
|---|---|
| `Collatz_HowTo.docx` | Full how-to guide in Word format (v1.2) |
| `Collatz_Academic_Paper.docx` | Peer-review paper in Word format |
| `collatz_mcom.tex` | Peer-review paper in AMS MCOM LaTeX format |

---

## Collatz_HowTo.docx

A formatted Word document covering the full system — requirements, quick start, production server setup, configuration, output files, scaling, merging results, GitHub repository, FAQ, and troubleshooting. Suitable for sharing with collaborators who want a printable reference.

Open with Microsoft Word, LibreOffice, or Google Docs (File → Upload).

---

## Collatz_Academic_Paper.docx

A peer-review ready academic paper covering:

- Introduction and background
- Formal proofs of the three algorithmic optimizations (Theorems 3.1–3.3)
- Algorithm design (pseudocode)
- Distributed architecture
- Implementation details
- Experimental results and benchmarks
- Discussion and conclusion
- Complete source code in Appendix A
- 16 references in IEEE format

Suitable for submission to computational mathematics journals. Author and institution fields are left blank for double-blind review — fill them in before submitting.

---

## collatz_mcom.tex

The same academic paper formatted for the **AMS Mathematics of Computation (MCOM)** journal using the official `mcom-l` document class.

### Compiling on Overleaf (easiest)

1. Go to https://www.overleaf.com/latex/templates/latex-template-for-the-ams-mathematics-of-computation-mcom/jbhmypnncmmc
2. Click "Open as Template"
3. Delete the template content and paste in `collatz_mcom.tex`
4. Click Compile

### Compiling locally

Requires a TeX Live or MiKTeX installation with the AMS journal packages:

```bash
pdflatex collatz_mcom.tex
pdflatex collatz_mcom.tex   # run twice for references
```

Or with bibliography:

```bash
pdflatex collatz_mcom.tex
bibtex collatz_mcom
pdflatex collatz_mcom.tex
pdflatex collatz_mcom.tex
```

### Key LaTeX packages used

- `mcom-l` — AMS MCOM document class (provided in the Overleaf template)
- `algorithm` + `algpseudocode` — pseudocode for Algorithms 1 and 2
- `listings` — Python source code in Appendix A
- `booktabs` — publication-quality tables
- `amssymb`, `amsmath`, `amsthm` — standard AMS math

### Before submitting

Fill in these fields in the top matter:

```latex
\author{Your Name}
\address{Your Institution, City, Country}
\email{your@email.com}
```

The MSC 2020 classification codes are already set:
- Primary: `11Y16` (Number-theoretic algorithms; complexity)
- Secondary: `11B37`, `68W10`, `68Q25`

### Target journals

This paper is formatted for MCOM but the content is also suitable for:
- *Experimental Mathematics* (Taylor & Francis)
- *Journal of Integer Sequences* (open access)
- *Mathematics of Computation* (AMS) — primary target

---

## Suggested submission workflow

1. Compile `collatz_mcom.tex` on Overleaf — verify it looks correct
2. Add your name, institution, and email
3. Export as PDF
4. Submit via the MCOM submission portal: https://www.ams.org/publications/journals/journalsframework/mcom
5. Upload both the `.tex` file and the PDF
