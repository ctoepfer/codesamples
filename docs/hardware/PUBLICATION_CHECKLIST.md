# Publication checklist: `docs/hardware_internal/` → `docs/hardware/`

Before any fact, claim, protocol detail, or code snippet moves from the internal research collection into a public guide (or into public package metadata such as a capability manifest), it must be reviewed against every item below. **A claim should be included publicly only when it is relevant to what Pacific BrewIO actually implements or intentionally supports** — internal research that goes beyond that scope stays internal, permanently, regardless of how well-documented it is.

This is a promotion gate, not a formality. Treat a "no" or "unsure" answer on any item as a blocker, not a note to revisit later.

## Technical review

- [ ] **Technical accuracy** — has the claim been verified against real hardware (not just static analysis or vendor-app decompilation)?
- [ ] **Current model and firmware applicability** — is it still true for the models/firmware Pacific BrewIO actually targets, today?
- [ ] **Evidence quality** — what evidence tier backs this claim in the internal research (official docs, source-verified open-source firmware, static analysis of a closed app, third-party corroboration, architectural inference)? Only "official" or "source-verified" tiers should generally back a public compatibility claim; anything weaker needs explicit real-hardware confirmation first.
- [ ] **Physical hardware validation** — has someone actually run this against the physical device, not just read the protocol?
- [ ] **Safety classification** — does the public guide correctly carry forward the risk tier (read-only/low/medium/high) and every safety warning attached to the underlying operation?
- [ ] **Conflicting evidence** — do multiple internal sources disagree about this behavior? If so, resolve the conflict (or explicitly scope the claim to the specific version/model it was confirmed on) before publishing either version.
- [ ] **Deprecated findings** — is this superseded by a newer firmware/app version's behavior already noted in the internal research? Don't publish a stale finding as current.
- [ ] **Public API relevance** — does this describe something Pacific BrewIO's typed API or capability manifest actually exposes? Internal protocol trivia that never surfaces through the public interface does not belong in a public guide.

## Legal and privacy review

- [ ] **Licensing and provenance** — has the source file's provenance been classified (see the provenance categories in `docs/pacific-brewio-architecture.md`)? Do not publish content whose provenance is "unknown or requires review."
- [ ] **Copyright concerns** — does publishing this risk reproducing copyrighted vendor material (app strings, images, substantial verbatim text) rather than an independent description of behavior?
- [ ] **Secret or personal-data leakage** — does the source material contain any credential, token, account identifier, device serial number, MAC address tied to a real owned unit, or other personal/private data that must be scrubbed or genericized first?
- [ ] **Vendor trademarks** — are vendor names/marks used only descriptively (e.g. "compatible with X") and not in a way implying endorsement, partnership, or official status?
- [ ] **Unsupported/private endpoint exposure** — does this document a private, undocumented, or unsupported vendor endpoint (a mobile-app-only cloud route, an internal API) in a way that could be read as inviting misuse, rather than as evidence recorded for engineering context?

## Engineering readiness

- [ ] **Unit tests** — does the corresponding driver code have unit test coverage for the behavior being documented?
- [ ] **Integration tests** — where practical, has the behavior been exercised against real (or, for the simulator, deliberately fake) hardware in an automated test?
- [ ] **Documentation examples** — does every code example in the guide actually run against the current package version? (Do not publish an example that was never executed.)
- [ ] **Explicit support status** — does the guide state one of the defined status words (Stable/Experimental/Read-only/Partial/Planned/Research only/Unsupported), matching the actual current implementation state, not an aspirational one?

## After promotion

- [ ] The internal research file is left in place, unmodified, in `docs/hardware_internal/` — promotion is a copy-and-adapt operation, not a move. The internal notebook keeps its full uncertainty, warnings, and provenance notes regardless of what became public.
- [ ] The public guide's own provenance section states which internal file(s) informed it, for future audit — without exposing the internal file's contents to readers who don't have access to it.
