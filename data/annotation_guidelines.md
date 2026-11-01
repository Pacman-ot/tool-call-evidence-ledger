# Annotation guidelines

1. Label each atomic claim independently as `SUPPORTED`, `UNSUPPORTED`, or `PARTIALLY_SUPPORTED`.
2. Prefer exact evidence field paths (`$.output.count`) when the claim restates a stored field.
3. For derived claims, record the formula and both operand pointers.
4. Do not mark a paraphrase `UNSUPPORTED` solely because string match fails if the meaning is clearly entailed by the trace — mark `SUPPORTED` with a note, or `PARTIALLY_SUPPORTED` if material extras were invented.
5. Record ambiguous cases in `annotator_note` rather than forcing a label.
6. Hold out a second domain before tuning matcher rules.
