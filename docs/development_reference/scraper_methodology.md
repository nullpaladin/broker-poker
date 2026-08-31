# Automated Scraper Development Methodology

This document outlines the procedure for developing a fully automated web scraper for a new URL, minimizing the need for manual intervention. The approach is heavily influenced by existing examples, particularly those utilizing browser automation wrappers.

## Core Principle
The goal is to replace brittle, static selectors (e.g., fixed XPaths) and fixed time delays (`time.sleep()`) with dynamic, robust detection methods that respond to the live state of the target website.

## Development Stages

### Stage 1: Discovery and Analysis (The "Non-Intervention" Phase)
1.  **Navigation**: Use the browser automation tool to navigate to the target URL (`agent-browser open <NEW_URL>`).
2.  **DOM Mapping**: Immediately take a comprehensive snapshot of the current page state (`agent-browser snapshot -i`). This generates references (@e1, @e2, etc.) for all interactive elements.
3.  **Interaction Mapping**: Analyze the snapshot to determine the exact sequence of required actions:
    *   **Inputs**: Identify fields needing text entry.
    *   **Clicks**: Identify buttons or links that trigger navigation or submission.
    *   **Dropdowns**: Identify selectors for selection menus.
    *   **Loops**: Detect pagination controls to define the scraping loop boundary.

### Stage 2: Script Generation and Implementation
1.  **Architecture**: Replicate the structural pattern observed in successful scrapers (e.g., using a dedicated wrapper class for abstraction).
2.  **Selector Replacement**: Systematically replace all hardcoded selectors from the example with the stable, context-aware references found in Stage 1.
3.  **Wait Logic Enhancement**: **Crucially**, replace all `time.sleep()` calls with explicit, conditional waiting mechanisms (e.g., "Wait until element X is clickable"). This ensures the script waits only as long as necessary for dynamic content to load.
4.  **Flow Control**: Implement state-based control flow (e.g., "If 'Next Page' element is present, loop; otherwise, break").

### Stage 3: Validation and Refinement
1.  **Execution**: Run the generated script against the target URL.
2.  **Error Handling**: If the script fails, the error should point to a specific element failure. This failure is then used to return to Stage 1 (re-snapshotting) to find a new, functional selector for the failing component.

## Rights Coverage

The goal is to exercise **as many privacy rights as possible** for each broker — not just opt-out. Where a site offers separate forms for Right to Access, Right to Delete, and Right to Opt-Out, the scraper should handle all of them (typically gated behind `REMOVE_INFORMATION` for deletion).

When a site only exposes a subset of rights, note it explicitly in the README and in the scraper with a comment explaining what is missing and why (e.g., no form exists, email-only, requires account login). This makes it easy to revisit as sites update their privacy portals.

## Summary
The process is iterative: **Observe $\rightarrow$ Map $\rightarrow$ Script $\rightarrow$ Validate $\rightarrow$ Refine.** By prioritizing dynamic element detection over fixed paths, the scraper achieves a high degree of automation capability without constant manual intervention.