# A bit of code from my shop, my experiments, and the projects I keep coming back to

I’m Charles Toepfer. My background is in software and technology, but these days I also own and operate [Pacific Brewing Supplies](https://pacific.supplies/), a homebrewing, winemaking, fermentation, and draft-supply shop in San Dimas, California. That mix of software work and running a real shop is the reason this repository looks a little eclectic.

I still like writing software because I run into a real problem, get curious about a thing, or decide an existing tool doesn’t quite do what I want. Some projects become useful tools. Others stay experiments. A few are just small utilities I wanted to keep around because they saved me time once.

## About Me

I’ve spent a lot of time building software for systems where the real world is messy: hardware, protocols, data quality, edge cases, and business workflows that have to work without a polished lab environment. That tendency shows up here.

The projects in this repository are not all part of one product or one plan. They’re connected by a common thread: they are things I built because I needed them, wanted to understand them better, or wanted to make them available to other people who might find them useful.

## Repository

This repository started as a place for code samples and tidbits, and it has gradually become a workspace with a few more substantial projects in it. Some are fairly mature, some are active experiments, and some are smaller utilities or older pieces of code I still keep around.

The common thread is not a polished monorepo product. It is that these are things I have built, investigated, or wanted to keep public: brewing tools, hardware integrations, research tooling, Drupal work, a small Roku utility, and a few one-off explorations.

If you want the current status of any project, the best place to look is that project’s own README. This repository is more of a personal workspace and collection than a single product line.

## Projects

### [brewconvert](brewconvert/)

This is my brewing recipe interchange and validation work. It is more than a converter that turns one XML file into another. The real problem is keeping the meaning of a recipe intact while translating between different formats and tools, each with slightly different assumptions about units, phases, ingredient types, and missing data.

The project is built around semantic validation, typed quantities, and preserving source evidence rather than silently guessing. That means ambiguous or unsafe inputs get flagged clearly instead of being converted into something plausible but wrong. For brewing data, that distinction matters a lot. Exporting a recipe is easy; exporting it without changing what the brewer actually meant is the interesting part.

### [brewpanel](brewpanel/)

This is a modular brewing control and integration project aimed at the real-world problem of talking to many different kinds of brewing hardware. Temperature controllers, hydrometers, sensors, and brewing systems all speak different protocols and expose different capabilities, but the software around them should not need to know every manufacturer-specific detail.

The underlying idea is a standardized capability layer: drivers expose common concepts like temperature, gravity, connectivity, and actuator behavior, and the rest of the application can work against those interfaces instead of scattered protocol code. The project also includes a safety model for state-changing operations so hardware actions do not silently bypass any confirmation path.

The current status is mixed in a healthy way: some drivers are implemented and working, while others are stubs or planned integrations. This is not a finished product so much as a foundation for turning a messy hardware ecosystem into something more manageable.

### [packscope](packscope/)

PackScope is a project for EEG and eye-tracking analysis in packaging and advertising research. The key idea is not to pretend the underlying signals justify stronger claims than they actually support. It is built around provenance, calibration, quality gates, and uncertainty: raw signals stay raw, gaze is calibrated before it is treated as a display coordinate, and interpretation remains separate from the measured data.

The project is deliberately careful about what it does not claim. It is not a medical tool, not a mind-reading system, and not a purchase-prediction engine. It is an exploratory toolkit for researchers who want to study patterns without turning measurement artifacts into certainty.

### [Drupal](Drupal/)

This directory contains Drupal work rather than a standalone Drupal project. The main package here is the [Commerce USIO](Drupal/modules/commerce_usio/) payment gateway module, which integrates Drupal Commerce with the USIO checkout flow and keeps the card-tokenization model aligned with the security and PCI-scope concerns that matter in a real checkout flow.

This is a practical integration project rather than a general-purpose framework. It is meant to be used as a module in a Drupal site and to be audited carefully before production use.

### [Roku](Roku/)

This is a small Go project for Roku beta-channel installation and validation. The goal is to assist with the mechanical parts of a beta test: loading configs, checking a manifest, downloading a channel bundle, validating checksums, and walking a tester through the Roku developer workflow without turning that workflow into a mystery.

It keeps the “what the device requires” and “what the app does” pieces separate, which matters when you are dealing with a device that does not let you shortcut its own developer-mode process.

### [shoeboxed](shoeboxed/)

This is a small utility for working with the Shoeboxed API. It is not a polished product; it is an example of the kind of direct integration work I sometimes do when a vendor exposes an API that is useful but awkward, and I want a simple way to authenticate and fetch the data I need.

### [docs](docs/)

This is the project documentation and architecture layer for the workspace. It includes notes on AI integration, hardware research, Pacific BrewIO architecture, and internal documentation for the brewing hardware systems referenced elsewhere in the repo.

A lot of this documentation exists because the software here is usually tied to real hardware, real protocols, and actual operational constraints. The docs are as important as the code in making those assumptions explicit.

## Contact

I’m on LinkedIn here:

[https://www.linkedin.com/in/charlest/](https://www.linkedin.com/in/charlest/)

And Pacific Brewing Supplies is here:

[https://pacific.supplies/](https://pacific.supplies/)
