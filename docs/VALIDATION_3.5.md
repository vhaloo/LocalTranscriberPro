# Validation 3.5.0 — 2026-11-01

## Scope

This release adds explicit CPU virtual-memory loading, cancellable CPU ASR/MT process isolation, quiet startup update checks, a visible update badge and default idle Windows installation. Existing 3.4 functions, language catalogues and model weights are retained. No new semantic reliability percentage or language-quality claim is introduced.

## Source checks

Unit tests cover low RAM with runtime/disk/language checks retained, strict checkpoint retention on CPU allocation failure, real subprocess lifecycle/cancellation, settings migration, quiet offline/current checks, active/private work deferral, hidden settings, updater byte reuse/tampering and final free-space checks. Real Tk fixtures exercise download-to-idle handoff without executing an installer. The transport and final launch are explicitly recording stubs in this UI fixture.

Native source checks transcribe with Tiny and full Whisper large-v3 in CPU virtual-memory mode and translate Tiny's English result to French using an isolated MADLAD CPU worker, all with model downloads disabled. A real large-v3 native load is cancelled and its worker disappears while the parent survives. This is functional evidence, not a forced OS exhaustion experiment or a multilingual quality benchmark. Model inference remains subject to the operating-system commit limit.

## Native delivery

Native build, installed-runtime, signature and data-preservation results are recorded after packaging and before publication. macOS arm64 and Linux x86-64 remain experimental; CI does not establish physical microphone or GPU compatibility.

Historical language diagnostics retain their original scope: [language diagnostics](LANGUAGE_DIAGNOSTICS_3.3.md), [3.4 validation](VALIDATION_3.4.md). Private sessions do not create new application transcript/audio/history files, but OS-managed virtual memory can page process data to disk.
