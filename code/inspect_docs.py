from docx import Document

doc1 = Document('full_text_batch_1.docx')
print(f"Doc 1 has {len(doc1.paragraphs)} paragraphs.")
for p in doc1.paragraphs[:50]:
    if p.text.strip():
        print(p.text[:200])
