# Source acquisition protocol

1. **Population and priority.** People are sourced from official institutional pages and documents first; Wikipedia biographies are used for broad initial coverage. A person may have more than one source.
2. **Inclusion.** A source must identify the subject and contain a usable biographical or institutional statement. unavailable pages and pages without a CV are recorded as missing, not as negative evidence.
3. **Retrieval.** Each source records its URL, retrieval date, local path and revision where available.
4. **Conversion.** HTML/PDF is converted to plain text and segmented once into sentences with character offsets. The stored text is the object hashed in `source_document.sha256`; the hash fixes the snapshot, not the factual accuracy of the publisher.
5. **Missingness.** A person with no source remains missing. Absence of a source is not evidence that the person lacks an affiliation or qualification.
6. **Acquisition history.** Before/after coverage counts are retained as repository history; the paper reports the frozen release rather than treating acquisition as an experiment.
